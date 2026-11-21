"""Colector de codigo/carpeta de ReVital: lee los archivos de una app legacy que DECLARAN versiones.

Evidencia mas precisa que adivinar desde fuera: web.config, pom.xml, composer.json/lock, package.json/lock,
requirements.txt, packages.config, DLL y JAR, librerias JS con version en el nombre y los archivos de version
de Drupal y WordPress. Solo lectura, solo stdlib (Python 3.8+).

Uso: python -m revital.codigo RUTA_APP [--entidad X] [--out salida]
Solo contra sistemas propios o con autorizacion.
"""
import argparse, json, os, re, sys
import xml.etree.ElementTree as ET

from revital import inventory

SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__", ".idea", "obj"}
MAX_ARCHIVOS, MAX_DLL = 50000, 300
JAR_RE = re.compile(r"^(.+?)-(\d[\w.]*)\.jar$", re.I)
JS_RE = re.compile(r"^(.+?)[-.](\d+\.\d+[\d.]*)(?:\.min)?\.js$", re.I)
# Version en el comentario de cabecera. jQuery se exige EXACTO ("jQuery JavaScript Library v1.4.4") para no confundir
# el nucleo con sus plugins (jquery.form 3.x, jquery.once 1.2...), que tienen otra numeracion.
JS_CABECERAS = (
    (re.compile(r"jQuery JavaScript Library v?(\d+\.\d+[\d.]*)", re.I), "jquery"),
    (re.compile(r"jQuery UI[^\r\n\d]{0,40}?v?(\d+\.\d+[\d.]*)", re.I), "jquery-ui"),
    (re.compile(r"\b(?:Prototype JavaScript framework|MooTools|Dojo Toolkit|YUI|Underscore|Backbone|Bootstrap|AngularJS|Modernizr)"
                r"[^\r\n\d]{0,40}?v?(\d+\.\d+[\d.]*)"), None),
)
DLL_VER = re.compile(rb"F\x00i\x00l\x00e\x00V\x00e\x00r\x00s\x00i\x00o\x00n\x00\x00*((?:[0-9.]\x00)+)")


def leer(path, limite=8_000_000):
    with open(path, "rb") as f:
        return f.read(limite)


def texto(path):
    return leer(path).decode("utf-8", "replace")


def limpiar(v):
    """'^2.3' / '>=1.0' / '~1.2.3' -> '2.3' / '1.0' / '1.2.3' (primera version que aparece)."""
    m = re.search(r"\d[\w.]*", v or "")
    return m.group(0) if m else ""


def web_config(t):
    out, alertas = [], []
    for v in re.findall(r'targetFramework\s*=\s*"v?([\d.]+)"', t):
        out.append((".NET Framework", v, "targetFramework"))
    for n, v in re.findall(r'assembly\s*=\s*"([\w.]+),\s*Version=([\d.]+)', t):
        out.append((n, v, "assembly"))
    if re.search(r'<compilation[^>]*debug\s*=\s*"true"', t, re.I):
        alertas.append("web.config: compilation debug=true (modo depuracion en produccion)")
    if re.search(r'<customErrors[^>]*mode\s*=\s*"Off"', t, re.I):
        alertas.append("web.config: customErrors mode=Off (muestra errores detallados al publico)")
    return out, alertas


def pom_xml(t):
    t = re.sub(r"\sxmlns(:\w+)?=\"[^\"]*\"", "", t, count=0)  # sin namespaces para buscar simple
    t = re.sub(r"\s[\w.-]+:[\w.-]+=\"[^\"]*\"", "", t)  # y sin atributos con prefijo (xsi:schemaLocation), que quedarian sin declarar
    try:
        raiz = ET.fromstring(t)
    except ET.ParseError:
        return [], ["pom.xml: no se pudo leer (XML invalido)"]
    props = {(p.tag): (p.text or "").strip() for p in raiz.findall("properties/*")}
    def res(v):
        return re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m.group(1), ""), (v or "").strip())
    out = []
    for d in raiz.iter("dependency"):
        a = d.findtext("artifactId")
        if a:
            out.append((a.strip(), res(d.findtext("version")), "dependency"))
    return out, []


def json_deps(t, claves, fuente, exacto=False):
    try:
        d = json.loads(t)
    except ValueError:
        return []
    out = []
    for c in claves:
        for n, v in (d.get(c) or {}).items():
            if "/" in n or not n.startswith(("php", "ext-")):
                out.append((n, v if exacto else limpiar(v), fuente))
    return out


def lock_composer(t):
    try:
        d = json.loads(t)
    except ValueError:
        return []
    return [(p["name"], p.get("version", "").lstrip("v"), "composer.lock") for p in d.get("packages", []) if "name" in p]


def lock_npm(t):
    try:
        d = json.loads(t)
    except ValueError:
        return []
    out = []
    for ruta, p in (d.get("packages") or {}).items():  # lockfile v2/v3
        if ruta and p.get("version"):
            out.append((ruta.split("node_modules/")[-1], p["version"], "package-lock.json"))
    for n, p in (d.get("dependencies") or {}).items():  # lockfile v1
        if isinstance(p, dict) and p.get("version"):
            out.append((n, p["version"], "package-lock.json"))
    return out


