"""Colector web de ReVital: documenta una app web legacy -> inventario-web-<destino>.json + reporte .md.

Solo stdlib, compatible con Python 3.8+ (Windows 7 en adelante).
Uso: python -m revital.crawler https://app.interna.gob [--max 200] [--delay 0.5] [--insecure] [--entidad X] [--scope host2,host3] [--out salida]
Solo contra sistemas propios o con autorizacion.
"""
import argparse, io, os, re, socket, ssl, sys, time, zipfile, zlib
from collections import Counter, deque
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urljoin, urlparse, urldefrag, urlunparse
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler, HTTPSHandler
from urllib.error import HTTPError, URLError

from revital import inventory

# nombre-version en rutas de scripts: jquery-1.4.2.min.js, prototype-1.6.js, etc.
LIB_RE = re.compile(r"([a-z][a-z0-9.]*?)[-.@/]v?(\d+\.\d+(?:\.\d+)*)", re.I)
TECH_HEADERS = ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version")
EXT_HINTS = {".aspx": "ASP.NET WebForms", ".asp": "ASP Clasico", ".jsp": "Java JSP",
             ".php": "PHP", ".cfm": "ColdFusion", ".do": "Java Struts", ".action": "Java Struts"}
# la cookie de sesion delata la plataforma aunque no haya extension
COOKIE_HINTS = (("aspsessionid", "ASP Clasico"), ("asp.net_sessionid", "ASP.NET"), ("jsessionid", "Java servlet"),
                ("phpsessid", "PHP"), ("cfid", "ColdFusion"), ("cftoken", "ColdFusion"))
PATH_HINTS = (("/webresource.axd", "ASP.NET WebForms"), ("/scriptresource.axd", "ASP.NET WebForms"),
              ("/struts/", "Apache Struts"), ("/wp-content/", "WordPress"), ("/wp-includes/", "WordPress"),
              ("/sites/default/", "Drupal"), ("/media/jui/", "Joomla"), ("/_layouts/", "SharePoint"))
# paginas de error y comentarios suelen exponer "Apache Tomcat/6.0.18", "Microsoft-IIS/6.0", etc.
SERVER_RE = re.compile(r"(Apache Tomcat|Apache|Microsoft-IIS|nginx|Jetty|JBoss|WebLogic|WebSphere|PHP|OpenSSL)[/ ]+(\d[\w.]*)", re.I)
DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".rtf", ".zip", ".rar"}
SKIP_EXT = {".jpg", ".jpeg", ".png", ".gif", ".ico", ".css", ".js", ".svg", ".mp3", ".mp4", ".avi", ".woff", ".ttf"}
SESSION_PARAMS = {"jsessionid", "phpsessid", "sid", "aspsessionid", "sessionid"}

# Muchos servidores (WAF, IIS viejo, Apache con reglas) rechazan a quien no parezca un navegador: sin UA de navegador, sin Accept, sin cookies.
# Sigue siendo honesto: dice que es ReVital y solo lee. Se puede cambiar con --user-agent.
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; ReVital/0.1; solo-lectura)", "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
             "Accept-Language": "es,en;q=0.8", "Accept-Encoding": "gzip, deflate"}
_JAR = CookieJar()  # sesion de este analisis: sitios que redirigen hasta que aceptas una cookie


def _canon(netloc):
    """Identidad de un sitio para el alcance: 'WWW.Ejemplo.com:80' == 'ejemplo.com'. El puerto 8080 u otro SI es otro sitio."""
    n = netloc.lower().rsplit("@", 1)[-1].rstrip(".")
    host, sep, port = n.partition(":")
    if port in ("80", "443"):
        n = host
    return re.sub(r"^www\.", "", n)


