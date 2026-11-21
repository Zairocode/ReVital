"""Prueba de integracion: sitio falso legacy local. Correr: python tests/test_crawler_local.py"""
import os, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import crawler


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        p = self.path
        if p.startswith("/ver"):          # trampa: id infinito
            n = int(p.split("=")[1])
            return self.send(200, '<a href="/ver?id=%d">sig</a>' % (n + 1))
        if p == "/fuera":                 # redirect a otro host
            self.send_response(302); self.send_header("Location", "http://example.invalid/"); self.end_headers(); return
        if p == "/%zz":
            return self.send(400, "<h1>Bad Request</h1>", {"Server": "Apache/2.4.49 (Unix)"})
        if p == "/robots.txt":
            return self.send(200, "User-agent: *\nDisallow: /admin/\nSitemap: http://%s/sitemap.xml" % self.headers["Host"], ctype="text/plain")
        if p == "/sitemap.xml":
            return self.send(200, "<urlset><url><loc>http://%s/oculta</loc></url></urlset>" % self.headers["Host"], ctype="application/xml")
        if p == "/oculta":
            return self.send(200, "<title>Oculta</title>", {"Server": "Apache/2.0.52 (Unix) PHP/5.2.17"})
        if p == "/CHANGELOG.txt":
            return self.send(200, "Drupal 7.57, 2018-02-21\n-----------------------\nDrupal 7.56, 2017-06-21\n", ctype="text/plain")
        if p == "/informe.pdf":
            return self.send(200, b"%PDF-1.4 /Producer (Acrobat Distiller 8.0.0)", ctype="application/pdf")
        if p == "/nada":                  # pagina de error con version
            return self.send(404, "<h3>Apache Tomcat/5.5.23</h3>")
        self.send(200, '<title>Inicio</title><a href="/ver?id=1">v</a><a href="/fuera">f</a><a href="/nada">n</a>'
                       '<a href="/informe.pdf">pdf</a><a href="/x;jsessionid=AB">x</a>',
                  {"Set-Cookie": "ASPSESSIONIDXX=1", "Server": "Microsoft-IIS/6.0"})

    def send(self, code, body, hdr=None, ctype="text/html"):
        self.send_response(code); self.send_header("Content-Type", ctype)
        for k, v in (hdr or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body if isinstance(body, bytes) else body.encode())


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
inv = crawler.crawl("http://127.0.0.1:%d/" % srv.server_port, max_pages=50, delay=0)
srv.shutdown()
pages = inv["extra"]["pages"]
prods = {(c["producto"], c["version"]) for c in inv["components"]}
assert len([p for p in pages if "/ver?id=" in p["url"]]) <= 5, "trampa no contenida"
assert any("fuera de scope" in p.get("error", "") for p in pages), "redirect externo no bloqueado"
assert ("Apache Tomcat", "5.5.23") in prods and ("Microsoft-IIS", "6.0") in prods, prods
assert ("ASP Clasico", "") in prods, prods
assert any(d.endswith("informe.pdf") for d in inv["extra"]["documentos"])
assert any(p["url"].endswith("/oculta") for p in pages) and ("Apache", "2.0.52") in prods, "sitemap no usado"
assert inv["extra"]["robots_disallow"] == ["/admin/"], inv["extra"]["robots_disallow"]
assert ("Drupal", "7.57") in prods and ("PHP", "5.2.17") in prods, prods
assert ("Apache", "2.4.49") in prods, "sonda de error 400 del front no leida"
assert ("Acrobat Distiller", "8.0.0") in prods, "metadato de documento no leido"
assert not any("jsessionid" in p["url"] for p in pages)
print("ok", len(pages), "paginas")
