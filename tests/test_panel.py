"""Panel local: paginas, descargas, zip y protecciones. Correr: python tests/test_panel.py"""
import http.client, io, json, os, socket, sys, tempfile, threading, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital.panel import app, vistas

salida = tempfile.mkdtemp()


def w(nombre, contenido):
    with open(os.path.join(salida, nombre), "w", encoding="utf-8") as f:
        f.write(contenido if isinstance(contenido, str) else json.dumps(contenido))


hall = {"entidad": "MUNI-GT", "fecha_evaluacion": "2026-11-21", "catalogos": {"kev_version": "2026.11.20"},
        "componentes": [{"producto": "Drupal", "detectado_como": "Drupal", "version": "7.57", "evidencia": [{"kind": "web", "donde": "/CHANGELOG.txt", "fuente": "archivo"}]}],
        "hallazgos": [{"cve": "CVE-2018-7600", "producto": "Drupal", "version": "7.57", "en_kev": True, "cvss": 9.8, "nivel": 1, "nivel_txt": "CRITICO",
                       "ransomware": "Known", "vencido": True, "accion": "Apply updates per vendor instructions.", "fecha_limite": "2022-05-03",
                       "agregado_kev": "2021-11-03", "nombre": "Drupalgeddon 2", "descripcion": "RCE <script>alert(1)</script>", "motivo": "KEV + ransomware",
                       "confianza": "confirmado", "evidencia": [{"kind": "web", "donde": "/x", "fuente": "y"}],
                       "parche": "Actualizar Drupal a 7.58", "mitigacion": "Bloquear en el WAF",
                       "regla": "SecRule ARGS_NAMES \"@contains #\" \"id:900100,deny\"",
                       "exploits": [[44449, 1, "webapps", "2018-04-13", "Drupalgeddon2 <b>RCE</b>"]]},
                      {"cve": "CVE-2000-1", "producto": "Drupal", "version": "7.57", "en_kev": False, "cvss": 5.0, "nivel": 6, "nivel_txt": "BAJO", "evidencia": []}],
        "condicionales": [], "eol": [{"producto": "Drupal", "version": "7.57"}], "sin_mapeo": [],
        "configuracion": [{"tipo": "Configuracion insegura", "detalle": "web.config: debug=true", "recomendacion": "Apagar el modo debug", "evidencia": []}]}
w("hallazgos-muni-gt.json", hall)
w("reporte-muni-gt.md", "# Reporte ReVital: MUNI-GT\n\n| A | B |\n|---|---|\n| **uno** | `dos` |\n\n- item <b>x</b>\n")
w("inventario-web-localhost-8080.json", {"kind": "web", "target": "http://localhost:8080", "entidad": "MUNI-GT", "components": []})
w("reporte-MUNI-GT-web-localhost-8080.md", "# colector\n")
w("secreto-ajeno.json", {"x": 1})  # no pertenece a la entidad: no debe ir en el zip

s = socket.socket(); s.bind(("127.0.0.1", 0)); puerto = s.getsockname()[1]; s.close()
srv = app.crear(salida, puerto)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def pedir(metodo, ruta, cuerpo=None, host=None, extra=None):
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=10)
    h = {"Host": host or "127.0.0.1:%d" % puerto}
    h.update(extra or {})
    if cuerpo is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    c.request(metodo, ruta, body=cuerpo, headers=h)
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


# paginas
st, _, b = pedir("GET", "/"); assert st == 200 and b"MUNI-GT" in b and b"NO CUMPLE" in b
st, _, b = pedir("GET", "/e/muni-gt"); assert st == 200 and b"CVE-2018-7600" in b
st, _, b = pedir("GET", "/e/muni-gt?tab=hallazgos"); assert st == 200 and b"EN KEV" in b and b"ransomware" in b
assert b"<script>alert(1)</script>" not in b and b"&lt;script&gt;" in b, "la descripcion debe ir escapada (XSS)"
for txt in (b"Actualizar Drupal a 7.58", b"Bloquear en el WAF", b"SecRule ARGS_NAMES", b"EDB-44449"):
    assert txt in b, txt  # parche, mitigacion, regla copiable y exploits publicos
assert b"<b>RCE</b>" not in b and b"&lt;b&gt;RCE" in b, "el titulo del exploit va escapado"
st, _, r = pedir("GET", "/e/muni-gt"); assert b"Configuraci" in r and b"debug=true" in r and b"Apagar el modo debug" in r
st, _, b = pedir("GET", "/e/muni-gt?tab=hallazgos&f=otras"); assert st == 200 and b"CVE-2000-1" in b and b"CVE-2018-7600" not in b
for tab in ("inventario", "docs", "historial"):
    assert pedir("GET", "/e/muni-gt?tab=" + tab)[0] == 200, tab
for ruta in ("/sentinela", "/trabajos"):
    assert pedir("GET", ruta)[0] == 200, ruta
