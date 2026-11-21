"""Evaluacion KEV/NVD sin red. Correr: python tests/test_cves.py"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import inventory
from revital.cves import catalogo, evaluar, normalizar, reporte, versiones as V

# --- versiones: numeros, no texto ---
assert V.comparar("10.0", "9.9") == 1          # como texto daria al reves
assert V.comparar("2.4.49", "2.4.49") == 0
assert V.comparar("7.0", "7") == 0
assert V.comparar("1.3.3c", "1.3.3") == 1      # letra = version posterior (ProFTPD, OpenSSL)
assert V.comparar("7.5-beta", "7.5") == -1     # beta = anterior a la final
assert V.en_rango("7.57", {"hasta_incl": "7.57"}) and not V.en_rango("7.58", {"hasta_incl": "7.57"})
assert V.en_rango("2.4.10", {"desde_incl": "2.4.0", "hasta_excl": "2.4.60"})
assert not V.en_rango("2.4.60", {"desde_incl": "2.4.0", "hasta_excl": "2.4.60"})
assert V.es_rama("7") and not V.es_rama("7.57")
assert V.rama_toca_rango("7", {"hasta_incl": "7.57"})
assert not V.rama_toca_rango("7", {"desde_incl": "8.5.0", "hasta_excl": "8.5.11"})

# --- nombres de los colectores -> CPE ---
alias = normalizar.cargar_alias()
assert normalizar.identificar("Apache", alias)[1] == ["apache:http_server"]
assert normalizar.identificar("apache http_server", alias)[1] == ["apache:http_server"]
assert normalizar.identificar("Microsoft-IIS", alias)[0] == "Microsoft IIS"
assert normalizar.identificar("Joomla", alias)[1] == ["joomla:joomla!"]
assert normalizar.identificar("Apache Tomcat", alias)[0] == "Apache Tomcat"
assert normalizar.identificar("Cosa Rara", alias) == (None, [])
assert normalizar.eol("Drupal", "7.57", alias, "2026-11-21") == ("7", "2025-01-05")
assert normalizar.eol("Drupal", "7.57", alias, "2024-01-01") is None   # antes de esa fecha si tenia soporte

# --- respuesta cruda del API 2.0 de NVD -> formato propio ---
crudo = {"id": "CVE-2010-20103", "descriptions": [{"lang": "en", "value": "backdoor"}],
         "metrics": {"cvssMetricV31": [{"type": "Primary", "cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"}}]},
         "configurations": [{"nodes": [{"cpeMatch": [
             {"vulnerable": True, "criteria": "cpe:2.3:a:proftpd:proftpd:1.3.3:c:*:*:*:*:*:*"},
             {"vulnerable": False, "criteria": "cpe:2.3:o:linux:linux_kernel:-:*:*:*:*:*:*:*"}]}]}]}
cid, d = catalogo.convertir_nvd(crudo)
assert cid == "CVE-2010-20103" and d["cvss"] == 9.8
assert d["afecta"] == [{"cpe": "proftpd:proftpd", "version": "1.3.3c"}], d["afecta"]
assert catalogo.es_nvd_crudo({"vulnerabilities": [{"cve": crudo}]})

# --- caso portal-muni-gt: salida real del crawler + catalogos de ejemplo ---
cat = catalogo.cargar(demo=True)
reglas = evaluar.cargar_reglas()
invs = inventory.cargar_todos(os.path.join(os.path.dirname(catalogo.__file__), "ejemplos"))
res = evaluar.evaluar(invs, cat, alias, reglas, "2026-11-21")
comps = {(c["producto"], c["version"]) for c in res["componentes"]}
assert ("Drupal", "7") not in comps and ("Drupal", "7.57") in comps      # rama descartada: se sabe la exacta
assert ("PHP", "") not in comps and ("PHP", "7.0.28") in comps          # sin version descartado: se sabe
assert ("Apache HTTP Server", "2.4.10") in comps and ("Apache HTTP Server", "2.4.49") in comps
criticos = {h["cve"] for h in res["hallazgos"] if h["nivel"] == 1}
assert criticos == {"CVE-2018-7600", "CVE-2021-41773", "CVE-2021-42013"}, criticos
assert all(h["en_kev"] and h["confianza"] == "confirmado" for h in res["hallazgos"])
cond = {(h["cve"], h["version"]) for h in res["condicionales"]}
assert cond == {("CVE-2024-38475", "2.4.10"), ("CVE-2024-38475", "2.4.49")}, cond
todos = {h["cve"] for h in res["hallazgos"] + res["condicionales"]}
assert "CVE-2019-6340" not in todos                                    # solo Drupal 8
assert {(c["producto"], c["rama"]) for c in res["eol"]} == {("Drupal", "7"), ("PHP", "7.0")}

out = tempfile.mkdtemp()
md, js = reporte.guardar("Muni San Ejemplo", invs, res, cat["info"], "2026-11-21", reglas, out)
texto = open(md, encoding="utf-8").read()
assert os.path.basename(md) == "reporte-muni-san-ejemplo.md"
assert "NO CUMPLE" in texto and "CVE-2018-7600" in texto and "catalogos de ejemplo" in texto
assert json.load(open(js, encoding="utf-8"))["entidad"] == "Muni San Ejemplo"
print("ok")
