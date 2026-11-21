"""Sentinela: entre dos vueltas detecta lo que cambio, lo deja en alertas.jsonl y ejecuta el comando propio.
Correr: python tests/test_sentinela.py"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import sentinela
from revital.panel import datos

subprocess.run([sys.executable, "-m", "revital.sentinela", "--demo"], check=True, stdout=subprocess.DEVNULL)


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
tipos_vacio = {(e["tipo"], e["severidad"]) for e in sentinela.comparar(antes, vacio)}
assert ("sin_datos", "alta") in tipos_vacio and not [t for t, _ in tipos_vacio if t == "cumplimiento"], tipos_vacio
assert sentinela.foto({"entidad": "X", "componentes": [], "hallazgos": []})["cumple"] is False

# el ciclo completo (vigilar) crea la carpeta y deja el estado para el panel, aunque no haya objetivos
nueva = os.path.join(tempfile.mkdtemp(), "no", "existe")
sentinela.vigilar({"salida": nueva, "objetivos": []}, una_vez=True)
est = datos.estado_sentinela(nueva)
assert est and est["en_marcha"] is False and est["ciclo"] == 1 and est["objetivos"] == [], est
print("ok: linea base, cambios detectados, alertas y comando propio")
