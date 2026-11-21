"""Descarga y congela los catalogos que usa la evaluacion, para que la demo corra SIN internet.

  catalogos/kev.json      catalogo CISA KEV completo (qué CVE se explotan hoy, acción requerida, fecha límite)
  catalogos/nvd-kev.json  extracto de NVD solo de las CVE que están en KEV: CVSS y rangos de versión afectados

Se corre UNA vez con internet y el resultado se commitea. Solo stdlib (Python 3.8+).
  python scripts/actualizar_catalogos.py            # descarga
  python scripts/actualizar_catalogos.py --check    # muestra versión/fecha de lo congelado (sirve offline)
Con NVD_API_KEY en el entorno la descarga es más rápida (opcional; sin clave se espera entre páginas).
"""
import argparse, json, os, sys, time
from urllib.request import Request, urlopen

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0?hasKev&resultsPerPage=2000&startIndex=%d"
DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogos")


def get(url, headers=None, intentos=4):
    for i in range(intentos):
        try:
            return urlopen(Request(url, headers=dict({"User-Agent": "ReVital-catalogos/0.1"}, **(headers or {}))), timeout=120).read()
        except Exception as e:  # NVD responde 403/503 si se pide demasiado rapido
            if i == intentos - 1:
                raise
            print("  reintento %d (%s)" % (i + 1, e))
            time.sleep(10 * (i + 1))


def reducir(cve):
    """Una CVE de NVD -> {cvss, cpes:[[vendor, producto, version, startInc, startExc, endInc, endExc], ...]}"""
    cvss = 0.0
    for clave in ("cvssMetricV31", "cvssMetricV40", "cvssMetricV30", "cvssMetricV2"):
        for m in cve.get("metrics", {}).get(clave, []):
            cvss = max(cvss, m.get("cvssData", {}).get("baseScore", 0.0))
        if cvss:
            break
    cpes = set()
    for cfg in cve.get("configurations", []):
        for nodo in cfg.get("nodes", []):
            for cm in nodo.get("cpeMatch", []):
                if not cm.get("vulnerable"):
                    continue
                p = cm["criteria"].split(":")  # cpe:2.3:part:vendor:producto:version:...
                if p[2] not in ("a", "o"):
                    continue
                cpes.add((p[3], p[4], p[5], cm.get("versionStartIncluding", ""), cm.get("versionStartExcluding", ""),
                          cm.get("versionEndIncluding", ""), cm.get("versionEndExcluding", "")))
    return {"cvss": cvss, "cpes": sorted(cpes)}


def descargar():
    os.makedirs(DIR, exist_ok=True)
    print("KEV ...")
    kev = get(KEV_URL)
    k = json.loads(kev.decode("utf-8"))
    with open(os.path.join(DIR, "kev.json"), "wb") as f:
        f.write(kev)
    print("  %d vulnerabilidades, catalogo %s" % (k["count"], k["catalogVersion"]))

    headers = {"apiKey": os.environ["NVD_API_KEY"]} if os.environ.get("NVD_API_KEY") else {}
    espera = 1 if headers else 7
    cves, inicio, total = {}, 0, None
    while total is None or inicio < total:
        print("NVD desde %d ..." % inicio)
        d = json.loads(get(NVD_URL % inicio, headers).decode("utf-8"))
        total = d["totalResults"]
        for v in d["vulnerabilities"]:
            cves[v["cve"]["id"]] = reducir(v["cve"])
        inicio += d["resultsPerPage"]
        if inicio < total:
            time.sleep(espera)
    faltan = sorted({e["cveID"] for e in k["vulnerabilities"]} - set(cves))
    out = {"descargado": time.strftime("%Y-%m-%d"), "kev_catalogVersion": k["catalogVersion"],
           "total": len(cves), "sin_datos_nvd": faltan, "cves": cves}
    with open(os.path.join(DIR, "nvd-kev.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    print("nvd-kev.json: %d CVE (%d KEV sin datos de version en NVD aun)" % (len(cves), len(faltan)))


def check():
    for nombre in ("kev.json", "nvd-kev.json"):
        p = os.path.join(DIR, nombre)
        if not os.path.exists(p):
            print("FALTA", p)
            sys.exit(1)
    k = json.load(open(os.path.join(DIR, "kev.json"), encoding="utf-8"))
    n = json.load(open(os.path.join(DIR, "nvd-kev.json"), encoding="utf-8"))
    print("KEV catalogo %s (%d CVE) | NVD extracto descargado %s (%d CVE, %.1f MB)" % (
        k["catalogVersion"], k["count"], n["descargado"], n["total"],
        os.path.getsize(os.path.join(DIR, "nvd-kev.json")) / 1e6))
    if n["kev_catalogVersion"] != k["catalogVersion"]:
        print("AVISO: kev.json y nvd-kev.json son de catalogos distintos; vuelve a descargar")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    check() if a.check else descargar()
