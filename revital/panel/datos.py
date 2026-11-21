"""Lee lo que producen los colectores y la evaluacion (carpeta salida/). El panel no calcula nada: solo muestra."""
import io, json, os, time, zipfile

from revital import inventory

ORDEN_NIVEL = {"CRITICO": 0, "URGENTE (vencido)": 1, "URGENTE": 2, "ALTO (exploit publico)": 3, "ALTO": 4, "MEDIO": 5, "BAJO": 6}


def leer(path, defecto=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def resumen(h):
    """Numeros para las tarjetas de una entidad a partir de su hallazgos-<slug>.json."""
    hall = h.get("hallazgos", [])
    kev = [x for x in hall if x.get("en_kev")]
    return {"kev": len(kev), "ransomware": sum(1 for x in kev if x.get("nivel") == 1),
            "vencidas": sum(1 for x in kev if x.get("vencido")), "otras": len(hall) - len(kev),
            "condicionales": len(h.get("condicionales", [])), "componentes": len(h.get("componentes", [])),
            "eol": len(h.get("eol", [])), "cumple": not kev}


def entidades(salida):
    """Una fila por hallazgos-<slug>.json, la mas reciente primero."""
    out = []
    if not os.path.isdir(salida):
        return out
    for n in os.listdir(salida):
        if n.startswith("hallazgos-") and n.endswith(".json"):
            h = leer(os.path.join(salida, n))
            if h:
                p = os.path.join(salida, n)
                out.append({"slug": n[len("hallazgos-"):-len(".json")], "entidad": h.get("entidad", n), "h": h,
                            "r": resumen(h), "mtime": os.path.getmtime(p)})
    return sorted(out, key=lambda e: -e["mtime"])


def entidad(salida, slug):
    return next((e for e in entidades(salida) if e["slug"] == slug), None)


def inventarios(salida, nombre_entidad):
    """Inventarios crudos de los colectores de esa entidad."""
    out = []
    if os.path.isdir(salida):
        for n in sorted(os.listdir(salida)):
            if n.startswith("inventario-") and n.endswith(".json"):
                inv = leer(os.path.join(salida, n))
                if inv and (inv.get("entidad") or "").lower() == (nombre_entidad or "").lower():
                    out.append(dict(inv, _archivo=n))
    return out


def archivos(salida, slug, nombre_entidad):
    """Documentacion descargable de una entidad: reporte final, hallazgos, inventarios y reportes por colector."""
    out = []
    if not os.path.isdir(salida):
        return out
    inv_names = {i["_archivo"] for i in inventarios(salida, nombre_entidad)}
    for n in sorted(os.listdir(salida)):
        p = os.path.join(salida, n)
        if not os.path.isfile(p):
            continue
        base = n.lower()
        if n in ("reporte-%s.md" % slug, "hallazgos-%s.json" % slug):
            tipo = "Reporte final" if n.endswith(".md") else "Hallazgos (datos)"
        elif n in inv_names:
            tipo = "Inventario (%s)" % (n.split("-")[1] if "-" in n else "")
        elif base.startswith("reporte-") and base.endswith(".md") and inventory.slug(n[len("reporte-"):]).startswith(slug + "-"):
            tipo = "Reporte del colector"
        else:
            continue
        st = os.stat(p)
        out.append({"nombre": n, "tipo": tipo, "bytes": st.st_size, "fecha": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
    orden = {"Reporte final": 0, "Reporte del colector": 1, "Hallazgos (datos)": 2}
    return sorted(out, key=lambda a: (orden.get(a["tipo"], 3), a["nombre"]))


def zip_de(salida, slug, nombre_entidad):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for a in archivos(salida, slug, nombre_entidad):
            z.write(os.path.join(salida, a["nombre"]), "ReVital-%s/%s" % (slug, a["nombre"]))
    return buf.getvalue()


def ruta_segura(salida, nombre):
    """Solo archivos que estan directamente dentro de salida/ (evita ../ y rutas absolutas)."""
    if not nombre or nombre != os.path.basename(nombre) or nombre.startswith("."):
        return None
    p = os.path.join(salida, nombre)
    return p if os.path.isfile(p) else None


def historial(salida, slug, limite=20):
    d = os.path.join(salida, "historial", slug)
    if not os.path.isdir(d):
        return []
    return [leer(os.path.join(d, n), {}) for n in sorted(os.listdir(d))[-limite:]][::-1]


def alertas(salida, limite=40, slug=None, entidad=None):
    p = os.path.join(salida, "alertas.jsonl")
    out = []
    try:
        with open(p, encoding="utf-8") as f:
            for linea in f:
                try:
                    a = json.loads(linea)
                except ValueError:
                    continue
                if entidad is None or (a.get("entidad") or "").lower() == entidad.lower():
                    out.append(a)
    except OSError:
        pass
    return out[-limite:][::-1]


def estado_sentinela(salida):
    return leer(os.path.join(salida, "sentinela-estado.json"), None)
