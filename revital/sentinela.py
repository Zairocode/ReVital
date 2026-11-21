"""Sentinela de ReVital: vuelve a analizar los objetivos cada cierto tiempo, compara contra la vez anterior y avisa.

Detecta: componentes nuevos o con otra version, vulnerabilidades KEV nuevas o resueltas, cambio de cumplimiento y
objetivos que dejan de responder. Los avisos se ven en el panel (salida/alertas.jsonl) y, si se configura, ejecutan un
comando propio. Solo stdlib (Python 3.8+); pensado para dejarlo corriendo en un equipo viejo.

  python -m revital.sentinela --config sentinela.json            # vigila en bucle (cada `cada_minutos`)
  python -m revital.sentinela --config sentinela.json --una-vez  # una sola vuelta
  python -m revital.sentinela --demo                             # autoprueba de la comparacion, sin red

sentinela.json (ver revital/sentinela.ejemplo.json):
  {"cada_minutos": 60, "salida": "salida",
   "objetivos": [{"entidad": "MUNI-GT", "tipo": "web", "destino": "http://localhost:8080", "insecure": false},
                 {"entidad": "MUNI-GT", "tipo": "codigo", "destino": "C:\\\\inetpub\\\\portal"}],
   "al_detectar_cambio": "python mi_aviso.py"}     # opcional; recibe REVITAL_ENTIDAD y REVITAL_ALERTAS (JSON)
Solo contra sistemas propios o con autorizacion.
"""
import argparse, json, os, shlex, subprocess, sys, time

from revital import inventory

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEVERIDAD = {"info": 0, "media": 1, "alta": 2, "critica": 3}


def _leer(path, defecto=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def foto(hallazgos):
    """Resumen comparable de un hallazgos-<entidad>.json."""
    comps = {}
    for c in hallazgos.get("componentes", []):
        comps.setdefault(c["producto"], set()).add(c["version"] or "?")
    kev = {}
    for h in hallazgos.get("hallazgos", []):
        if h.get("en_kev"):
            kev["%s | %s %s" % (h["cve"], h["producto"], h["version"])] = h.get("nivel_txt", "")
    return {"entidad": hallazgos.get("entidad", ""), "componentes": {k: sorted(v) for k, v in comps.items()},
            "kev": kev, "no_kev": sum(1 for h in hallazgos.get("hallazgos", []) if not h.get("en_kev")),
            "cumple": not kev}


def comparar(prev, nuevo):
    """Eventos entre dos fotos. Sin foto previa no hay nada que comparar: es la linea base."""
    if not prev:
        return []
    ev = []

    def add(tipo, sev, detalle):
        ev.append({"tipo": tipo, "severidad": sev, "detalle": detalle})

    for prod in sorted(set(nuevo["componentes"]) | set(prev["componentes"])):
        a, b = prev["componentes"].get(prod), nuevo["componentes"].get(prod)
        if a is None:
            add("componente_nuevo", "media", "Aparecio %s %s" % (prod, ", ".join(b)))
        elif b is None:
            add("componente_quitado", "info", "Ya no se ve %s %s" % (prod, ", ".join(a)))
        elif a != b:
            add("version_cambiada", "media", "%s: %s -> %s" % (prod, ", ".join(a), ", ".join(b)))
    for k, niv in sorted(nuevo["kev"].items()):
        if k not in prev["kev"]:
            add("kev_nueva", "critica" if niv == "CRITICO" else "alta", "Vulnerabilidad explotada nueva: %s [%s]" % (k, niv))
    for k in sorted(set(prev["kev"]) - set(nuevo["kev"])):
        add("kev_resuelta", "info", "Ya no aplica: %s" % k)
    if prev.get("cumple") and not nuevo["cumple"]:
        add("cumplimiento", "alta", "Paso de CUMPLE a NO CUMPLE (%d KEV abiertas)" % len(nuevo["kev"]))
    elif not prev.get("cumple") and nuevo["cumple"]:
        add("cumplimiento", "info", "Paso a CUMPLE: no quedan KEV abiertas")
    return ev


def _historial(salida, slug):
    d = os.path.join(salida, "historial", slug)
    return d, (sorted(os.listdir(d)) if os.path.isdir(d) else [])


def _alertar(salida, entidad, eventos):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(salida, "alertas.jsonl"), "a", encoding="utf-8") as f:
        for e in eventos:
            f.write(json.dumps(dict(e, ts=ts, entidad=entidad), ensure_ascii=False) + "\n")