def _descomprimir(raw, enc):
    """Si el servidor comprime (aunque no se lo hayamos pedido). Tope de 8 MB descomprimido contra bombas de compresion."""
    enc = (enc or "").lower()
    try:
        if "gzip" in enc:
            return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, 8_000_000)
        if "deflate" in enc:
            try:
                return zlib.decompressobj().decompress(raw, 8_000_000)
            except zlib.error:
                return zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw, 8_000_000)
    except zlib.error:
        pass
    return raw


def causa(e):
    """Por que no se pudo conectar, en palabras de una persona (no 'urlopen error timed out')."""
    r = getattr(e, "reason", e)
    if isinstance(r, socket.gaierror):
        return "no se pudo resolver el nombre del sitio (DNS): revisa que este bien escrito"
    if isinstance(r, ConnectionRefusedError):
        return "conexion rechazada: no hay ningun servicio escuchando en ese puerto"
    if isinstance(r, (socket.timeout, TimeoutError)) or "timed out" in str(r):
        return "tiempo agotado: el servidor no responde o un firewall descarta la conexion (prueba otra red; con curl ocurre lo mismo si no es de ReVital)"
    if isinstance(r, ssl.SSLCertVerificationError):
        return "el certificado no es valido (autofirmado, vencido o de otro nombre): usa --insecure si es un sistema propio"
    if isinstance(r, ssl.SSLError):
        return "fallo de TLS (%s): si es un servidor muy viejo prueba --insecure" % (getattr(r, "reason", None) or r)
    if isinstance(e, HTTPError):
        return "el servidor respondio HTTP %d" % e.code
    return str(r)[:140]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.links, self.scripts, self.forms, self.meta, self.comments = "", [], [], [], {}, []
        self._in_title = False

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "title":
            self._in_title = True
        elif tag in ("a", "frame", "iframe") and (a.get("href") or a.get("src")):
            self.links.append(a.get("href") or a.get("src"))
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        elif tag == "meta" and a.get("name") and a.get("content"):
            self.meta[a["name"].lower()] = a["content"]
        elif tag == "form":
            self.forms.append({"action": a.get("action", ""), "method": a.get("method", "get").lower(), "inputs": []})
        elif tag in ("input", "select", "textarea") and self.forms:
            self.forms[-1]["inputs"].append(a.get("name") or a.get("id") or tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_comment(self, d):
        self.comments.append(d)

    def handle_data(self, d):
        if self._in_title:
            self.title += d.strip()


class _Scope(HTTPRedirectHandler):
    """No sigue redirects a hosts fuera de scope (ni siquiera los contacta)."""
    def __init__(self, allowed):
        self.allowed = allowed  # identidades de _canon()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _canon(urlparse(newurl).netloc) not in self.allowed:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def decode(raw, ctype=""):
    """Charset del header o del <meta>; si no, utf-8 y, si no cuadra, latin-1 (que nunca falla)."""
    m = re.search(rb"charset=[\"']?([\w-]+)", ctype.encode() + b" " + raw[:2048], re.I)
    for enc in ([m.group(1).decode()] if m else []) + ["utf-8"]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            pass
    return raw.decode("latin-1")


def fetch(url, ctx, allowed, timeout=15, retries=2):
    """-> (status, headers, body, url_final). Reintenta fallos de red; los HTTP 4xx/5xx se devuelven tal cual."""
    req = Request(url, headers=CABECERAS)
    opener = build_opener(HTTPSHandler(context=ctx), HTTPCookieProcessor(_JAR), _Scope(allowed))
    for i in range(retries + 1):
        try:
            try:
                r = opener.open(req, timeout=timeout)
            except HTTPError as e:
                r = e
            ctype = r.headers.get("Content-Type", "")
            ok = ("html" in ctype or "xml" in ctype or ctype.startswith("text/")
                  or ctype.split(";")[0] in ("", "application/octet-stream"))  # legacy mal configurado
            body = decode(_descomprimir(r.read(2_000_000), r.headers.get("Content-Encoding")), ctype) if ok else ""
            headers = dict(r.headers.items())
            headers["set-cookie"] = "\n".join(r.headers.get_all("Set-Cookie") or [])
            return r.getcode(), headers, body, r.geturl()
        except Exception:
            if i == retries:
                raise
            time.sleep(1 + i)


def meta_documento(raw, nombre):
    """Software que creo el documento (revela versiones de Office/Acrobat). -> [(producto, version)]"""
    out = []
    if raw[:4] == b"%PDF":
        for campo in (b"Producer", b"Creator"):
            m = re.search(rb"/" + campo + rb"\s*\(([^)]{3,80})\)", raw)
            if m:
                out.append(split_ver(m.group(1).decode("latin-1")))
    elif raw[:2] == b"PK":  # docx/xlsx/pptx son zip con docProps/app.xml
        try:
            app = zipfile.ZipFile(io.BytesIO(raw)).read("docProps/app.xml").decode("utf-8", "replace")
            a, v = re.search(r"<Application>(.*?)</Application>", app), re.search(r"<AppVersion>(.*?)</AppVersion>", app)
            if a:
                out.append((a.group(1), v.group(1) if v else ""))
        except Exception:
            pass
    return out


def normalize(url):
    """Quita fragmento y ids de sesion en URL para no recorrer la misma pagina mil veces."""
    u = urlparse(urldefrag(url)[0])
    path = re.sub(r";jsessionid=[^?/]*", "", u.path, flags=re.I)
    q = "&".join(x for x in u.query.split("&") if x and x.split("=")[0].lower() not in SESSION_PARAMS)
    return urlunparse((u.scheme, u.netloc.lower(), path, "", q, ""))


def split_ver(txt):
    """'Microsoft-IIS/6.0' -> ('Microsoft-IIS', '6.0'); sin version -> (txt, '')."""
    m = re.match(r"\s*(.*?)[/ ]+v?(\d[\w.]*)\s*$", txt)
    return (m.group(1), m.group(2)) if m else (txt.strip(), "")


def tokens_ver(txt):
    """'Apache/2.4.49 (Unix) PHP/7.4' -> [('Apache','2.4.49'), ('PHP','7.4')]; sin tokens producto/version -> split_ver."""
    t = re.findall(r"([A-Za-z][\w.\-]*)/(\d[\w.]*)", txt)
    return t or [split_ver(txt)]


# archivos que revelan la version exacta del CMS (el meta generator de Drupal 7 solo dice "Drupal 7")
PROBES = (("/CHANGELOG.txt", r"(?m)^Drupal (\d+\.\d+)", "Drupal"),
          ("/readme.html", r"Version (\d+\.\d+(?:\.\d+)?)", "WordPress"),
          ("/administrator/manifests/files/joomla.xml", r"<version>([\d.]+)</version>", "Joomla"))


def sondear(start, ctx, allowed, timeout):
    """Pide los archivos de PROBES en la raiz. -> [(producto, version, fuente, donde)]"""
    u = urlparse(start)
    out = []
    for ruta, rx, prod in PROBES:
        url = "%s://%s%s" % (u.scheme, u.netloc, ruta)
        try:
            st, _, body, _ = fetch(url, ctx, allowed, timeout, retries=0)
        except Exception:
            continue
        m = re.search(rx, body) if st == 200 else None
        if m:
            out.append((prod, m.group(1), "archivo " + ruta, url))
    # Detras de un proxy, el header Server de las paginas es el del backend. Una URL mal formada la contesta
    # el servidor de enfrente con su propio error 400: ahi si aparece su version real.
    try:
        _, h, _, _ = fetch("%s://%s/%%zz" % (u.scheme, u.netloc), ctx, allowed, timeout, retries=0)
        srv = {k.lower(): v for k, v in h.items()}.get("server", "")
        out += [(p_, v_, "header server en error 400 (servidor de enfrente)", u.netloc) for p_, v_ in tokens_ver(srv) if v_]
    except Exception:
        pass
    return out


def detect_tech(url, headers, page, status=200, body=""):
    """Devuelve set de (producto, version, fuente)."""
    tech = set()
    low = {k.lower(): v for k, v in headers.items()}
    for h in TECH_HEADERS:
        if h in low:
            tech.update((prod, ver, "header " + h) for prod, ver in tokens_ver(low[h]))
    if "generator" in page.meta:
        tech.add(split_ver(re.sub(r"\s*\(.*?\)", "", page.meta["generator"])) + ("meta generator",))
    for s in page.scripts:
        m = LIB_RE.search(os.path.basename(urlparse(s).path))
        if m:
            tech.add((m.group(1).lower(), m.group(2), "script"))
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext in EXT_HINTS:
        tech.add((EXT_HINTS[ext], "", "extension " + ext))
    for c in low.get("set-cookie", "").split("\n"):
        name = c.split("=")[0].strip().lower()
        tech.update((prod, "", "cookie " + hint) for hint, prod in COOKIE_HINTS if name.startswith(hint))
    for ref in page.links + page.scripts:
        tech.update((prod, "", "ruta " + hint) for hint, prod in PATH_HINTS if hint in ref.lower())
    textos = [(c, "comentario html") for c in page.comments] + ([(body, "pagina de error")] if status >= 400 else [])
    for texto, fuente in textos:
        tech.update((m.group(1), m.group(2), fuente) for m in SERVER_RE.finditer(texto))
    return tech


def descubrir(start, ctx, allowed, timeout):
    """robots.txt y sitemap.xml como fuente de rutas (los Disallow suelen apuntar a /admin, /backup...).
    -> (urls_de_sitemap, rutas_disallow)"""
    u = urlparse(start)
    base = "%s://%s" % (u.scheme, u.netloc)

    def leer(url):
        try:
            st, _, body, _ = fetch(url, ctx, allowed, timeout, retries=0)
            return body if st == 200 else ""
        except Exception:
            return ""

    robots = leer(base + "/robots.txt")
    disallow = sorted({m.group(1) for m in re.finditer(r"(?im)^\s*disallow:\s*(/\S*)", robots)})
    maps = [m.group(1) for m in re.finditer(r"(?im)^\s*sitemap:\s*(\S+)", robots)] or [base + "/sitemap.xml"]
    urls, i = [], 0
    while i < len(maps) and i < 5:  # tope: 5 sitemaps (indices anidados incluidos)
        for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", leer(maps[i]), re.S):
            (maps if loc.endswith(".xml") else urls).append(loc)
        i += 1
    return urls[:500], disallow


TLS_VERSIONES = (("TLSv1.3", "TLSv1_3"), ("TLSv1.2", "TLSv1_2"), ("TLSv1.1", "TLSv1_1"), ("TLSv1.0", "TLSv1"))
TLS_OBSOLETAS = ("TLSv1.1", "TLSv1.0")


def contexto_tls(insecure):
    """Contexto normal; con insecure acepta certificados malos y baja hasta TLS 1.0 (Python moderno exige >= 1.2 por defecto)."""
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        try:
            ctx.set_ciphers("ALL:@SECLEVEL=0")
            ctx.minimum_version = ssl.TLSVersion.TLSv1
        except (ssl.SSLError, ValueError, AttributeError):  # build sin soporte de protocolos viejos: se queda con lo que haya
            pass
    return ctx


def sondear_tls(host, port, timeout=5):
    """Prueba cada version de TLS por separado. -> {version: cifrado} de las que el SERVIDOR acepta.
    Un servidor que todavia acepta TLS 1.0/1.1 es un hallazgo en si mismo."""
    aceptadas = {}
    for nombre, attr in TLS_VERSIONES:
        try:
            v = getattr(ssl.TLSVersion, attr)
            c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            c.check_hostname, c.verify_mode = False, ssl.CERT_NONE
            c.minimum_version = c.maximum_version = v
            try:
                c.set_ciphers("ALL:@SECLEVEL=0")
            except ssl.SSLError:
                pass
            with socket.create_connection((host, port), timeout=timeout) as s:
                with c.wrap_socket(s, server_hostname=host) as t:
                    aceptadas[nombre] = t.cipher()[0]
        except (ssl.SSLError, OSError, ValueError, AttributeError):
            pass  # no la acepta el servidor, o este Python no sabe hablarla
    return aceptadas


def completar_url(destino, ctx, timeout):
    """'ejemplo.gob', '10.0.0.5:8080' o ' http://x/ ' -> URL completa. Sin esquema se prueba https y, si no hay, http."""
    d = destino.strip()
    if "://" in d:
        return d
    sitio = d.split("/")[0]
    for esq in ("https", "http"):
        try:
            fetch("%s://%s/" % (esq, sitio), ctx, {_canon(sitio)}, min(timeout, 6), retries=0)
            return "%s://%s" % (esq, d)
        except Exception:
            continue
    return "http://" + d


def crawl(start, max_pages=200, delay=0.5, insecure=False, entidad="", scope=(), timeout=15, per_pattern=5, max_docs=20):
    ctx = contexto_tls(insecure)
    _JAR.clear()
    start = normalize(completar_url(start, ctx, timeout))
    allowed = {_canon(urlparse(start).netloc)} | {_canon(h) for h in scope}  # www.ejemplo.com y ejemplo.com son el mismo sitio
    print("Recorriendo %s | sitios permitidos: %s | solo con autorizacion" % (start, ", ".join(sorted(allowed))))
    try:  # prueba de vida: si el objetivo no responde, no se gastan decenas de peticiones con espera y se dice claro
        fetch(start, ctx, allowed, timeout, retries=1)
    except Exception as e:
        inv = inventory.nuevo("web", start, entidad)
        c = causa(e)
        inv["extra"] = {"tls": {"aceptadas": {}, "obsoletas": []}, "pages": [{"url": start, "error": c}], "documentos": [],
                        "hosts_permitidos": sorted(allowed), "robots_disallow": [], "sitemap_urls": 0, "sin_respuesta": True, "causa": c}
        return inv
    seen, queue, pages, tech, docs, patrones = set(), deque([start]), [], {}, set(), Counter()
    urls_map, disallow = descubrir(start, ctx, allowed, timeout)
    for prod, ver, fuente, donde in sondear(start, ctx, allowed, timeout):
        tech.setdefault((prod, ver, fuente), donde)
    for l in urls_map + [urljoin(start, d) for d in disallow if not re.search(r"[*$?]", d)]:
        l = normalize(l)
        if _canon(urlparse(l).netloc) in allowed:
            queue.append(l)
    try:
        while queue and len(pages) < max_pages:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            try:
                status, headers, body, final = fetch(url, ctx, allowed, timeout)
            except Exception as e:  # ponytail: un error por pagina no tumba el crawl; se reporta
                pages.append({"url": url, "error": causa(e)})
                continue
            loc = urljoin(url, headers.get("Location", "")) if 300 <= status < 400 else final
            if _canon(urlparse(loc).netloc) not in allowed:
                pages.append({"url": url, "error": "fuera de scope: redirige a %s (si es parte del mismo sistema, agrega --scope %s)" % (loc, urlparse(loc).netloc)})
                continue
            p = Page()
            p.feed(body)
            for k in detect_tech(url, headers, p, status, body):
                tech.setdefault(k, url)  # donde = primera pagina donde aparecio
            pages.append({"url": url, "status": status, "title": p.title, "forms": p.forms, "scripts": p.scripts})
            for l in p.links:
                l = normalize(urljoin(url, l))
                u = urlparse(l)
                ext = os.path.splitext(u.path)[1].lower()
                if not l.startswith("http") or _canon(u.netloc) not in allowed or l in seen or ext in SKIP_EXT:
                    continue
                if ext in DOC_EXT:
                    docs.add(l)
                    continue
                # tope por patron: /ver?id=1..99999 o calendarios infinitos no se recorren enteros
                key = (u.netloc, u.path, tuple(sorted(x.split("=")[0] for x in u.query.split("&") if x)))
                patrones[key] += 1
                if patrones[key] <= per_pattern:
                    queue.append(l)
            time.sleep(delay)
    except KeyboardInterrupt:
        print("Interrumpido: se guarda lo recorrido hasta ahora")
    opener = build_opener(HTTPSHandler(context=ctx), HTTPCookieProcessor(_JAR), _Scope(allowed))
    for d in sorted(docs)[:max_docs]:  # ponytail: solo los primeros max_docs; subir si hace falta
        try:
            raw = opener.open(Request(d, headers=dict(CABECERAS, **{"Accept-Encoding": "identity"})), timeout=timeout).read(3_000_000)
        except Exception:
            continue
        for prod, ver in meta_documento(raw, d):
            tech.setdefault((prod, ver, "metadato de documento"), d)
    tls = {}
    u = urlparse(start)
    if u.scheme == "https":
        host, _, port = u.netloc.partition(":")
        tls = sondear_tls(host, int(port or 443), min(timeout, 5))
        for ver in TLS_OBSOLETAS:
            if ver in tls:  # no es una version de software, pero es un hallazgo: protocolo obsoleto activo en el servidor
                tech.setdefault(("TLS", ver.replace("TLSv", ""), "protocolo obsoleto aceptado por el servidor"), u.netloc)
    inv = inventory.nuevo("web", start, entidad)
    inv["components"] = [inventory.componente(p, v, f, d) for (p, v, f), d in sorted(tech.items())]
    inv["extra"]["tls"] = {"aceptadas": tls, "obsoletas": [v for v in TLS_OBSOLETAS if v in tls]}
    inv["extra"]["pages"] = pages
    inv["extra"]["documentos"] = sorted(docs)
    inv["extra"]["hosts_permitidos"] = sorted(allowed)
    inv["extra"]["robots_disallow"] = disallow
    inv["extra"]["sitemap_urls"] = len(urls_map)
    if not any("status" in p for p in pages):  # ninguna pagina respondio (p. ej. redirige fuera del alcance): no es "sin hallazgos"
        inv["extra"]["sin_respuesta"] = True
        inv["extra"]["causa"] = next((p["error"] for p in pages if "error" in p), "ninguna pagina respondio")
    return inv


def to_markdown(r):
    pages, docs = r["extra"]["pages"], r["extra"]["documentos"]
    out = ["# Reporte ReVital (web): %s" % r["target"], "", "Entidad: %s" % (r["entidad"] or "-"),
           "Generado: %s" % r["generado"], "Paginas: %d" % len(pages), "", "## Componentes", "",
           "| Producto | Version | Fuente | Donde |", "|---|---|---|---|"]
    out += ["| %(producto)s | %(version)s | %(fuente)s | %(donde)s |" % c for c in r["components"]]
    tls = r["extra"].get("tls", {})
    if tls.get("aceptadas"):
        out += ["", "## Protocolos TLS que acepta el servidor", ""]
        out += ["- %s (%s)%s" % (v, c, "  **OBSOLETO**" if v in tls["obsoletas"] else "") for v, c in tls["aceptadas"].items()]
    out += ["", "## Documentos enlazados (%d)" % len(docs), ""] + ["- " + d for d in docs]
    if r["extra"]["robots_disallow"]:
        out += ["", "## Rutas que robots.txt pide ocultar (%d)" % len(r["extra"]["robots_disallow"]), ""]
        out += ["- `%s`" % d for d in r["extra"]["robots_disallow"]]
    out += ["", "## Paginas", ""]
    for p in pages:
        out.append("- `%s` -> %s %s" % (p["url"], p.get("status", "ERROR"), p.get("title") or p.get("error", "")))
        for f in p.get("forms", []):
            out.append("  - form %s %s (%s)" % (f["method"].upper(), f["action"] or "(misma)", ", ".join(f["inputs"])))
    return "\n".join(out) + "\n"


def demo():  # python -m revital.crawler --demo : verifica el parser sin red
    p = Page()
    p.feed('<title>X</title><script src="/js/jquery-1.4.2.min.js"></script><!-- Apache Tomcat/6.0.18 -->'
           '<meta name="generator" content="Joomla 1.5"><a href="/WebResource.axd?d=1">r</a>'
           '<form action="/a" method="POST"><input name="u"></form>')
    t = detect_tech("http://h/login.aspx", {"Server": "Microsoft-IIS/6.0", "Set-Cookie": "ASPSESSIONIDQQ=x; path=/"}, p)
    assert p.title == "X" and p.forms[0]["inputs"] == ["u"], p.forms
    assert {("jquery", "1.4.2", "script"), ("Microsoft-IIS", "6.0", "header server"),
            ("ASP.NET WebForms", "", "extension .aspx"), ("Joomla", "1.5", "meta generator"),
            ("Apache Tomcat", "6.0.18", "comentario html"), ("ASP Clasico", "", "cookie aspsessionid"),
            ("ASP.NET WebForms", "", "ruta /webresource.axd")} <= t, t
    err = detect_tech("http://h/x", {}, Page(), 404, "<h3>Apache Tomcat/5.5.23</h3>")
    assert ("Apache Tomcat", "5.5.23", "pagina de error") in err, err
    assert decode("Educación".encode("latin-1")) == "Educación" and decode("Educación".encode("utf-8")) == "Educación"
    assert decode('<meta charset="iso-8859-1">Niño'.encode("latin-1")).endswith("Niño")
    assert meta_documento(b"%PDF-1.4 /Producer (Acrobat Distiller 8.0.0)", "a.pdf") == [("Acrobat Distiller", "8.0.0")]
    z = io.BytesIO()
    zipfile.ZipFile(z, "w").writestr("docProps/app.xml", "<Application>Microsoft Office Word</Application><AppVersion>12.0000</AppVersion>")
    assert meta_documento(z.getvalue(), "a.docx") == [("Microsoft Office Word", "12.0000")]
    h = detect_tech("http://h/", {"Server": "Apache/2.4.49 (Unix) PHP/7.4.33 OpenSSL/1.0.2k"}, Page())
    assert {("Apache", "2.4.49", "header server"), ("PHP", "7.4.33", "header server"),
            ("OpenSSL", "1.0.2k", "header server")} <= h, h
    assert normalize("HTTP://H/a;jsessionid=AB12?x=1&PHPSESSID=z#f") == "http://h/a?x=1"
    print("ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--max", type=int, default=200)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--out", default="salida")
    ap.add_argument("--entidad", default="")
    ap.add_argument("--scope", default="", help="hosts extra permitidos, separados por coma (ej: portal.gob,api.gob)")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo(); sys.exit()
    if not a.url:
        ap.error("falta url")
    res = crawl(a.url, a.max, a.delay, a.insecure, a.entidad, [h for h in a.scope.split(",") if h], a.timeout)
    j = inventory.guardar(res, a.out)
    md = os.path.join(a.out, "reporte-%s-web-%s.md" % (a.entidad or "sin-entidad", inventory.slug(res["target"])))
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(res))
    if res["extra"].get("sin_respuesta"):  # nunca presentar un fallo como "sin hallazgos"
        sys.exit("NO RESPONDIO: %s -> %s\nNo se analizo nada. El reporte dira 'sin datos', no 'cumple'. (Guardado en %s)" % (res["target"], res["extra"]["causa"], j))
    print("listo: %s y %s (%d componentes)" % (j, md, len(res["components"])))
