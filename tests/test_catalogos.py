"""Los catalogos congelados bastan para el caso de demo y se leen SIN red. Correr: python tests/test_catalogos.py"""
import json, os, socket

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogos")


def sin_red(*a, **k):
    raise AssertionError("el test no debe tocar la red")


socket.socket = sin_red  # modo avion: cualquier intento de conexion falla el test
kev = json.load(open(os.path.join(D, "kev.json"), encoding="utf-8"))
nvd = json.load(open(os.path.join(D, "nvd-kev.json"), encoding="utf-8"))
assert kev["count"] == len(kev["vulnerabilities"]) == nvd["total"] and not nvd["sin_datos_nvd"]
por_id = {e["cveID"]: e for e in kev["vulnerabilities"]}

# CVE-2021-41773: Apache 2.4.49 exacto; ransomware conocido
assert por_id["CVE-2021-41773"]["knownRansomwareCampaignUse"] == "Known"
assert ("apache", "http_server", "2.4.49", "", "", "", "") in {tuple(c) for c in nvd["cves"]["CVE-2021-41773"]["cpes"]}
# CVE-2018-7600: Drupal hasta 7.57 incluida (rango)
assert ["drupal", "drupal", "*", "", "", "7.57", ""] in nvd["cves"]["CVE-2018-7600"]["cpes"]
assert nvd["cves"]["CVE-2018-7600"]["cvss"] >= 9.8
# CVE-2024-38475: Apache del backend (2.4.10 < 2.4.60)
assert any(c[:2] == ["apache", "http_server"] and c[6] == "2.4.60" for c in nvd["cves"]["CVE-2024-38475"]["cpes"])
print("ok", kev["catalogVersion"], "-", nvd["total"], "CVE, sin red")
