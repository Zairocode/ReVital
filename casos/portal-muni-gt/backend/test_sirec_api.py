"""Prueba del contrato de SIREC (docs/features/sirec-api.md) contra un SIREC corriendo.

  python3 casos/portal-muni-gt/backend/test_sirec_api.py                         # por defecto http://127.0.0.1:8088
  SIREC_BASE=http://100.91.166.18:8088 python3 casos/portal-muni-gt/backend/test_sirec_api.py

Crea una orden de pago y una solicitud LAIP (datos ficticios) cada vez que corre.
"""
import json, os, re, sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("SIREC_BASE", "http://127.0.0.1:8088").rstrip("/") + "/sirec/api"
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def pedir(ruta, datos=None):
    req = Request(BASE + ruta, data=urlencode(datos).encode() if datos is not None else None,
                  headers={"Content-Type": "application/x-www-form-urlencoded"} if datos is not None else {})
    try:
        with urlopen(req, timeout=15) as r:
            return r.status, r.headers.get("Content-Type", ""), json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), json.loads(e.read().decode("utf-8"))


def error(ruta, codigo_http, codigo, datos=None):
    st, ct, j = pedir(ruta, datos)
    assert st == codigo_http and j.get("error") == codigo and j.get("mensaje"), (ruta, st, j)


st, ct, j = pedir("/estado")
assert st == 200 and "application/json" in ct and "utf-8" in ct.lower(), (st, ct)
assert j["sistema"] == "SIREC" and j["version"] == "3.2.1" and "ficticia" in j["municipalidad"], j

st, _, f = pedir("/iusi?finca=F-1024")
assert st == 200, (st, f)
assert (f["finca"], f["zona"], f["direccion"], f["propietario"]) == ("F-1024", 3, "4a avenida 7-21, zona 3, Soke", "M**** L****"), f
assert (f["valor_fiscal"], f["tasa_por_millar"], f["iusi_anual"], f["saldo_pendiente"], f["moneda"]) == (185000.0, 9, 1665.0, 832.5, "GTQ"), f
assert [(t["trimestre"], t["estado"]) for t in f["trimestres"]] == [(1, "pagado"), (2, "pagado"), (3, "pendiente"), (4, "pendiente")], f
assert f["trimestres"][0]["fecha_pago"] == "2026-03-12" and f["trimestres"][2]["fecha_pago"] is None and f["trimestres"][0]["monto"] == 416.25
st, _, f = pedir("/iusi?finca=F-2048")
assert st == 200 and f["saldo_pendiente"] == 0 and {t["estado"] for t in f["trimestres"]} == {"pagado"}, f
st, _, f = pedir("/iusi?finca=F-3072")
assert st == 200 and "vencido" in [t["estado"] for t in f["trimestres"]], f
error("/iusi?finca=F-0000", 404, "finca_no_encontrada")
error("/iusi?finca=1024", 400, "finca_invalida")
error("/iusi", 400, "finca_invalida")

st, _, o = pedir("/orden-pago", {"concepto": "iusi", "referencia": "F-1024"})
assert st == 200 and re.match(r"^OP-2026-\d{6}$", o["orden"]) and o["monto"] == 832.5 and o["moneda"] == "GTQ", o
assert (o["concepto"], o["referencia"]) == ("iusi", "F-1024") and FECHA.match(o["vence"]) and o["pagar_en"], o
error("/orden-pago", 400, "concepto_invalido", {"concepto": "tarjeta", "referencia": "F-1024"})
error("/orden-pago", 400, "referencia_invalida", {"concepto": "iusi", "referencia": "xyz"})
error("/orden-pago", 404, "referencia_no_encontrada", {"concepto": "iusi", "referencia": "F-0000"})

error("/laip", 400, "campo_obligatorio", {"nombre": "", "descripcion": "Quiero el presupuesto 2026"})
error("/laip", 400, "descripcion_corta", {"nombre": "Vecino de prueba", "descripcion": "corto"})
st, _, s = pedir("/laip", {"nombre": "Vecino de prueba (ficticio)", "correo": "", "descripcion": "Solicito el detalle del gasto en alumbrado 2026."})
assert st == 201 and re.match(r"^LAIP-2026-\d{4}$", s["folio"]) and s["estado"] == "recibida" and FECHA.match(s["fecha"]) and s["vence"] > s["fecha"], s
st, _, g = pedir("/laip/" + s["folio"])
assert st == 200 and g["folio"] == s["folio"] and g["estado"] == "recibida" and isinstance(g["dias_restantes"], int) and g["dias_restantes"] >= 0, g
st, _, g = pedir("/laip/LAIP-2026-0101")
assert st == 200 and g["estado"] == "resuelta", g
st, _, g = pedir("/laip/LAIP-2026-0140")
assert st == 200 and g["estado"] == "en_tramite", g
error("/laip/LAIP-2026-9999", 404, "folio_no_encontrado")
print("ok: contrato de SIREC cumplido en", BASE)
