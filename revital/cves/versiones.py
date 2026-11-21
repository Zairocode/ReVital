"""Comparar versiones sin librerias: '10.0' > '9.9', '1.3.3c' > '1.3.3', '7.5-beta' < '7.5'."""
import re

# sufijos que van ANTES de la version final. Las letras sueltas (OpenSSL 1.0.2k, ProFTPD 1.3.3c) van DESPUES.
PRE = ("dev", "alpha", "beta", "pre", "rc")


def partes(v):
    """'2.4.49' -> [(2,0,''), (4,0,''), (49,0,'')]; '1.3.3c' -> [..., (3,1,'c')]; '7.5-beta' -> [(7,0,''), (5,-1,'beta')]."""
    out = []
    for num, suf in re.findall(r"(\d+)([a-z]*)", (v or "").lower()):
        rango = 0 if not suf else (-1 if suf in PRE else 1)
        out.append((int(num), rango, suf))
    # sufijo separado por guion o punto: '7.5-beta' / '7.5.beta'
    m = re.search(r"\d[-_.]?(dev|alpha|beta|pre|rc)\d*$", (v or "").lower())
    if m and out and out[-1][1] == 0:
        n = out[-1][0]
        out[-1] = (n, -1, m.group(1))
    return out


def comparar(a, b):
    """-1, 0 o 1. Rellena con ceros: '7.0' == '7'."""
    pa, pb = partes(a), partes(b)
    largo = max(len(pa), len(pb))
    pa += [(0, 0, "")] * (largo - len(pa))
    pb += [(0, 0, "")] * (largo - len(pb))
    return (pa > pb) - (pa < pb)


def valida(v):
    return bool(partes(v))


def es_rama(v):
    """'7' (solo version mayor, ej. meta generator 'Drupal 7') no basta para confirmar un CVE."""
    return len(partes(v)) == 1


def en_rango(v, r):
    """r viene de NVD: {'version': '2.4.49'} o {'desde_incl'|'desde_excl'|'hasta_incl'|'hasta_excl': ...}."""
    if r.get("version"):
        return comparar(v, r["version"]) == 0
    if r.get("desde_incl") and comparar(v, r["desde_incl"]) < 0:
        return False
    if r.get("desde_excl") and comparar(v, r["desde_excl"]) <= 0:
        return False
    if r.get("hasta_incl") and comparar(v, r["hasta_incl"]) > 0:
        return False
    if r.get("hasta_excl") and comparar(v, r["hasta_excl"]) >= 0:
        return False
    return True


def rama_toca_rango(rama, r):
    """Para versiones incompletas ('7'): el rango tiene alguna version dentro de la rama 7.x."""
    inicio, fin = rama, str(partes(rama)[0][0] + 1)
    if r.get("version"):
        return comparar(r["version"], inicio) >= 0 and comparar(r["version"], fin) < 0
    bajo = r.get("desde_incl") or r.get("desde_excl")
    alto = r.get("hasta_incl") or r.get("hasta_excl")
    if alto and comparar(alto, inicio) < 0:
        return False
    if r.get("hasta_excl") and comparar(r["hasta_excl"], inicio) == 0:
        return False
    return not (bajo and comparar(bajo, fin) >= 0)
