"""Sentinela: entre dos vueltas detecta lo que cambio, lo deja en alertas.jsonl y ejecuta el comando propio.
Correr: python tests/test_sentinela.py"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import sentinela
from revital.panel import datos

subprocess.run([sys.executable, "-m", "revital.sentinela", "--demo"], check=True, stdout=subprocess.DEVNULL)
# el ejemplo que el panel muestra para copiar debe ser JSON valido (rutas de Windows con \\ escapadas)
ej = json.load(open(os.path.join(os.path.dirname(sentinela.__file__), "sentinela.ejemplo.json"), encoding="utf-8"))
assert {o["tipo"] for o in ej["objetivos"]} == {"web", "codigo", "red"}, ej


def hall(version_drupal, kev):
    return {"entidad": "MUNI-GT", "componentes": [{"producto": "Drupal", "version": version_drupal}],
            "hallazgos": [{"cve": c, "producto": "Drupal", "version": version_drupal, "en_kev": True, "nivel_txt": n} for c, n in kev]}


def guardar(salida, h):
    with open(os.path.join(salida, "hallazgos-muni-gt.json"), "w", encoding="utf-8") as f:
        json.dump(h, f)


salida = tempfile.mkdtemp()
marca = os.path.join(salida, "gancho.txt")
# el comando propio: un python que escribe lo que recibe en la variable de entorno
gancho = [sys.executable, "-c", "import os;open(r'%s','w').write(os.environ['REVITAL_ENTIDAD']+'|'+os.environ['REVITAL_ALERTAS'])" % marca]
cfg = {"salida": salida, "al_detectar_cambio": subprocess.list2cmdline(gancho)}

guardar(salida, hall("7.57", [("CVE-2018-7600", "CRITICO")]))
assert sentinela.registrar(cfg, salida, "MUNI-GT") == [], "la primera vuelta es solo linea base"
assert not os.path.exists(marca) and not datos.alertas(salida)

guardar(salida, hall("7.58", [("CVE-2018-7600", "CRITICO"), ("CVE-2020-1", "URGENTE")]))  # otra version + KEV nueva
ev = sentinela.registrar(cfg, salida, "MUNI-GT")
tipos = {e["tipo"] for e in ev}
assert {"version_cambiada", "kev_nueva"} <= tipos, tipos

al = datos.alertas(salida)
assert len(al) == len(ev) and al[0]["entidad"] == "MUNI-GT" and al[0]["ts"], al
assert os.path.exists(marca), "no se ejecuto el comando propio"
recibido = open(marca, encoding="utf-8").read()
assert recibido.startswith("MUNI-GT|") and "kev_nueva" in recibido, recibido
assert len(datos.historial(salida, "muni-gt")) == 2 and datos.historial(salida, "muni-gt")[-1]["linea_base"]

# sin cambios no hay ruido ni se vuelve a llamar al comando
os.remove(marca)
assert sentinela.registrar(cfg, salida, "MUNI-GT") == [] and not os.path.exists(marca)
# si el objetivo deja de responder (0 componentes) es una alerta, no "paso a cumplir"
vacio = {"entidad": "X", "componentes": {}, "kev": {}, "no_kev": 0, "cumple": False}
antes = {"entidad": "X", "componentes": {"Drupal": ["7.57"]}, "kev": {}, "no_kev": 0, "cumple": True}
antes = {"entidad": "X", "componentes": {"Drupal": ["7.57"], "Apache": ["2.4.49"]},
         "kev": {"CVE-2018-7600 | Drupal 7.57": "CRITICO", "CVE-2021-41773 | Apache 2.4.49": "CRITICO"}, "cumple": False}
assert [(e["tipo"], e["severidad"]) for e in sentinela.comparar(antes, vacio)] == [("sin_datos", "alta")],     "caerse NO es 'ya no aplica': no debe haber componente_quitado ni kev_resuelta"

# una entidad con VARIOS objetivos y uno caido: se alerta, el reporte dice INCOMPLETO y no se compara ni se guarda foto engañosa
import socket
bueno = tempfile.mkdtemp()
with open(os.path.join(bueno, "requirements.txt"), "w") as f:
    f.write("Django==1.4.5" + chr(10))
cerrado = socket.socket(); cerrado.bind(("127.0.0.1", 0)); muerto = cerrado.getsockname()[1]; cerrado.close()
sal2 = tempfile.mkdtemp()
est2 = sentinela.vuelta({"salida": sal2, "objetivos": [{"entidad": "MIXTA", "tipo": "codigo", "destino": bueno},
                                                       {"entidad": "MIXTA", "tipo": "web", "destino": "http://127.0.0.1:%d" % muerto}]}, sal2)
assert [o["ok"] for o in est2] == [True, False], est2
assert any(a["tipo"] == "objetivo_inalcanzable" for a in datos.alertas(sal2))
assert not datos.historial(sal2, "mixta"), "con un objetivo caido no se guarda foto ni se compara"
rep2 = open(os.path.join(sal2, "reporte-mixta.md"), encoding="utf-8").read()
assert "INCOMPLETO" in rep2 and "127.0.0.1:%d" % muerto in rep2, rep2[:400]
assert datos.leer(os.path.join(sal2, "hallazgos-mixta.json"))["sin_respuesta"][0]["target"].endswith(str(muerto))
assert sentinela.foto({"entidad": "X", "componentes": [], "hallazgos": []})["cumple"] is False

# el ciclo completo (vigilar) crea la carpeta y deja el estado para el panel, aunque no haya objetivos
nueva = os.path.join(tempfile.mkdtemp(), "no", "existe")
sentinela.vigilar({"salida": nueva, "objetivos": []}, una_vez=True)
est = datos.estado_sentinela(nueva)
assert est and est["en_marcha"] is False and est["ciclo"] == 1 and est["objetivos"] == [], est
# objetivo de RED: un FTP que aparece entre dos vueltas (el "cambio en vivo" del demo) -> componente nuevo + KEV nueva
import threading
def escuchar(puerto, banner):
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(("127.0.0.1", puerto)); srv.listen(4)
    def bucle():
        while True:
            try:
                c, _ = srv.accept()
            except OSError:
                return
            try:
                c.sendall(banner)
            finally:
                c.close()
    threading.Thread(target=bucle, daemon=True).start()
    return srv
libre = lambda: (lambda s: (s.bind(("127.0.0.1", 0)), s.getsockname()[1], s.close())[1])(socket.socket())
p_ssh, p_ftp = libre(), libre()
ssh = escuchar(p_ssh, b"SSH-2.0-OpenSSH_7.2\r\n")
sal3 = tempfile.mkdtemp()
cfg3 = {"salida": sal3, "objetivos": [{"entidad": "SERVIDOR-MUNI", "tipo": "red", "destino": "127.0.0.1", "puertos": [p_ssh, p_ftp]}]}
est3 = sentinela.vuelta(cfg3, sal3)
assert [o["ok"] for o in est3] == [True], est3
assert not [a for a in datos.alertas(sal3) if a["tipo"] != "objetivo_inalcanzable"], "primera vuelta = linea base"
ftp = escuchar(p_ftp, b"220 ProFTPD 1.3.5 Server (MuniSoke) [127.0.0.1]\r\n")
sentinela.vuelta(cfg3, sal3)
al3 = datos.alertas(sal3)
assert any(a["tipo"] == "componente_nuevo" and "ProFTPD" in a["detalle"] for a in al3), al3
assert any(a["tipo"] == "kev_nueva" and "CVE-2015-3306" in a["detalle"] for a in al3), al3
assert sentinela.vuelta({"salida": sal3, "objetivos": [{"entidad": "X", "tipo": "red", "destino": "8.8.8.8"}]}, sal3)[0]["ok"] is False, "red publica: se rechaza"
ssh.close(); ftp.close()
print("ok: linea base, cambios detectados, alertas y comando propio")
