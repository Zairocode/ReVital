"""'producto' de los colectores -> producto oficial (CPE de NVD), usando alias.json."""
import json, os, re

from revital.cves import versiones

AQUI = os.path.dirname(os.path.abspath(__file__))


def clave(nombre):
    """'Microsoft-IIS' -> 'microsoft iis'; 'apache http_server' -> 'apache http server'."""
    return re.sub(r"\s+", " ", re.sub(r"[-_/]", " ", (nombre or "").lower())).strip()


def cargar_alias(path=None):
    with open(path or os.path.join(AQUI, "alias.json"), encoding="utf-8") as f:
        prods = json.load(f)["productos"]
    indice = {}
    for oficial, d in prods.items():
        for n in d["nombres"] + [oficial]:
            indice[clave(n)] = oficial
    return prods, indice


def cpe_corto(c):
    """'joomla:joomla\\!' -> 'joomla:joomla!' (NVD escapa algunos caracteres)."""
    return c.replace("\\", "").lower()


def identificar(producto, alias):
    """-> (nombre_oficial, [cpes]) o (None, []) si no esta en alias.json."""
    prods, indice = alias
    oficial = indice.get(clave(producto))
    if not oficial:
        return None, []
    return oficial, [cpe_corto(c) for c in prods[oficial]["cpe"]]


def eol(oficial, version, alias, hoy):
    """-> (rama, fecha_fin) si la version esta en una rama sin soporte a la fecha 'hoy' (YYYY-MM-DD)."""
    if not oficial or not version:
        return None
    pv = [p[0] for p in versiones.partes(version)]
    for rama, fin in alias[0][oficial].get("eol", {}).items():
        pr = [p[0] for p in versiones.partes(rama)]
        if pv[:len(pr)] == pr and fin <= hoy:
            return rama, fin
    return None
