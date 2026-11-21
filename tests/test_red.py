"""Colector de red contra servidores FALSOS locales (solo 127.0.0.1): banners de equipos viejos, alertas, seguridad y cruce con KEV.
Correr: python tests/test_red.py"""
import json, os, socket, subprocess, sys, tempfile, threading
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from revital import inventory, red

subprocess.run([sys.executable, "-m", "revital.red", "--demo"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)


def servidor(responder):
    """Escucha en un puerto libre de 127.0.0.1; responder(conexion) dice lo que diria el servicio."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(8)

    def bucle():
        while True:
            try:
                c, _ = s.accept()
            except OSError:
                return
            try:
                responder(c)
            except OSError:
                pass
            finally:
                c.close()
    threading.Thread(target=bucle, daemon=True).start()
    return s, s.getsockname()[1]


def dice(texto):
    return lambda c: c.sendall(texto)


def http(c):
    c.settimeout(2)
    c.recv(1024)
    c.sendall(b"HTTP/1.1 200 OK\r\nServer: Apache/2.2.15 (CentOS) PHP/5.3.3\r\nContent-Length: 0\r\n\r\n")


def mudo(c):
    c.settimeout(2)
    try:
        c.recv(1024)
    except OSError:
        pass


svs = {"ssh": servidor(dice(b"SSH-2.0-OpenSSH_5.3\r\n")), "ftp": servidor(dice(b"220 ProFTPD 1.3.5 Server (Debian) [10.0.0.9]\r\n")),
       "smtp": servidor(dice(b"220 mail.muni.local ESMTP Exim 4.69 Sat, 21 Nov 2026\r\n")), "telnet": servidor(dice(b"\xff\xfd\x18\xff\xfd\x20")),
       "mysql": servidor(dice(b"\x4a\x00\x00\x00\x0a5.1.73\x00\x01\x00\x00\x00")), "http": servidor(http), "mudo": servidor(mudo)}
cerrado = socket.socket(); cerrado.bind(("127.0.0.1", 0)); puerto_cerrado = cerrado.getsockname()[1]; cerrado.close()  # nadie escucha aqui
puertos = [p for _, p in svs.values()] + [puerto_cerrado]

equipos = red.escanear(["127.0.0.1"], puertos, timeout=1.0, espera=0.4, hilos=4)
assert len(equipos) == 1 and equipos[0]["ip"] == "127.0.0.1", equipos
por_serv = {p["servicio"]: p for p in equipos[0]["puertos"]}
assert len(equipos[0]["puertos"]) == 7, "7 abiertos y el cerrado no cuenta: %s" % [p["servicio"] for p in equipos[0]["puertos"]]
assert por_serv["SSH"]["productos"] == [("OpenSSH", "5.3")] and por_serv["FTP"]["productos"] == [("ProFTPD", "1.3.5")]
assert por_serv["SMTP"]["productos"] == [("Exim", "4.69")] and por_serv["MySQL"]["productos"] == [("MySQL", "5.1.73")] and "Telnet" in por_serv
assert ("Apache", "2.2.15") in por_serv["HTTP"]["productos"] and ("PHP", "5.3.3") in por_serv["HTTP"]["productos"]
assert "desconocido" in por_serv, "un puerto abierto que no dice nada se reporta, sin inventar un programa"

inv = a_inv = red.a_inventario(equipos, "127.0.0.1", "MUNI-GT")
assert inv["kind"] == "red" and {(c["producto"], c["version"]) for c in inv["components"]} >= {("OpenSSH", "5.3"), ("ProFTPD", "1.3.5"), ("Exim", "4.69"), ("MySQL", "5.1.73"), ("Apache", "2.2.15")}
al = " | ".join(inv["extra"]["alertas"])
for clave in ("Telnet (sin cifrar)", "FTP (sin cifrar)", "base de datos MySQL"):
    assert clave in al and "Servicio inseguro expuesto" in al, (clave, al)
assert "SSH" not in al and "HTTP" not in al, "SSH y HTTP no son una alerta por si solos"
assert "## Servicios expuestos" in red.to_markdown(inv)

# cruce con KEV (revital.cves): ProFTPD 1.3.5 -> CVE-2015-3306, Exim 4.69 -> CVE-2010-4344, Apache 2.2.15, y las alertas traen que hacer
salida = tempfile.mkdtemp()
inventory.guardar(inv, salida)
r = subprocess.run([sys.executable, "-m", "revital.cves", "--out", salida, "--entidad", "MUNI-GT"], cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
assert r.returncode == 0, r.stdout
h = json.load(open(os.path.join(salida, "hallazgos-muni-gt.json"), encoding="utf-8"))
kev = {(x["cve"], x["producto"]) for x in h["hallazgos"] if x["en_kev"]}
assert ("CVE-2015-3306", "ProFTPD") in kev and ("CVE-2010-4344", "Exim") in kev, kev
assert any(p == "Apache HTTP Server" for _, p in kev), kev
assert len(h["configuracion"]) >= 3 and all(c["recomendacion"] for c in h["configuracion"]), [c["detalle"] for c in h["configuracion"]]

# seguridad: sin --autorizo no se envia nada; un rango publico o gigante se rechaza
def correr(*a):
    return subprocess.run([sys.executable, "-m", "revital.red"] + list(a), cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
r = correr("127.0.0.1"); assert r.returncode != 0 and "--autorizo" in r.stdout and "ningun paquete" in r.stdout, r.stdout
r = correr("8.8.8.0/24", "--autorizo"); assert r.returncode != 0 and "No se escaneo nada" in r.stdout and "privada" in r.stdout, r.stdout
r = correr("100.128.0.0/30", "--autorizo"); assert r.returncode != 0 and "privada" in r.stdout, r.stdout  # justo fuera del rango Tailscale/CGNAT
r = correr("10.0.0.0/8", "--autorizo"); assert r.returncode != 0 and "maximo" in r.stdout, r.stdout
out = tempfile.mkdtemp()
r = correr("127.0.0.1", "--puertos", str(svs["ssh"][1]), "--entidad", "X", "--out", out, "--autorizo"); assert r.returncode == 0, r.stdout
assert any(n.startswith("inventario-red-127-0-0-1") for n in os.listdir(out)) and any(n.startswith("reporte-X-red-") for n in os.listdir(out)), os.listdir(out)
print("ok: %d servicios identificados, %d alertas, %d KEV" % (len(equipos[0]["puertos"]), len(inv["extra"]["alertas"]), len(kev)))
