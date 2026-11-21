"""python -m revital.cves [--out salida] [--entidad X] | --demo | --actualizar"""
import argparse, os, sys, time

from revital import inventory
from revital.cves import catalogo, evaluar, normalizar, reporte

AQUI = os.path.dirname(os.path.abspath(__file__))


def correr(out, entidad=None, datos=catalogo.DATOS, demo=False, hoy=None, entrada=None):
    hoy = hoy or time.strftime("%Y-%m-%d")
    entrada = entrada or out
    if not os.path.isdir(entrada) or not [n for n in os.listdir(entrada) if n.startswith("inventario-")]:
        sys.exit("No hay inventario-*.json en '%s'. Corre antes un colector (ej. python -m revital.crawler URL) "
                 "o prueba con: python -m revital.cves --demo" % entrada)
    cat = catalogo.cargar(datos, demo)
    alias, reglas = normalizar.cargar_alias(), evaluar.cargar_reglas()
    grupos = evaluar.por_entidad(inventory.cargar_todos(entrada), entidad)
    if not grupos:
        sys.exit("Ningun inventario es de la entidad '%s'" % entidad)
    i = cat["info"]
    if i["ejemplo"] and not demo:
        print("AVISO: usando catalogos de ejemplo (no hay catalogos/kev.json). Ver catalogos/LEEME.md")
    print("KEV %s (%s) | NVD: %s (%d CVE)" % (i["kev_version"], i["kev_fuente"], i["nvd_fuente"], i["nvd_cves"]))
    salidas = []
    for ent, invs in sorted(grupos.items()):
        res = evaluar.evaluar(invs, cat, alias, reglas, hoy)
        md, js = reporte.guardar(ent, invs, res, cat["info"], hoy, reglas, out)
        kev = [h for h in res["hallazgos"] if h["en_kev"]]
        print("\n%s: %d componentes, %d KEV abiertos, %d otras, %d a verificar, %d fuera de soporte, "
              "%d configuraciones inseguras" % (ent, len(res["componentes"]), len(kev), len(res["hallazgos"]) - len(kev),
                                               len(res["condicionales"]), len(res["eol"]), len(res["configuracion"])))
        for h in kev:
            print("  [%s] %s  %s %s" % (h["nivel_txt"], h["cve"], h["producto"], h["version"]))
        print("  -> %s" % md)
        salidas.append((ent, res, md))
    return salidas


def demo(out):
    """Caso portal-muni-gt (Drupal 7.57 + Apache 2.4.49/2.4.10) con catalogos de ejemplo; verifica el resultado."""
    salidas = correr(out, demo=True, hoy="2026-11-21", entrada=os.path.join(AQUI, "ejemplos"))
    _, res, _ = salidas[0]
    criticos = {h["cve"] for h in res["hallazgos"] if h["nivel"] == 1}
    assert {"CVE-2018-7600", "CVE-2021-41773"} <= criticos, criticos
    assert "CVE-2024-38475" in {h["cve"] for h in res["condicionales"]}
    assert "CVE-2019-6340" not in {h["cve"] for h in res["hallazgos"] + res["condicionales"]}  # es de Drupal 8
    assert {"Drupal", "PHP"} <= {c["producto"] for c in res["eol"]}
    print("\nok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ReVital: cruce de inventarios con NVD y CISA KEV")
    ap.add_argument("--out", default="salida", help="carpeta con los inventario-*.json y donde se escribe el reporte")
    ap.add_argument("--entidad", help="solo esta entidad (por defecto, un reporte por cada entidad encontrada)")
    ap.add_argument("--datos", default=catalogo.DATOS, help="carpeta con el extra opcional nvd_min.json")
    ap.add_argument("--hoy", help="fecha de evaluacion YYYY-MM-DD (por defecto hoy)")
    ap.add_argument("--demo", action="store_true", help="caso de ejemplo, sin red")
    ap.add_argument("--actualizar", action="store_true",
                    help="bajar de NVD todas las CVE de los productos de alias.json a datos/ (internet). "
                         "KEV: python scripts/actualizar_catalogos.py")
    ap.add_argument("--productos", help="con --actualizar: solo estos productos, separados por coma (ej. drupal,php)")
    ap.add_argument("--insecure", action="store_true", help="con --actualizar: no verificar certificados TLS")
    a = ap.parse_args()
    if a.actualizar:
        prods = {normalizar.clave(p) for p in a.productos.split(",")} if a.productos else None
        sys.exit(0 if catalogo.actualizar(a.datos, prods, a.insecure) else 1)
    if a.demo:
        demo(a.out)
    else:
        correr(a.out, a.entidad, a.datos, hoy=a.hoy)
