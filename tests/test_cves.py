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
# nombres que emite el colector de codigo (revital/codigo.py)
assert normalizar.identificar("log4j-core", alias)[1] == ["apache:log4j"]
assert normalizar.identificar(".NET Framework", alias)[1] == ["microsoft:.net_framework"]
assert normalizar.identificar("symfony/symfony", alias)[1] == ["symfony:symfony"]
assert normalizar.identificar("jquery-ui", alias)[1] == ["jqueryui:jquery_ui"]
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
md, js = reporte.guardar("MUNI-GT", invs, res, cat["info"], "2026-11-21", reglas, out)
texto = open(md, encoding="utf-8").read()
assert os.path.basename(md) == "reporte-muni-gt.md"
assert "NO CUMPLE" in texto and "CVE-2018-7600" in texto and "catalogos de ejemplo" in texto
assert json.load(open(js, encoding="utf-8"))["entidad"] == "MUNI-GT"

# --- TLS obsoleto (crawler) y alertas de configuracion (colector de codigo) ---
web = inventory.nuevo("web", "https://portal.gob", "MUNI-GT")
web["components"] = [inventory.componente("TLS", "1.0", "protocolo obsoleto aceptado por el servidor", "portal.gob"),
                     inventory.componente("TLS", "1.2", "x", "portal.gob")]
cod = inventory.nuevo("codigo", "C:\\inetpub\\app", "MUNI-GT")
cod["extra"]["alertas"] = ["web.config: compilation debug=true (modo depuracion en produccion)",
                           "web.config: customErrors mode=Off (muestra errores detallados al publico)",
                           "no se pudo leer bin/x.dll: permiso denegado"]
r3 = evaluar.evaluar([web, cod], cat, alias, reglas, "2026-11-21")
conf = {(c["tipo"], c["detalle"]) for c in r3["configuracion"]}
assert ("Protocolo obsoleto", "El servidor acepta TLS 1.0") in conf, conf
assert not any("1.2" in d for _, d in conf)
assert all(c["recomendacion"] for c in r3["configuracion"]), r3["configuracion"]
assert len(r3["configuracion"]) == 3 and len(r3["notas_colectores"]) == 1
assert not any(c["producto"] == "TLS" for c in r3["sin_mapeo"])
txt = reporte.markdown("MUNI-GT", [web, cod], r3, cat["info"], "2026-11-21", reglas)
assert "## 4. Configuracion insegura" in txt and "RFC 8996" in txt and "permiso denegado" in txt

# --- catalogos congelados del equipo (catalogos/, formato nvd-kev.json) ---
nk = catalogo.convertir_nvd_kev({"cves": {"CVE-X": {"cvss": 9.8, "cpes": [
    ["drupal", "drupal", "*", "", "", "7.57", ""], ["apache", "http_server", "2.4.49", "", "", "", ""],
    ["cisco", "ios", "*", "", "", "12.2\\(15\\)zj3", ""]]}}})
assert nk["CVE-X"]["afecta"][:2] == [{"cpe": "drupal:drupal", "hasta_incl": "7.57"},
                                     {"cpe": "apache:http_server", "version": "2.4.49"}], nk
assert nk["CVE-X"]["afecta"][2]["hasta_incl"] == "12.2(15)zj3" and nk["CVE-X"]["severidad"] == "CRITICAL"
if os.path.exists(os.path.join(catalogo.CATALOGOS, "kev.json")):
    real = catalogo.cargar(datos=tempfile.mkdtemp())  # solo catalogos/, sin el extra local de datos/
    assert not real["info"]["ejemplo"] and real["info"]["solo_kev"]
    r2 = evaluar.evaluar(invs, real, alias, reglas, "2026-11-21")
    crit = {h["cve"] for h in r2["hallazgos"] if h["nivel"] == 1}
    assert {"CVE-2018-7600", "CVE-2018-7602", "CVE-2021-41773", "CVE-2021-42013", "CVE-2021-40438"} <= crit, crit
    assert all(h["en_kev"] for h in r2["hallazgos"])
    print("catalogos/: KEV %s, %d hallazgos KEV en el caso" % (real["info"]["kev_version"], len(r2["hallazgos"])))
print("ok")