assert pedir("GET", "/e/no-existe")[0] == 404 and pedir("GET", "/nada")[0] == 404

# documentos: ver (markdown a html, escapado), descargar y zip
st, _, b = pedir("GET", "/ver/reporte-muni-gt.md"); assert st == 200 and b"<table>" in b and b"<b>uno</b>" in b and b"&lt;b&gt;x&lt;/b&gt;" in b
st, h, b = pedir("GET", "/descargar/hallazgos-muni-gt.json"); assert st == 200 and "attachment" in h["Content-Disposition"] and json.loads(b)["entidad"] == "MUNI-GT"
st, h, b = pedir("GET", "/zip/muni-gt"); assert st == 200 and h["Content-Type"] == "application/zip"
nombres = zipfile.ZipFile(io.BytesIO(b)).namelist()
assert "ReVital-muni-gt/reporte-muni-gt.md" in nombres and "ReVital-muni-gt/inventario-web-localhost-8080.json" in nombres, nombres
assert not [n for n in nombres if "secreto" in n], "el zip solo lleva lo de la entidad"

# protecciones
assert pedir("GET", "/descargar/..%2fREADME.md")[0] == 404 and pedir("GET", "/descargar/%2e%2e%2f%2e%2e%2fREADME.md")[0] == 404
assert pedir("GET", "/descargar/C%3A%5CWindows%5Cwin.ini")[0] == 404
assert pedir("GET", "/descargar/x.exe")[0] == 404
assert pedir("GET", "/", host="evil.example.com")[0] == 403, "un Host ajeno (DNS rebinding) debe rechazarse"
form = "tipo=web&destino=http%3A%2F%2Flocalhost%3A1&entidad=X"
assert pedir("POST", "/analizar", form + "&autorizo=1", extra={"Origin": "http://evil.example.com"})[0] == 403
assert pedir("POST", "/analizar", form)[0] == 400, "sin confirmar autorizacion no se analiza"
assert pedir("POST", "/analizar", "tipo=web&destino=file%3A%2F%2F%2Fetc%2Fpasswd&entidad=X&autorizo=1")[0] == 400
assert pedir("POST", "/analizar", "tipo=web&destino=http%3A%2F%2Fa&entidad=%3Bcalc&autorizo=1")[0] == 400
assert pedir("POST", "/analizar", "tipo=codigo&destino=C%3A%5Cno%5Cexiste&entidad=X&autorizo=1")[0] == 400
# JavaScript: solo archivos locales de /static (GSAP y panel.js); nada embebido ni de internet
casa = pedir("GET", "/")[2]
assert casa.count(b"<script") == casa.count(b'<script src="/static/') == 2, "solo scripts locales"
assert b"http://" not in casa.split(b"<body>")[0] and b"https://" not in casa.split(b"<body>")[0], "nada se carga de internet"
assert b"Revitaliza tu Sistema" in casa and b'name="autorizo" value="1"' in casa and b"Tengo autorizaci" not in casa
st, h, b = pedir("GET", "/static/gsap.min.js"); assert st == 200 and "javascript" in h["Content-Type"] and b"GSAP" in b[:200]
assert pedir("GET", "/static/instrument-sans-latin-400-normal.woff2")[0] == 200
for malo in ("/static/..%2fapp.py", "/static/app.py", "/static/%2e%2e%2f%2e%2e%2fREADME.md", "/static/x.exe"):
    assert pedir("GET", malo)[0] == 404, malo
st, _, b = pedir("GET", "/api/estado"); assert st == 200 and "v" in json.loads(b)
# un solo buscador: sin "tipo", una URL es web y lo demas es una carpeta
assert pedir("POST", "/analizar", "destino=C%3A%5Cno%5Cexiste&entidad=X&autorizo=1")[0] == 400
# vigilancia por entidad (interruptor)
assert pedir("POST", "/vigilar", "slug=muni-gt&activar=1")[0] == 303
cfg = json.load(open(os.path.join(salida, "vigilancia.json"), encoding="utf-8"))
assert cfg["objetivos"] == [{"entidad": "MUNI-GT", "tipo": "web", "destino": "http://localhost:8080", "insecure": False}], cfg
assert b"Vigilando cada hora" in pedir("GET", "/e/muni-gt")[2]
assert pedir("POST", "/vigilar", "slug=muni-gt&activar=0")[0] == 303
assert json.load(open(os.path.join(salida, "vigilancia.json"), encoding="utf-8"))["objetivos"] == []
assert pedir("POST", "/vigilar", "slug=no-existe&activar=1")[0] == 404

# el markdown mal formado no rompe nada
assert "<table>" in vistas.md_a_html("| a |\n|---|\n| b |") and vistas.md_a_html("") == ""
srv.shutdown()
print("ok: paginas, descargas, zip y protecciones")