def escanear(raiz):
    comps, alertas, archivos, dlls = {}, [], [], 0

    def add(items, nombre, rel):
        for prod, ver, det in items:
            comps.setdefault((prod, ver, "%s (%s)" % (nombre, det)), rel)

    n = 0
    for dirpath, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            n += 1
            if n > MAX_ARCHIVOS:
                alertas.append("se alcanzo el tope de %d archivos; el resto no se reviso" % MAX_ARCHIVOS)
                return comps, alertas, n
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, raiz).replace(os.sep, "/")
            low = f.lower()
            try:
                if low == "web.config":
                    o, a = web_config(texto(p)); add(o, f, rel); alertas += a
                elif low == "pom.xml":
                    o, a = pom_xml(texto(p)); add(o, f, rel); alertas += a
                elif low == "composer.json":
                    add(json_deps(texto(p), ("require",), "composer.json restriccion"), f, rel)
                elif low == "composer.lock":
                    add(lock_composer(texto(p)), f, rel)
                elif low == "package.json":
                    add(json_deps(texto(p), ("dependencies",), "package.json restriccion"), f, rel)
                elif low == "package-lock.json":
                    add(lock_npm(texto(p)), f, rel)
                elif low == "requirements.txt":
                    add([(a, b, "pin") for a, b in re.findall(r"(?m)^\s*([\w.\-]+)\s*==\s*([\w.]+)", texto(p))], f, rel)
                elif low == "packages.config":
                    add([(a, b, "NuGet") for a, b in re.findall(r'<package[^>]*\bid="([^"]+)"[^>]*\bversion="([^"]+)"', texto(p))], f, rel)
                elif low == "bootstrap.inc":
                    add([("Drupal", v, "VERSION") for v in re.findall(r"define\('VERSION',\s*'([\d.]+)'", texto(p))], f, rel)
                elif low == "version.php" and "wp-includes" in rel:
                    add([("WordPress", v, "wp_version") for v in re.findall(r"\$wp_version\s*=\s*'([\d.]+)'", texto(p))], f, rel)
                elif low.endswith(".jar"):
                    m = JAR_RE.match(f)
                    if m:
                        add([(m.group(1), m.group(2), "nombre del archivo")], f, rel)
                elif low.endswith(".js"):
                    m = JS_RE.match(f)
                    if m:
                        add([(m.group(1).lower(), m.group(2), "nombre del archivo")], f, rel)
                    else:  # jquery.js sin version en el nombre: casi siempre la trae en el comentario de cabecera
                        cab = leer(p, 600).decode("utf-8", "replace")
                        for rx, prod in JS_CABECERAS:
                            h = rx.search(cab)
                            if h:
                                nombre = prod or re.sub(r"[^A-Za-z.]+", "", h.group(0).split()[0]).lower()
                                add([(nombre, h.group(1), "cabecera de .js")], "js", rel)
                                break
                elif low.endswith(".dll") and dlls < MAX_DLL:
                    dlls += 1
                    m = DLL_VER.search(leer(p))
                    if m:
                        v = m.group(1).decode("utf-16-le")
                        add([(f[:-4], v, "FileVersion")], f, rel)
            except OSError as e:
                alertas.append("no se pudo leer %s: %s" % (rel, e))
    return comps, alertas, n


def to_markdown(inv):
    x = inv["extra"]
    out = ["# Reporte ReVital (codigo): %s" % inv["target"], "", "Entidad: %s" % (inv["entidad"] or "-"),
           "Generado: %s" % inv["generado"], "Archivos revisados: %d" % x["archivos_revisados"], "",
           "## Componentes (versiones declaradas)", "", "| Producto | Version | Fuente | Donde |", "|---|---|---|---|"]
    out += ["| %(producto)s | %(version)s | %(fuente)s | %(donde)s |" % c for c in inv["components"]]
    if x["alertas"]:
        out += ["", "## Alertas de configuracion", ""] + ["- " + a for a in x["alertas"]]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ruta")
    ap.add_argument("--entidad", default="")
    ap.add_argument("--out", default="salida")
    a = ap.parse_args()
    if not os.path.isdir(a.ruta):
        ap.error("no es una carpeta: %s" % a.ruta)
    comps, alertas, n = escanear(a.ruta)
    inv = inventory.nuevo("codigo", os.path.abspath(a.ruta), a.entidad)
    inv["components"] = [inventory.componente(p, v, f, d) for (p, v, f), d in sorted(comps.items())]
    inv["extra"] = {"archivos_revisados": n, "alertas": sorted(set(alertas))}
    j = inventory.guardar(inv, a.out)
    md = os.path.join(a.out, "reporte-%s-codigo-%s.md" % (a.entidad or "sin-entidad", inventory.slug(inv["target"])))
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(inv))
    print("listo: %s y %s (%d componentes, %d alertas)" % (j, md, len(inv["components"]), len(alertas)))


if __name__ == "__main__":
    sys.exit(main())
