"""Prueba de PUNTA A PUNTA del caso MUNI-GT: ReVital completo contra el stack levantado (portal + servidor de la muni).

Sirve tambien de ensayo del demo. Necesita el stack arriba (docker compose up -d en casos/portal-muni-gt/docker).

  python3 casos/portal-muni-gt/backend/test_e2e.py                      # stack local: 127.0.0.1, portal en :8080
  E2E_IP=100.91.166.18 E2E_PORTAL=http://100.91.166.18:8088 python3 casos/portal-muni-gt/backend/test_e2e.py

Que comprueba:
  1. Colector de red: MySQL y Redis expuestos; Exim 4.89 y MySQL 5.5.62 por banner; el proxy Apache 2.4.49 delante del portal.
  2. Crawler (portal) + colector de codigo (SIREC) + cruce KEV en una sola entidad: las KEV que el demo muestra.
  3. Portal -> SIREC -> BD por el mismo origen: consulta IUSI, orden de pago y solicitud LAIP que persiste.
  4. Cambio en vivo: con el FTP apagado se toma la linea base; se enciende el ProFTPD REAL y el sentinela avisa.
Al final deja el FTP como estaba. Solo conecta a la IP indicada (debe ser propia: privada o Tailscale).
Crea una orden de pago y una solicitud LAIP ficticias cada vez que corre.
"""
import json, os, socket, subprocess, sys, tempfile, time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DOCKER = os.path.join(RAIZ, "casos", "portal-muni-gt", "docker")
sys.path.insert(0, RAIZ)
from revital import sentinela  # noqa: E402

IP = os.environ.get("E2E_IP", "127.0.0.1")
PORTAL = os.environ.get("E2E_PORTAL", "http://%s:8080" % IP).rstrip("/")
PUERTO_PORTAL = int(PORTAL.rsplit(":", 1)[1]) if PORTAL.count(":") == 2 else 80
ENT = "MUNI-GT-E2E"
SAL = tempfile.mkdtemp(prefix="revital-e2e-")
ok, fallas = 0, []


def chk(cond, que, detalle=""):
    global ok
    if cond:
        ok += 1
        print("  [OK]    " + que)
    else:
        fallas.append(que)
        print("  [FALLA] %s %s" % (que, ("-> " + str(detalle)[:300]) if detalle else ""))


def revital(*args, timeout=600):
    r = subprocess.run([sys.executable, "-m"] + list(args), cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=timeout)
    return r.returncode, r.stdout


def compose(*args):
    return subprocess.run(["docker", "compose", "--profile", "cambio"] + list(args), cwd=DOCKER, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True, timeout=300)


def banner(puerto, timeout=3):
    try:
        with socket.create_connection((IP, puerto), timeout=timeout) as s:
            s.settimeout(timeout)
            return s.recv(256).decode("latin-1", "replace")
    except OSError:
        return ""


def api(ruta, datos=None):
    req = Request(PORTAL + "/sirec/api" + ruta, data=urlencode(datos).encode() if datos is not None else None)
    try:
        with urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except OSError as e:
        return 0, {"error": str(e)}