def _gancho(cfg, entidad, eventos):
    cmd = cfg.get("al_detectar_cambio")
    if not cmd or not [e for e in eventos if SEVERIDAD.get(e["severidad"], 0) >= 1]:
        return
    env = dict(os.environ, REVITAL_ENTIDAD=entidad, REVITAL_ALERTAS=json.dumps(eventos, ensure_ascii=False))
    try:  # sin shell: el comando lo define quien administra el sentinela, no entra nada de la red.
        # En Windows la linea se pasa entera (CreateProcess la interpreta); shlex.split deja comillas y rompe las rutas.
        subprocess.run(cmd if os.name == "nt" else shlex.split(cmd), env=env, timeout=60, cwd=RAIZ)
    except (OSError, subprocess.SubprocessError) as e:
        _alertar(cfg["salida"], entidad, [{"tipo": "gancho_fallo", "severidad": "media", "detalle": "El comando no corrio: %s" % e}])


def _correr(cmd, timeout):
    p = subprocess.run([sys.executable, "-m"] + cmd, cwd=RAIZ, timeout=timeout, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, (p.stdout or "")[-400:]


def vuelta(cfg, salida, timeout=900):
    """Un ciclo: re-analiza cada objetivo, evalua cada entidad, compara y avisa. -> estado de los objetivos."""
    os.makedirs(salida, exist_ok=True)
    estado, entidades = [], []
    for o in cfg["objetivos"]:
        ent = o["entidad"]
        if o["tipo"] == "web":
            cmd = ["revital.crawler", o["destino"], "--entidad", ent, "--out", salida, "--delay", "0.2"]
            cmd += ["--insecure"] if o.get("insecure") else []
        elif o["tipo"] == "codigo":
            cmd = ["revital.codigo", o["destino"], "--entidad", ent, "--out", salida]
        else:
            estado.append(dict(o, ok=False, detalle="tipo desconocido: %s" % o["tipo"]))
            continue
        try:
            rc, cola = _correr(cmd, timeout)
        except (OSError, subprocess.SubprocessError) as e:
            rc, cola = 1, str(e)
        estado.append(dict(o, ok=(rc == 0), detalle="" if rc == 0 else cola.strip()[-200:]))
        if rc != 0:
            _alertar(salida, ent, [{"tipo": "objetivo_inalcanzable", "severidad": "alta",
                                    "detalle": "No se pudo analizar %s (%s): %s" % (o["destino"], o["tipo"], cola.strip()[-120:])}])
        if ent not in entidades:
            entidades.append(ent)
    for ent in entidades:
        try:
            _correr(["revital.cves", "--out", salida, "--entidad", ent], timeout)
        except (OSError, subprocess.SubprocessError):
            continue
        registrar(cfg, salida, ent)
    return estado


def registrar(cfg, salida, ent):
    """Con el hallazgos-<entidad>.json ya generado: lo compara con la vuelta anterior, guarda la foto y avisa."""
    slug = inventory.slug(ent) or "sin-entidad"
    h = _leer(os.path.join(salida, "hallazgos-%s.json" % slug))
    if not h:
        return []
    nueva = foto(h)
    d, previos = _historial(salida, slug)
    prev = (_leer(os.path.join(d, previos[-1])) or {}).get("foto") if previos else None
    eventos = comparar(prev, nueva) if prev else []
    os.makedirs(d, exist_ok=True)
    # microsegundos en el nombre: dos vueltas en el mismo segundo no se pisan
    with open(os.path.join(d, time.strftime("%Y%m%d-%H%M%S") + "-%06d.json" % int((time.time() % 1) * 1e6)), "w", encoding="utf-8") as f:
        json.dump({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "foto": nueva, "eventos": eventos,
                   "linea_base": prev is None}, f, ensure_ascii=False, indent=1)
    if eventos:
        _alertar(salida, ent, eventos)
        _gancho(dict(cfg, salida=salida), ent, eventos)
    return eventos


def _estado(salida, **kw):
    os.makedirs(salida, exist_ok=True)
    p = os.path.join(salida, "sentinela-estado.json")
    actual = _leer(p, {}) or {}
    actual.update(kw)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(actual, f, ensure_ascii=False, indent=1)


def vigilar(cfg, una_vez=False):
    salida = cfg.get("salida") or "salida"
    cada = max(1, int(cfg.get("cada_minutos", 60)))
    ciclo = 0
    _estado(salida, pid=os.getpid(), iniciado=time.strftime("%Y-%m-%d %H:%M:%S"), cada_minutos=cada, en_marcha=True)
    try:
        while True:
            ciclo += 1
            _estado(salida, ciclo=ciclo, analizando=True)
            est = vuelta(cfg, salida)
            prox = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + cada * 60))
            _estado(salida, analizando=False, ultima_vuelta=time.strftime("%Y-%m-%d %H:%M:%S"), objetivos=est,
                    proxima_vuelta=None if una_vez else prox)
            print("vuelta %d lista (%d objetivos). %s" % (ciclo, len(est), "" if una_vez else "Proxima: " + prox))
            if una_vez:
                break
            time.sleep(cada * 60)
    except KeyboardInterrupt:
        print("sentinela detenido")
    finally:
        _estado(salida, en_marcha=False, analizando=False)


