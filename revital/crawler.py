"""Colector web de ReVital: documenta una app web legacy -> inventario-web.json + reporte .md.

Solo stdlib, compatible con Python 3.8+ (Windows 7 en adelante).
Uso: python -m revital.crawler https://app.interna.gob [--max 200] [--delay 0.5] [--insecure] [--entidad X] [--out salida]
Solo contra sistemas propios o con autorizacion.
"""
import argparse, json, os, re, ssl, sys, time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from revital import inventory

# nombre-version en rutas de scripts: jquery-1.4.2.min.js, prototype-1.6.js, etc.
LIB_RE = re.compile(r"([a-z][a-z0-9.]*?)[-.@/]v?(\d+\.\d+(?:\.\d+)*)", re.I)
TECH_HEADERS = ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version")
EXT_HINTS = {".aspx": "ASP.NET WebForms", ".asp": "ASP Clasico", ".jsp": "Java JSP",
             ".php": "PHP", ".cfm": "ColdFusion", ".do": "Java Struts", ".action": "Java Struts"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.links, self.scripts, self.forms, self.meta = "", [], [], [], {}
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

    def handle_data(self, d):
        if self._in_title:
            self.title += d.strip()


def fetch(url, ctx):
    req = Request(url, headers={"User-Agent": "ReVital-crawler/0.1"})
    try:
        r = urlopen(req, timeout=15, context=ctx)
    except HTTPError as e:
        r = e
    ctype = r.headers.get("Content-Type", "")
    ok = "html" in ctype or ctype.split(";")[0] in ("", "application/octet-stream")  # legacy mal configurado
    body = r.read(2_000_000).decode("latin-1") if ok else ""  # latin-1 no falla nunca
    return r.getcode(), dict(r.headers), body


def split_ver(txt):
    """'Microsoft-IIS/6.0' -> ('Microsoft-IIS', '6.0'); sin version -> (txt, '')."""
    m = re.match(r"\s*(.*?)[/ ]+v?(\d[\w.]*)\s*$", txt)
    return (m.group(1), m.group(2)) if m else (txt.strip(), "")


def detect_tech(url, headers, page):
    """Devuelve set de (producto, version, fuente)."""
    tech = set()
    low = {k.lower(): v for k, v in headers.items()}
    for h in TECH_HEADERS:
        if h in low:
            tech.add(split_ver(low[h]) + ("header " + h,))
    if "generator" in page.meta:
        tech.add(split_ver(page.meta["generator"]) + ("meta generator",))
    for s in page.scripts:
        m = LIB_RE.search(os.path.basename(urlparse(s).path))
        if m:
            tech.add((m.group(1).lower(), m.group(2), "script"))
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext in EXT_HINTS:
        tech.add((EXT_HINTS[ext], "", "extension " + ext))
    return tech


def crawl(start, max_pages=200, delay=0.5, insecure=False, entidad=""):
    ctx = ssl.create_default_context()
    if insecure:  # servidores viejos: TLS 1.0, certs vencidos o autofirmados
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        try:
            ctx.set_ciphers("ALL:@SECLEVEL=0")
        except ssl.SSLError:
            pass
    host, seen, queue, pages, tech = urlparse(start).netloc, set(), [start], [], {}
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            status, headers, body = fetch(url, ctx)
        except Exception as e:  # ponytail: un error por pagina no tumba el crawl; se reporta
            pages.append({"url": url, "error": str(e)})
            continue
        p = Page()
        p.feed(body)
        t = detect_tech(url, headers, p)
        for k in t:
            tech.setdefault(k, url)  # donde = primera pagina donde aparecio
        pages.append({"url": url, "status": status, "title": p.title, "forms": p.forms,
                      "scripts": p.scripts})
        for l in p.links:
            l = urldefrag(urljoin(url, l))[0]
            if urlparse(l).netloc == host and l.startswith("http") and l not in seen:
                queue.append(l)
        time.sleep(delay)
    inv = inventory.nuevo("web", start, entidad)
    inv["components"] = [inventory.componente(p, v, f, d) for (p, v, f), d in sorted(tech.items())]
    inv["extra"]["pages"] = pages
    return inv


def to_markdown(r):
    pages = r["extra"]["pages"]
    out = ["# Reporte ReVital (web): %s" % r["target"], "", "Entidad: %s" % (r["entidad"] or "-"),
           "Generado: %s" % r["generado"], "Paginas: %d" % len(pages), "", "## Componentes", "",
           "| Producto | Version | Fuente | Donde |", "|---|---|---|---|"]
    out += ["| %(producto)s | %(version)s | %(fuente)s | %(donde)s |" % c for c in r["components"]]
    out += ["", "## Paginas", ""]
    for p in pages:
        out.append("- `%s` -> %s %s" % (p["url"], p.get("status", "ERROR"), p.get("title") or p.get("error", "")))
        for f in p.get("forms", []):
            out.append("  - form %s %s (%s)" % (f["method"].upper(), f["action"] or "(misma)", ", ".join(f["inputs"])))
    return "\n".join(out) + "\n"


def demo():  # python crawler.py --demo : verifica el parser sin red
    p = Page()
    p.feed('<title>X</title><script src="/js/jquery-1.4.2.min.js"></script>'
           '<meta name="generator" content="Joomla 1.5"><form action="/a" method="POST"><input name="u"></form>')
    t = detect_tech("http://h/login.aspx", {"Server": "Microsoft-IIS/6.0"}, p)
    assert p.title == "X" and p.forms[0]["inputs"] == ["u"], p.forms
    assert {("jquery", "1.4.2", "script"), ("Microsoft-IIS", "6.0", "header server"),
            ("ASP.NET WebForms", "", "extension .aspx"), ("Joomla", "1.5", "meta generator")} <= t, t
    print("ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--max", type=int, default=200)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--out", default="salida")
    ap.add_argument("--entidad", default="")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo(); sys.exit()
    if not a.url:
        ap.error("falta url")
    res = crawl(a.url, a.max, a.delay, a.insecure, a.entidad)
    j = inventory.guardar(res, a.out)
    md = os.path.join(a.out, "reporte-%s-web.md" % (a.entidad or "sin-entidad"))
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(res))
    print("listo: %s y %s (%d componentes)" % (j, md, len(res["components"])))