def leer(nombre):
    with open(os.path.join(SAL, nombre), encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ 0. el stack esta arriba
print("== Punta a punta MUNI-GT contra %s (portal %s) ==" % (IP, PORTAL))
st, est = api("/estado")
if st != 200:
    sys.exit("SIREC no responde en %s/sirec/api/estado (%s). Levanta el stack: cd %s && docker compose up -d" % (PORTAL, est, DOCKER))
ftp_estaba = "ProFTPD" in banner(21)
if ftp_estaba:
    print("  (el FTP estaba encendido: se apaga para la linea base y se deja encendido al final)")
    compose("stop", "ftp")
    time.sleep(1)

try:
    # ------------------------------------------------------------------ 1. colector de red
    print("-- 1. Colector de red --")
    puertos = "21,25,3306,6379,%d" % PUERTO_PORTAL
    rc, out = revital("revital.red", IP, "--puertos", puertos, "--entidad", ENT, "--out", SAL, "--autorizo")
    chk(rc == 0, "revital.red termina bien", out[-300:])
    inv = leer("inventario-red-%s.json" % IP.replace(".", "-"))
    comps = {(c["producto"], c["version"]) for c in inv["components"]}
    alertas = " | ".join(inv["extra"]["alertas"])
    chk("base de datos MySQL" in alertas, "alerta: MySQL expuesto a la red", alertas)
    chk("Redis" in alertas, "alerta: Redis expuesto a la red", alertas)
    chk(("Exim", "4.89") in comps, "banner: Exim 4.89", comps)
    chk(("MySQL", "5.5.62") in comps, "banner: MySQL 5.5.62", comps)
    chk(("Apache", "2.4.49") in comps, "proxy Apache 2.4.49 detectado delante del portal", comps)
    chk(not any(p == "ProFTPD" for p, _ in comps), "el FTP esta apagado antes del cambio en vivo", comps)

    # ------------------------------------------------------------------ 2. web + codigo + KEV
    print("-- 2. Crawler + codigo + cruce KEV --")
    rc, out = revital("revital.crawler", PORTAL, "--entidad", ENT, "--out", SAL, "--delay", "0.1")
    chk(rc == 0, "crawler recorre el portal", out[-300:])
    rc, out = revital("revital.codigo", os.path.join("casos", "portal-muni-gt", "backend", "sirec"), "--entidad", ENT, "--out", SAL)
    chk(rc == 0, "colector de codigo lee SIREC", out[-300:])
    rc, out = revital("revital.cves", "--out", SAL, "--entidad", ENT)
    chk(rc == 0, "cruce con KEV", out[-300:])
    h = leer("hallazgos-muni-gt-e2e.json")
    kev = {(x["cve"], x["producto"]) for x in h["hallazgos"] if x["en_kev"]}
    cves = {c for c, _ in kev}
    for cve, que in (("CVE-2019-10149", "Exim 4.89 (banner)"), ("CVE-2017-5638", "Struts 2.3.31 (codigo SIREC)"),
                     ("CVE-2021-44228", "Log4Shell (codigo SIREC)"), ("CVE-2022-22965", "Spring4Shell (codigo SIREC)"),
                     ("CVE-2021-41773", "Apache 2.4.49 (proxy)"), ("CVE-2018-7600", "Drupal 7.57 (portal)")):
        chk(cve in cves, "KEV %s: %s" % (cve, que), sorted(cves)[:40])
    rep = open(os.path.join(SAL, "reporte-muni-gt-e2e.md"), encoding="utf-8").read()
    chk("NO CUMPLE" in rep, "el reporte de la entidad dice NO CUMPLE")

    # ------------------------------------------------------------------ 3. portal -> SIREC -> BD
    print("-- 3. Portal -> SIREC -> base de datos --")
    st, f = api("/iusi?finca=F-1024")
    chk(st == 200 and f.get("saldo_pendiente") == 832.5, "IUSI F-1024 por el portal: saldo Q 832.50", f)
    st, o = api("/orden-pago", {"concepto": "agua", "referencia": "A-10006"})
    chk(st == 200 and o.get("orden", "").startswith("OP-2026-") and o.get("monto") == 605.56, "orden de pago de agua A-10006", o)
    st, s = api("/laip", {"nombre": "Prueba punta a punta (ficticio)", "descripcion": "Solicito el informe de ejecucion del presupuesto 2026."})
    folio = s.get("folio", "")
    st2, g = api("/laip/" + folio) if folio else (0, {})
    chk(st == 201 and st2 == 200 and g.get("estado") == "recibida", "solicitud LAIP %s guardada y consultable" % folio, (s, g))

    # ------------------------------------------------------------------ 4. cambio en vivo
    print("-- 4. Cambio en vivo (sentinela + ProFTPD real) --")
    sal_s = os.path.join(SAL, "sentinela")
    cfg = {"salida": sal_s, "objetivos": [{"entidad": ENT + "-VIVO", "tipo": "red", "destino": IP, "puertos": [21, 25, 3306, 6379]}]}
    e1 = sentinela.vuelta(cfg, sal_s)
    chk(e1 and e1[0]["ok"], "vuelta 1 del sentinela (linea base, FTP apagado)", e1)
    r = compose("up", "-d", "ftp")
    chk(r.returncode == 0, "encender el FTP (docker compose --profile cambio up -d ftp)", r.stdout[-300:])
    for _ in range(20):
        if "ProFTPD 1.3.5" in banner(21):
            break
        time.sleep(1)
    chk("ProFTPD 1.3.5" in banner(21), "ProFTPD 1.3.5 responde en :21")
    sentinela.vuelta(cfg, sal_s)
    eventos = []
    with open(os.path.join(sal_s, "alertas.jsonl"), encoding="utf-8") as fa:
        eventos = [json.loads(l) for l in fa if l.strip()]
    chk(any(e["tipo"] == "componente_nuevo" and "ProFTPD 1.3.5" in e["detalle"] for e in eventos), "sentinela: Aparecio ProFTPD 1.3.5", eventos)
    chk(any(e["tipo"] == "kev_nueva" and "CVE-2015-3306" in e["detalle"] for e in eventos), "sentinela: KEV nueva CVE-2015-3306", eventos)
finally:
    if not ftp_estaba:
        compose("stop", "ftp")
        print("  (FTP apagado otra vez: listo para el demo)")
    else:
        compose("up", "-d", "ftp")

print("== Resultado: %d OK, %d fallas (salidas en %s) ==" % (ok, len(fallas), SAL))
sys.exit(1 if fallas else 0)
