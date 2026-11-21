"""Catalogos offline: CISA KEV (explotados activamente) y NVD (que versiones afecta cada CVE).

datos/kev.json      = el JSON de CISA tal cual (navegador: Ctrl+S, o --actualizar)
datos/nvd_min.json  = extracto de NVD en formato propio (lo genera --actualizar)
datos/*.json        = respuestas crudas del API de NVD guardadas desde el navegador; se convierten solas
Si datos/ esta vacio se usan los catalogos de ejemplo de ejemplos/ y el reporte lo avisa.
"""
import json, os, ssl, sys, time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from revital.cves import normalizar

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
EJEMPLOS = os.path.join(AQUI, "ejemplos")
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _leer(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- NVD: formato crudo del API 2.0 -> formato propio ----------

def convertir_nvd(cve):
    """Un item 'cve' del API 2.0 de NVD -> (id, {descripcion, cvss, severidad, afecta:[{cpe, rango...}]})."""
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
                r = {"cpe": normalizar.cpe_corto(p[3] + ":" + p[4])}
                if p[5] not in ("*", "-"):
                    r["version"] = p[5] + (p[6] if p[6] not in ("*", "-") else "")
                for k_nvd, k in (("versionStartIncluding", "desde_incl"), ("versionStartExcluding", "desde_excl"),
                                 ("versionEndIncluding", "hasta_incl"), ("versionEndExcluding", "hasta_excl")):
                    if cm.get(k_nvd):
                        r[k] = cm[k_nvd]
                if r not in afecta:
                    afecta.append(r)
    return cve["id"], {"descripcion": desc, "cvss": cvss, "severidad": sev, "afecta": afecta}


def es_nvd_crudo(d):
    v = d.get("vulnerabilities") if isinstance(d, dict) else None
    return bool(v) and isinstance(v[0], dict) and "cve" in v[0]


# ---------- carga ----------

def cargar(datos=DATOS, demo=False):
    """-> {'kev': {cveID: entrada}, 'nvd': {cveID: {...}}, 'info': {...}}"""
    info = {"ejemplo": False, "kev_version": "", "kev_fecha": "", "nvd_fuente": "", "nvd_cves": 0}
    kev_path = os.path.join(datos, "kev.json")
    if demo or not os.path.exists(kev_path):
        kev_path = os.path.join(EJEMPLOS, "kev_demo.json")
        info["ejemplo"] = True
    kev_raw = _leer(kev_path)
    kev = {v["cveID"]: v for v in kev_raw["vulnerabilities"]}
    info["kev_version"], info["kev_fecha"] = kev_raw.get("catalogVersion", ""), kev_raw.get("dateReleased", "")[:10]

    nvd, fuentes = {}, []
    archivos = [] if demo or not os.path.isdir(datos) else sorted(os.listdir(datos))
    for n in archivos:
        if not n.endswith(".json") or n == "kev.json":
            continue
        d = _leer(os.path.join(datos, n))
        if es_nvd_crudo(d):
            nvd.update(convertir_nvd(x["cve"]) for x in d["vulnerabilities"])
        elif isinstance(d, dict) and "cves" in d:
            nvd.update(d["cves"])
        else:
            continue
        fuentes.append(n)
    if not nvd:
        nvd = _leer(os.path.join(EJEMPLOS, "nvd_demo.json"))["cves"]
        fuentes, info["ejemplo"] = ["ejemplos/nvd_demo.json"], True
    info["nvd_fuente"], info["nvd_cves"] = ", ".join(fuentes), len(nvd)
    return {"kev": kev, "nvd": nvd, "info": info, "indice": indexar(nvd)}


def indexar(nvd):
    """cpe -> [(cve, rango)] para buscar rapido por producto."""
    idx = {}
    for cve, d in nvd.items():
        for r in d.get("afecta", []):
            idx.setdefault(r["cpe"], []).append((cve, r))
    return idx


# ---------- actualizar (requiere internet; correr en una maquina con red y copiar datos/) ----------

def _bajar(url, ctx, headers=None):
    req = Request(url, headers=dict({"User-Agent": "ReVital/0.1"}, **(headers or {})))
    with urlopen(req, timeout=120, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def actualizar(datos=DATOS, productos=None, insecure=False):
    """Baja KEV completo y, por cada producto de alias.json, los CVE de NVD que lo mencionan."""
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    os.makedirs(datos, exist_ok=True)
    print("Bajando CISA KEV...")
    kev = _bajar(KEV_URL, ctx)
    with open(os.path.join(datos, "kev.json"), "w", encoding="utf-8") as f:
        json.dump(kev, f, ensure_ascii=False)
    print("  %d vulnerabilidades, version %s" % (len(kev["vulnerabilities"]), kev.get("catalogVersion")))

    clave_api = os.environ.get("NVD_API_KEY", "")  # opcional; sin ella NVD permite pocas consultas por minuto
    pausa = 1 if clave_api else 6
    hdr = {"apiKey": clave_api} if clave_api else {}
    prods = normalizar.cargar_alias()[0]
    destino = os.path.join(datos, "nvd_min.json")
    previo = _leer(destino)["cves"] if os.path.exists(destino) else {}
    cves, fallos = dict(previo), []
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
    return not fallos


if __name__ == "__main__":
    sys.exit("Usar: python -m revital.cves --actualizar")
