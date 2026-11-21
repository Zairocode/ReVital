"""TLS viejo: servidor local limitado a TLS 1.0 y otro moderno (solo 1.2). Necesita el comando `openssl` para
fabricar un certificado de prueba; si no esta, se omite. Correr: python tests/test_crawler_tls.py"""
import os, shutil, ssl, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import crawler

if not shutil.which("openssl"):
    print("omitido: no hay openssl para crear el certificado de prueba")
    sys.exit(0)

tmp = tempfile.mkdtemp()
cert, key = os.path.join(tmp, "c.pem"), os.path.join(tmp, "k.pem")
subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", cert,
                "-days", "1", "-subj", "/CN=localhost"], check=True, capture_output=True)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        b = b"<title>Portal viejo</title>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Server", "Microsoft-IIS/6.0")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


def servidor(minimo, maximo):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    try:
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        ctx.minimum_version, ctx.maximum_version = minimo, maximo
    except (ssl.SSLError, ValueError):
        return None
    srv = HTTPServer(("127.0.0.1", 0), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# servidor moderno: solo TLS 1.2
mod = servidor(ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_2)
acept = crawler.sondear_tls("127.0.0.1", mod.server_port)
assert list(acept) == ["TLSv1.2"], acept
inv = crawler.crawl("https://127.0.0.1:%d/" % mod.server_port, max_pages=3, delay=0, insecure=True)
assert inv["extra"]["tls"]["obsoletas"] == [] and ("Microsoft-IIS", "6.0") in {(c["producto"], c["version"]) for c in inv["components"]}
mod.shutdown()

# sin --insecure el certificado autofirmado se rechaza (no se contacta nada en silencio)
viejo = servidor(ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1)
if viejo is None:
    print("omitido el caso TLS 1.0: este Python/OpenSSL no puede ofrecer protocolos viejos")
    sys.exit(0)
url = "https://127.0.0.1:%d/" % viejo.server_port
seguro = crawler.crawl(url, max_pages=3, delay=0, insecure=False)
assert "error" in seguro["extra"]["pages"][0], seguro["extra"]["pages"][0]

# servidor legacy solo TLS 1.0: con --insecure el crawler entra y reporta el protocolo obsoleto
acept = crawler.sondear_tls("127.0.0.1", viejo.server_port)
assert list(acept) == ["TLSv1.0"], acept
inv = crawler.crawl(url, max_pages=3, delay=0, insecure=True)
comps = {(c["producto"], c["version"]) for c in inv["components"]}
assert ("Microsoft-IIS", "6.0") in comps, comps
assert ("TLS", "1.0") in comps and inv["extra"]["tls"]["obsoletas"] == ["TLSv1.0"], inv["extra"]["tls"]
assert "OBSOLETO" in crawler.to_markdown(inv)
viejo.shutdown()
print("ok: TLS 1.0 detectado y atravesado con --insecure; servidor moderno sin obsoletas")
