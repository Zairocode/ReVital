"""Pruebas del generador de datos ficticios de SIREC. Correr: python3 casos/portal-muni-gt/backend/db/test_datos.py"""
import os, re, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import generar_datos as g

d1, d2 = g.generar(), g.generar()
assert d1 == d2, "con la misma semilla los datos deben ser identicos"

# volumen y marca de ficticio
assert 280 <= len(d1["contribuyentes"]) <= 320, len(d1["contribuyentes"])
assert all(c["nota"] == "DATO FICTICIO" for c in d1["contribuyentes"])
assert len({c["dpi"] for c in d1["contribuyentes"]}) == len(d1["contribuyentes"]), "DPI unicos"

# IUSI: tasa por millar segun valor fiscal y trimestres = iusi_anual / 4
for i in d1["inmuebles"]:
    v = i["valor_fiscal"]
    assert i["tasa_por_millar"] == (0 if v <= 2000 else 2 if v <= 20000 else 6 if v <= 70000 else 9), i
    tri = [t for t in d1["trimestres"] if t["finca"] == i["finca"]]
    assert len(tri) == 4 and abs(sum(t["monto"] for t in tri) - i["iusi_anual"]) < 0.02, (i, tri)
    assert re.fullmatch(r"F-\d{4,5}", i["finca"]), i["finca"]

fin = {i["finca"]: i for i in d1["inmuebles"]}
tri = lambda f: [t["estado"] for t in d1["trimestres"] if t["finca"] == f]
# datos semilla garantizados por el contrato (docs/features/sirec-api.md)
f = fin["F-1024"]
assert (f["valor_fiscal"], f["tasa_por_millar"], f["iusi_anual"], f["zona"]) == (185000.00, 9, 1665.00, 3), f
assert f["direccion"] == "4a avenida 7-21, zona 3, Soke"
assert tri("F-1024") == ["pagado", "pagado", "pendiente", "pendiente"]
assert g.saldo(d1, "F-1024") == 832.50
assert set(tri("F-2048")) == {"pagado"} and g.saldo(d1, "F-2048") == 0
assert "vencido" in tri("F-3072")
assert "F-0000" not in fin
laip = {s["folio"]: s for s in d1["laip"]}
assert laip["LAIP-2026-0101"]["estado"] == "resuelta" and laip["LAIP-2026-0140"]["estado"] == "en_tramite"

# usuarios de SIREC con MD5 sin sal (realista para la epoca; es parte de lo que el pitch muestra)
assert all(re.fullmatch(r"[0-9a-f]{32}", u["clave_md5"]) for u in d1["usuarios"]) and any(u["rol"] == "admin" for u in d1["usuarios"])

# el SQL generado es el que esta versionado (nadie edita 02-datos.sql a mano)
sql = g.a_sql(d1)
assert "INSERT INTO contribuyentes" in sql and "'F-1024'" in sql and "'LAIP-2026-0140'" in sql
ruta = os.path.join(AQUI, "initdb", "02-datos.sql")
assert open(ruta, encoding="utf-8").read() == sql, "02-datos.sql desactualizado: correr python3 generar_datos.py"
print("ok: %d contribuyentes, %d inmuebles, %d solicitudes LAIP" % (len(d1["contribuyentes"]), len(d1["inmuebles"]), len(d1["laip"])))
