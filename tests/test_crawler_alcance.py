"""Por que el crawler 'no apunta bien' a muchos destinos reales: reproduce, con un servidor falso LOCAL (sin internet), lo que hacen
los sitios de verdad: bloquear clientes sin navegador, exigir cookies, comprimir sin pedirlo, redirigir entre www y el dominio base,
y objetivos escritos sin http://. Tambien: un objetivo caido debe reportarse como tal, nunca como 'sin vulnerabilidades'.
Correr: python tests/test_crawler_alcance.py"""
import gzip, os, socket, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from revital import crawler

fallos = []


def chequear(nombre, cond, detalle=""):
    print(("  ok     " if cond else "  FALLA  ") + nombre + ("" if cond else "  -> " + str(detalle)[:140]))
    if not cond:
        fallos.append(nombre)


PAGINA = b"<html><head><title>Portal</title><meta name='generator' content='Joomla 1.5'></head><body><a href='/otra'>otra</a></body></html>"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    def responder(self, codigo, cuerpo=b"", cab=None):
        self.send_response(codigo)
        for k, v in (cab or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ua, p = self.headers.get("User-Agent", ""), self.path
        if p.startswith("/exigeua"):                      # WAF tipico: rechaza lo que no parezca un navegador
            return self.responder(200, PAGINA, {"Content-Type": "text/html"}) if "Mozilla" in ua else self.responder(403, b"Forbidden")
        if p.startswith("/cookie"):                       # sesion obligatoria: sin cookie, redirige en bucle
            if "sid=" not in (self.headers.get("Cookie") or ""):
                return self.responder(302, b"", {"Location": "/cookie/entrar"})
            return self.responder(200, PAGINA, {"Content-Type": "text/html"})
        if p == "/cookie/entrar":
            return self.responder(302, b"", {"Location": "/cookie", "Set-Cookie": "sid=1; Path=/"})
        if p.startswith("/gzip"):                         # comprime aunque el cliente no lo haya pedido
            return self.responder(200, gzip.compress(PAGINA), {"Content-Type": "text/html", "Content-Encoding": "gzip"})
        if p.startswith("/sinaccept"):                    # algunos servidores viejos exigen cabecera Accept
            return self.responder(200, PAGINA, {"Content-Type": "text/html"}) if self.headers.get("Accept") else self.responder(406, b"No")
        self.responder(200, PAGINA, {"Content-Type": "text/html", "Server": "Apache/2.2.15"})


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d" % srv.server_port
cerrado = socket.socket(); cerrado.bind(("127.0.0.1", 0)); puerto_muerto = cerrado.getsockname()[1]; cerrado.close()


def corre(url, **kw):
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return crawler.crawl(url, max_pages=3, delay=0, timeout=4, **kw)


def ok(inv):
    """Solo cuenta si la pagina se LEYO de verdad (200 y se entendio su titulo), no una redireccion ni un 403."""
    return any(p.get("status") == 200 and p.get("title") == "Portal" for p in inv["extra"]["pages"])


print("Servidores que se comportan como los de verdad:")
chequear("lo normal funciona", ok(corre(base + "/")))
chequear("exige parecer un navegador (User-Agent)", ok(corre(base + "/exigeua")), "recibe 403")
chequear("responde comprimido sin que se lo pidan", ok(corre(base + "/gzip")), "no se entiende el contenido")
chequear("exige la cabecera Accept", ok(corre(base + "/sinaccept")), "406")
inv = corre(base + "/gzip")
chequear("...y de lo comprimido saca la tecnologia", any(c["producto"] == "Joomla" for c in inv["components"]), inv["components"])

print("Como lo escribe una persona:")
chequear("destino sin http:// (127.0.0.1:puerto)", ok(corre("127.0.0.1:%d" % srv.server_port)), "sin esquema no se sabe a donde ir")
inv_c = corre("127.0.0.1:%d" % puerto_muerto)
chequear("sin http:// y caido: el error recuerda que se probo https", inv_c["extra"].get("sin_respuesta") is True and "al probar https" in str(inv_c["extra"].get("causa")), inv_c["extra"].get("causa"))
chequear("destino con espacios o barra final", ok(corre("  " + base + "/  ")))

print("Alcance (www, dominio base y puertos por defecto):")
c = lambda n: getattr(crawler, "_canon", lambda x: x)(n)
chequear("example.com == www.example.com", c("example.com") == c("www.example.com"), (c("example.com"), c("www.example.com")))
chequear("example.com:80 == example.com y :443", c("example.com:80") == c("example.com") == c("example.com:443"))
chequear("el puerto 8080 SI es otro sitio", c("example.com:8080") != c("example.com"))
chequear("otro dominio NO es el mismo sitio", c("example.com") != c("example.org") and c("example.com") != c("evil-example.com"))
rd = crawler._Scope({c("example.com")})
chequear("sigue la redireccion al www del mismo sitio", rd.redirect_request(crawler.Request("http://example.com/"), None, 301, "", {}, "https://www.example.com/") is not None)
chequear("NO sigue la redireccion a otro dominio", rd.redirect_request(crawler.Request("http://example.com/"), None, 301, "", {}, "http://evil.com/") is None)

print("Objetivo caido: no puede parecer 'sin vulnerabilidades':")
inv = corre("http://127.0.0.1:%d/" % puerto_muerto)
chequear("el inventario dice que NO respondio", inv["extra"].get("sin_respuesta") is True, inv["extra"].keys())
chequear("explica por que (conexion rechazada)", "rechaz" in str(inv["extra"].get("causa", "")).lower(), inv["extra"].get("causa"))
r = subprocess.run([sys.executable, "-m", "revital.crawler", "http://127.0.0.1:%d/" % puerto_muerto, "--out", tempfile.mkdtemp(), "--timeout", "3", "--delay", "0"],
                   cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
chequear("el comando termina con error (codigo != 0)", r.returncode != 0, "codigo %s" % r.returncode)
chequear("y lo dice claro, sin 'listo'", "NO RESPONDIO" in r.stdout.upper() and "listo:" not in r.stdout, r.stdout[-160:])

srv.shutdown()
print("\n%d fallo(s)" % len(fallos) if fallos else "\nok: el crawler apunta bien a todos los casos")
sys.exit(1 if fallos else 0)
