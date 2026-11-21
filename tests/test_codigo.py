"""Colector de codigo contra una app legacy falsa en carpeta. Correr: python tests/test_codigo.py"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import codigo, inventory

raiz = tempfile.mkdtemp()


def w(rel, contenido, modo="w"):
    p = os.path.join(raiz, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, modo + ("b" if isinstance(contenido, bytes) else ""), **({} if isinstance(contenido, bytes) else {"encoding": "utf-8"})) as f:
        f.write(contenido)


w("web.config", '<configuration><system.web><compilation debug="true" targetFramework="2.0"><assemblies>'
                '<add assembly="System.Web.Extensions, Version=3.5.0.0, Culture=neutral"/></assemblies></compilation>'
                '<customErrors mode="Off"/></system.web></configuration>')
w("pom.xml", '<project xmlns="http://maven.apache.org/POM/4.0.0"><properties><log4j.v>2.14.1</log4j.v></properties>'
             '<dependencies><dependency><groupId>org.apache.logging.log4j</groupId><artifactId>log4j-core</artifactId>'
             '<version>${log4j.v}</version></dependency></dependencies></project>')
w("composer.json", json.dumps({"require": {"php": ">=5.3", "symfony/symfony": "^2.3"}}))
w("composer.lock", json.dumps({"packages": [{"name": "monolog/monolog", "version": "v1.0.2"}]}))
w("package.json", json.dumps({"dependencies": {"lodash": "^4.17.4"}}))
w("package-lock.json", json.dumps({"packages": {"": {}, "node_modules/lodash": {"version": "4.17.4"}}}))
w("requirements.txt", "Django==1.4.5\nrequests>=2.0\n")
w("packages.config", '<packages><package id="log4net" version="1.2.10" targetFramework="net40" /></packages>')
w("includes/bootstrap.inc", "<?php define('VERSION', '7.57');")
w("wp-includes/version.php", "<?php $wp_version = '4.9.8';")
w("lib/jquery-1.4.2.min.js", "x")
w("misc/jquery.js", "/*! jQuery JavaScript Library v1.4.4 */ (function(){})();")
w("misc/jquery.form.js", "/* jQuery Form Plugin version: 3.09 */")
w("misc/ui/jquery.ui.core.min.js", "/*! jQuery UI 1.8.7 */")
w("lib/prototype.js", "/* Prototype JavaScript framework, version 1.6.0.3 */")
w("lib/log4j-core-2.14.1.jar", b"PK")
w("bin/Foo.dll", b"MZ\x00\x00" + "FileVersion".encode("utf-16-le") + b"\x00\x00\x00\x00" + "2.0.50727.5420".encode("utf-16-le") + b"\x00\x00")
w("node_modules/x/package.json", json.dumps({"dependencies": {"debe-ignorarse": "9.9.9"}}))

comps, alertas, n = codigo.escanear(raiz)
prods = {(p, v) for (p, v, _) in comps}
esperados = {(".NET Framework", "2.0"), ("System.Web.Extensions", "3.5.0.0"), ("log4j-core", "2.14.1"),
             ("symfony/symfony", "2.3"), ("monolog/monolog", "1.0.2"), ("lodash", "4.17.4"), ("Django", "1.4.5"),
             ("log4net", "1.2.10"), ("Drupal", "7.57"), ("WordPress", "4.9.8"), ("jquery", "1.4.2"), ("jquery", "1.4.4"), ("jquery-ui", "1.8.7"), ("prototype", "1.6.0.3"), ("Foo", "2.0.50727.5420")}
assert esperados <= prods, esperados - prods
assert ("jquery", "3.09") not in prods, "un plugin de jQuery no es jQuery"
assert not any(p == "debe-ignorarse" for p, _ in prods), "node_modules debe ignorarse"
assert not any(p == "php" for p, _ in prods), "php>=5.3 no es un componente"
assert len(alertas) == 2 and any("debug" in a for a in alertas) and any("customErrors" in a for a in alertas), alertas

# el inventario cumple el contrato y la salida no pisa otros destinos
out = tempfile.mkdtemp()
inv = inventory.nuevo("codigo", raiz, "MUNI-GT")
inv["components"] = [inventory.componente(p, v, f, d) for (p, v, f), d in sorted(comps.items())]
assert os.path.basename(inventory.guardar(inv, out)).startswith("inventario-codigo-")
assert "log4j-core" in codigo.to_markdown(dict(inv, extra={"archivos_revisados": n, "alertas": alertas}))
print("ok", len(comps), "componentes,", n, "archivos")