def demo():
    a = {"entidad": "X", "componentes": {"Drupal": ["7.57"], "PHP": ["7.0.28"]},
         "kev": {"CVE-1 | Drupal 7.57": "CRITICO"}, "no_kev": 3, "cumple": False}
    assert comparar(None, a) == []
    assert comparar(a, a) == []
    b = {"entidad": "X", "componentes": {"Drupal": ["7.58"], "jQuery": ["1.4.4"]},
         "kev": {"CVE-2 | jQuery 1.4.4": "URGENTE"}, "no_kev": 3, "cumple": False}
    tipos = {(e["tipo"], e["severidad"]) for e in comparar(a, b)}
    assert ("version_cambiada", "media") in tipos and ("componente_nuevo", "media") in tipos, tipos
    assert ("componente_quitado", "info") in tipos and ("kev_nueva", "alta") in tipos and ("kev_resuelta", "info") in tipos, tipos
    limpio = dict(b, kev={}, cumple=True)
    assert ("cumplimiento", "info") in {(e["tipo"], e["severidad"]) for e in comparar(b, limpio)}
    assert ("cumplimiento", "alta") in {(e["tipo"], e["severidad"]) for e in comparar(limpio, b)}
    f = foto({"entidad": "X", "componentes": [{"producto": "Drupal", "version": "7.57"}],
              "hallazgos": [{"cve": "C", "producto": "Drupal", "version": "7.57", "en_kev": True, "nivel_txt": "CRITICO"},
                            {"cve": "D", "producto": "Drupal", "version": "7.57", "en_kev": False}]})
    assert f["kev"] == {"C | Drupal 7.57": "CRITICO"} and f["no_kev"] == 1 and not f["cumple"], f
    print("ok")


def main():
    ap = argparse.ArgumentParser(description="Sentinela de ReVital")
    ap.add_argument("--config", default="sentinela.json")
    ap.add_argument("--una-vez", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    cfg = _leer(a.config)
    if not cfg or not cfg.get("objetivos"):
        sys.exit("No encuentro una configuracion valida en '%s'. Copia revital/sentinela.ejemplo.json y editalo." % a.config)
    vigilar(cfg, a.una_vez)


if __name__ == "__main__":
    main()
