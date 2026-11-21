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

# --- parche, mitigacion y Exploit-DB ---
hh = {x["cve"]: x for x in res["hallazgos"]}
assert hh["CVE-2018-7600"]["parche"].startswith("Actualizar Drupal a una version posterior a 7.57")
assert "no tiene soporte" in hh["CVE-2018-7600"]["parche"]                            # Drupal 7 es EOL
assert hh["CVE-2021-41773"]["parche"] == "Actualizar Apache HTTP Server a una version posterior a 2.4.49."
assert hh["CVE-2021-42013"]["parche"] == "Actualizar Apache HTTP Server a una version posterior a 2.4.50."
assert "Require all denied" in hh["CVE-2021-41773"]["mitigacion"] and "RewriteCond" in hh["CVE-2021-41773"]["regla"]
assert [e[0] for e in hh["CVE-2021-41773"]["exploits"]] == [50383, 50512]
assert [e[0] for e in hh["CVE-2018-7600"]["exploits"]] == [44482, 44448, 44449]   # Metasploit primero, sin duplicados
assert hh["CVE-2018-7600"]["exploit_metasploit"] and hh["CVE-2018-7600"]["alias"] == "Drupalgeddon2"
assert not hh["CVE-2021-41773"]["exploit_metasploit"] and hh["CVE-2021-41773"]["alias"] == ""
# un indice viejo (5 campos por exploit) se sigue leyendo
assert catalogo.edb([1, 1, "webapps", "2020-01-01", "X"], catalogo.EDB_MSF, 0) == 0
assert evaluar.parche("X", {"hasta_excl": "2.4.60"}) == "Actualizar X a 2.4.60 o posterior."
# nivel 4: fuera de KEV pero con exploit publico; un exploit solo DoS no cuenta
assert evaluar.nivel(False, {}, 5.0, "2026-11-21", reglas, [[1, 1, "webapps", "", ""]]) == 4
assert evaluar.nivel(False, {}, 5.0, "2026-11-21", reglas, [[1, 1, "dos", "", ""]]) == 7
assert evaluar.nivel(False, {}, 9.8, "2026-11-21", reglas) == 5
# importador: CSV con el formato de files_exploits.csv
csv_txt = ("id,file,description,date_published,author,type,platform,port,date_added,date_updated,verified,codes,tags,aliases\n"
           "1,a,\"X - RCE\",2020-01-01,a,webapps,php,80,,,1,CVE-2020-0001;OSVDB-9,Remote,\n"
           "1,a,\"X - RCE\",2020-01-01,a,webapps,php,80,,,1,CVE-2020-0001,Metasploit Framework (MSF),Xgeddon\n"
           "2,b,\"Y (CVE-2019-0002) - DoS\",2019-01-01,b,dos,linux,,,,0,,,\n")
ix = catalogo.indexar_exploitdb(csv_txt)
assert ix == {"CVE-2020-0001": [[1, 1, "webapps", "2020-01-01", "X - RCE", "php", "80", 1, "Xgeddon"]],
              "CVE-2019-0002": [[2, 0, "dos", "2019-01-01", "Y (CVE-2019-0002) - DoS", "linux", "", 0, ""]]}, ix

out = tempfile.mkdtemp()
md, js = reporte.guardar("MUNI-GT", invs, res, cat["info"], "2026-11-21", reglas, out)
texto = open(md, encoding="utf-8").read()
assert os.path.basename(md) == "reporte-muni-gt.md"
assert "NO CUMPLE" in texto and "CVE-2018-7600" in texto and "catalogos de ejemplo" in texto
assert "## 2. Como corregir" in texto and "EDB-50383 (verificado)" in texto and "RewriteCond" in texto
assert "CVE-2018-7600 (Drupalgeddon2)" in texto and "EDB-44482 (Metasploit, verificado)" in texto
assert "[EDB-44482](https://www.exploit-db.com/exploits/44482)" in texto
assert json.load(open(js, encoding="utf-8"))["entidad"] == "MUNI-GT"

# --- cruce automatico por nombre exacto de NVD (productos que no estan en alias.json) ---
auto = normalizar.indice_automatico(["microsoft:windows_7", "microsoft:exchange_server", "acme:server", "otra:server", "x:ab"])
assert auto["windows 7"] == ["microsoft:windows_7"]                       # 'Windows 7' del colector host
assert auto["microsoft exchange server"] == ["microsoft:exchange_server"]  # fabricante + producto
assert "server" not in auto                                               # ambiguo: dos fabricantes
assert "acme server" in auto and "ab" not in auto                         # nombre muy corto: ignorado
w7 = inventory.nuevo("host", "PC-1", "MUNI-GT")
w7["components"] = [inventory.componente("Windows 7", "6.1.7601", "registro", "PC-1"),
                    inventory.componente("Cosa Rara", "1.0", "x", "PC-1")]
r_auto = evaluar.evaluar([w7], cat, alias, reglas, "2026-11-21")
assert [c["mapeo"] for c in r_auto["componentes"] if c["producto"] == "Windows 7"] == ["automatico"] or \
    not cat["indice"].get("microsoft:windows_7")                          # los datos demo no traen Windows
assert any(c["producto"] == "Cosa Rara" for c in r_auto["sin_mapeo"])
assert {c["mapeo"] for c in res["componentes"]} == {"alias"}               # el caso web no cambia

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
assert "## 5. Configuracion insegura" in txt and "RFC 8996" in txt and "permiso denegado" in txt

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
    r3 = evaluar.evaluar([w7], real, alias, reglas, "2026-11-21")
    w7h = {h["cve"] for h in r3["hallazgos"] if h["producto"] == "Windows 7"}
    assert "CVE-2019-0708" in w7h and len(w7h) > 50, len(w7h)             # BlueKeep, por cruce automatico
print("ok")
