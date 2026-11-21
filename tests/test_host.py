"""Colector de equipo: interpreta un Windows 7 de oficina (sin leer nada real) y lo cruza con revital.cves.
Corre en cualquier SO. Correr: python tests/test_host.py"""
import json, os, subprocess, sys, tempfile
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from revital import host, inventory

subprocess.run([sys.executable, "-m", "revital.host", "--demo"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)

raw = {"equipo": "PC-CONTA-01",
       "os": {"ProductName": "Windows 7 Professional", "CurrentVersion": "6.1", "CurrentBuild": "7601", "CSDVersion": "Service Pack 1"},
       "iis": {"MajorVersion": 7, "MinorVersion": 5}, "ie": {"version": "8.0.7601.17514"}, "dotnet": ["3.5.30729.5420"],
       "programas": [{"nombre": "Adobe Reader 9.5.0", "version": "9.5.0", "editor": "Adobe"},
                     {"nombre": "WinRAR 5.00 (64-bit)", "version": "5.00.0", "editor": "win.rar"},
                     {"nombre": "Adobe Flash Player 11 ActiveX", "version": "11.2.202.235", "editor": "Adobe"}],
       "seguridad": {"smb1": None, "rdp_bloqueado": 0, "uac": 1}, "hotfixes": [{"id": "KB2999226", "fecha": "2016-01-12"}],
       "puertos": [{"direccion": "0.0.0.0", "puerto": 23, "pid": "4"}]}
salida = tempfile.mkdtemp()
inv = host.a_inventario(raw, "MUNI-GT", "2026-11-21")
assert inv["kind"] == "host" and inv["target"] == "PC-CONTA-01"
inventory.guardar(inv, salida)

r = subprocess.run([sys.executable, "-m", "revital.cves", "--out", salida, "--entidad", "MUNI-GT"], cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
assert r.returncode == 0, r.stdout
h = json.load(open(os.path.join(salida, "hallazgos-muni-gt.json"), encoding="utf-8"))

kev = {(x["cve"], x["producto"]) for x in h["hallazgos"] if x["en_kev"]}
assert ("CVE-2023-38831", "WinRAR") in kev, "WinRAR 5.00 < 6.23"
assert any(p == "Adobe Flash Player" for _, p in kev) and any(p == "Adobe Acrobat Reader" for _, p in kev), kev
assert ("Internet Explorer", "8") in {(c["producto"], c["version"]) for c in h["eol"]}, h["eol"]  # IE 8: sin soporte desde 2016
cfg = {c["detalle"].split(":")[0].split(" (")[0]: c for c in h["configuracion"]}
assert len(h["configuracion"]) == 5, [c["detalle"] for c in h["configuracion"]]
assert all(c["recomendacion"] for c in h["configuracion"]), "cada alerta del equipo debe traer que hacer"
assert any("Windows 7" in c["detalle"] for c in h["configuracion"]) and any("Telnet" in c["detalle"] for c in h["configuracion"])
print("ok: Windows 7 -> %d KEV abiertas, %d sin soporte, %d configuraciones inseguras" % (len(kev), len(h["eol"]), len(h["configuracion"])))
