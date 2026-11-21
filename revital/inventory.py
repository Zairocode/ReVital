"""Contrato comun: todo colector (web, host, red, codigo) produce un inventario con este formato."""
import json, os, re, time

KINDS = ("web", "host", "red", "codigo")


def componente(producto, version="", fuente="", donde=""):
    """Una pieza de tecnologia detectada. version vacia = desconocida."""
    return {"producto": producto, "version": version, "fuente": fuente, "donde": donde}


def nuevo(kind, target, entidad=""):
    assert kind in KINDS, kind
    return {"kind": kind, "target": target, "entidad": entidad,
            "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
            "components": [], "extra": {}}


def slug(target):
    """'http://localhost:8080/x' -> 'localhost-8080-x'; sirve para nombrar archivos por objetivo."""
    return re.sub(r"[^a-z0-9]+", "-", target.lower().split("://")[-1])[:40].strip("-") or "destino"


def guardar(inv, out="salida", nombre=None):
    """Guarda salida/inventario-<kind>-<destino>.json. Dos objetivos distintos del mismo tipo no se pisan;
    volver a correr el mismo objetivo actualiza su archivo."""
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, nombre or "inventario-%s-%s.json" % (inv["kind"], slug(inv["target"])))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=2, ensure_ascii=False)
    return path


def cargar_todos(out="salida"):
    """Lee todos los inventario-*.json de la carpeta (los consume reglas-cisa-cves y el reporte)."""
    return [json.load(open(os.path.join(out, n), encoding="utf-8"))
            for n in sorted(os.listdir(out)) if n.startswith("inventario-") and n.endswith(".json")]
