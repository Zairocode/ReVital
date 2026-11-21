"""Catalogos offline: CISA KEV (explotados activamente) y NVD (que versiones afecta cada CVE).

Fuente principal (la del equipo, congelada en el repo por scripts/actualizar_catalogos.py):
  catalogos/kev.json       catalogo CISA KEV completo
  catalogos/nvd-kev.json   NVD de todas las CVE que estan en KEV: CVSS y versiones afectadas
Extra opcional, local (no se sube al repo; lo genera --actualizar):
  revital/cves/datos/nvd_min.json  NVD de TODAS las CVE (no solo KEV) de los productos de alias.json
  revital/cves/datos/*.json        respuestas crudas del API de NVD guardadas desde el navegador
Sin catalogos/ se usan los de ejemplos/ y el reporte lo avisa.
"""
import json, os, ssl, sys, time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from revital.cves import normalizar

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
CATALOGOS = os.path.join(RAIZ, "catalogos")
DATOS = os.path.join(AQUI, "datos")
EJEMPLOS = os.path.join(AQUI, "ejemplos")
NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _leer(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _severidad(cvss):
    if cvss is None:
        return ""
    return "CRITICAL" if cvss >= 9 else "HIGH" if cvss >= 7 else "MEDIUM" if cvss >= 4 else "LOW"


def _limpio(v):
    return (v or "").replace("\\", "")


# ---------- formatos de NVD -> formato propio {descripcion, cvss, severidad, afecta:[{cpe, version|rangos}]} ----------

def convertir_nvd(cve):
    """Un item 'cve' crudo del API 2.0 de NVD -> (id, {...})."""
    desc = next((d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
    cvss, sev = None, ""
    metricas = cve.get("metrics", {})
    for k in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        ms = metricas.get(k) or []
        m = next((x for x in ms if x.get("type") == "Primary"), ms[0] if ms else None)
        if m:
            cvss = m["cvssData"].get("baseScore")
            sev = m["cvssData"].get("baseSeverity") or m.get("baseSeverity", "")
            break
    afecta = []
    for conf in cve.get("configurations", []):
        for nodo in conf.get("nodes", []):
            for cm in nodo.get("cpeMatch", []):
                if not cm.get("vulnerable"):
                    continue  # plataforma ("corre sobre Windows"), no el producto vulnerable
                p = cm["criteria"].split(":")
                if len(p) < 7:
                    continue
                r = _rango(p[3], p[4], p[5], cm.get("versionStartIncluding"), cm.get("versionStartExcluding"),
                           cm.get("versionEndIncluding"), cm.get("versionEndExcluding"),
                           p[6] if p[6] not in ("*", "-") else "")
                if r not in afecta:
                    afecta.append(r)
    return cve["id"], {"descripcion": desc, "cvss": cvss, "severidad": sev or _severidad(cvss), "afecta": afecta}


def _rango(vendor, producto, version, si, se, ei, ee, update=""):
    r = {"cpe": normalizar.cpe_corto(vendor + ":" + producto)}
    if version not in ("*", "-", ""):
        r["version"] = _limpio(version) + update
    for k, v in (("desde_incl", si), ("desde_excl", se), ("hasta_incl", ei), ("hasta_excl", ee)):
        if v:
            r[k] = _limpio(v)
    return r


def convertir_nvd_kev(d):
    """catalogos/nvd-kev.json (formato del equipo: cpes = [vendor, producto, version, startInc, startExc, endInc, endExc])."""
    out = {}
    for cve, x in d.get("cves", {}).items():
        afecta = [_rango(*c[:7]) for c in x.get("cpes", []) if len(c) >= 7]
        out[cve] = {"descripcion": "", "cvss": x.get("cvss") or None, "severidad": _severidad(x.get("cvss") or None),
                    "afecta": afecta}
    return out


def es_nvd_crudo(d):
    v = d.get("vulnerabilities") if isinstance(d, dict) else None
    return bool(v) and isinstance(v[0], dict) and "cve" in v[0]


# ---------- carga ----------

def cargar(datos=DATOS, demo=False, catalogos=CATALOGOS):
    """-> {'kev': {cveID: entrada}, 'nvd': {cveID: {...}}, 'indice': {cpe: [(cve, rango)]}, 'info': {...}}"""
    info = {"ejemplo": False, "kev_version": "", "kev_fecha": "", "nvd_fuente": "", "nvd_cves": 0}
    candidatos = [] if demo else [os.path.join(catalogos, "kev.json"), os.path.join(datos, "kev.json")]
    kev_path = next((p for p in candidatos if os.path.exists(p)), None)
    if not kev_path:
        kev_path, info["ejemplo"] = os.path.join(EJEMPLOS, "kev_demo.json"), True
    kev_raw = _leer(kev_path)
    kev = {v["cveID"]: v for v in kev_raw["vulnerabilities"]}
    info["kev_version"], info["kev_fecha"] = kev_raw.get("catalogVersion", ""), kev_raw.get("dateReleased", "")[:10]
    info["kev_fuente"] = os.path.relpath(kev_path, RAIZ)

    nvd, fuentes = {}, []
    if not demo:
        p = os.path.join(catalogos, "nvd-kev.json")
        if os.path.exists(p):
            nvd.update(convertir_nvd_kev(_leer(p)))
            fuentes.append("catalogos/nvd-kev.json")
        for n in sorted(os.listdir(datos)) if os.path.isdir(datos) else []:
            if not n.endswith(".json") or n == "kev.json":
                continue
            d = _leer(os.path.join(datos, n))
            if es_nvd_crudo(d):
                extra = dict(convertir_nvd(x["cve"]) for x in d["vulnerabilities"])
            elif isinstance(d, dict) and "cves" in d and "descargado" not in d:
                extra = d["cves"]
            else:
                continue
            nvd.update(extra)  # datos/ trae descripcion y CVE fuera de KEV; pisa al extracto KEV-only
            fuentes.append("revital/cves/datos/" + n)
    if not nvd:
        nvd = _leer(os.path.join(EJEMPLOS, "nvd_demo.json"))["cves"]
        fuentes, info["ejemplo"] = ["revital/cves/ejemplos/nvd_demo.json"], True
    info["nvd_fuente"], info["nvd_cves"] = ", ".join(fuentes), len(nvd)
    info["solo_kev"] = fuentes == ["catalogos/nvd-kev.json"]
    return {"kev": kev, "nvd": nvd, "info": info, "indice": indexar(nvd)}


def indexar(nvd):
    """cpe -> [(cve, rango)] para buscar rapido por producto."""
    idx = {}
    for cve, d in nvd.items():
        for r in d.get("afecta", []):
            idx.setdefault(r["cpe"], []).append((cve, r))
    return idx


# ---------- actualizar el extra de datos/ (requiere internet) ----------

def _bajar(url, ctx, headers=None):
    req = Request(url, headers=dict({"User-Agent": "ReVital/0.1"}, **(headers or {})))
    with urlopen(req, timeout=120, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def actualizar(datos=DATOS, productos=None, insecure=False):
    """Baja de NVD todas las CVE (no solo KEV) de cada producto de alias.json -> datos/nvd_min.json.
    KEV y el extracto KEV de NVD se actualizan con: python scripts/actualizar_catalogos.py"""
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    os.makedirs(datos, exist_ok=True)
    clave_api = os.environ.get("NVD_API_KEY", "")  # opcional; sin ella NVD permite pocas consultas por minuto
    pausa = 1 if clave_api else 6
    hdr = {"apiKey": clave_api} if clave_api else {}
    prods = normalizar.cargar_alias()[0]
    destino = os.path.join(datos, "nvd_min.json")
    cves = _leer(destino)["cves"] if os.path.exists(destino) else {}
    fallos = []
    for oficial, d in prods.items():
        if productos and not ({normalizar.clave(n) for n in d["nombres"] + [oficial]} & productos):
            continue
        for cpe in d["cpe"]:
            inicio = 0
            while True:
                q = urlencode({"virtualMatchString": "cpe:2.3:a:" + cpe, "resultsPerPage": 2000, "startIndex": inicio})
                print("NVD %s (desde %d)..." % (cpe, inicio))
                try:
                    r = _bajar(NVD_URL + "?" + q, ctx, hdr)
                except Exception as e:  # un producto que falla no tumba la actualizacion
                    print("  fallo: %s" % e)
                    fallos.append(cpe)
                    break
                for x in r.get("vulnerabilities", []):
                    k, v = convertir_nvd(x["cve"])
                    cves[k] = v
                inicio += r.get("resultsPerPage", 0)
                time.sleep(pausa)
                if not r.get("resultsPerPage") or inicio >= r.get("totalResults", 0):
                    break
    with open(destino, "w", encoding="utf-8") as f:
        json.dump({"generado": time.strftime("%Y-%m-%d %H:%M:%S"), "fuente": NVD_URL, "cves": cves}, f, ensure_ascii=False)
    print("Listo: %s (%d CVE)%s" % (destino, len(cves), "; fallaron: " + ", ".join(fallos) if fallos else ""))
    print("KEV se actualiza aparte: python scripts/actualizar_catalogos.py")
    return not fallos


if __name__ == "__main__":
    sys.exit("Usar: python -m revital.cves --actualizar")
