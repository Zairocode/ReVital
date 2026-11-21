#!/usr/bin/env python3
"""Genera los datos FICTICIOS de SIREC (sistema de recaudacion de la muni ficticia MuniSoke GT).

Uso:  python3 generar_datos.py      (escribe initdb/02-datos.sql)

Semilla fija: siempre salen los mismos datos. Los nombres se arman combinando nombres y apellidos comunes;
no corresponden a personas reales. DPI, NIT, telefonos y fincas son inventados y cada contribuyente lleva
nota = 'DATO FICTICIO'. Los registros garantizados por el contrato (docs/features/sirec-api.md) se fijan a mano.
"""
import datetime, hashlib, os, random

AQUI = os.path.dirname(os.path.abspath(__file__))
SEMILLA = 2026
HOY = datetime.date(2026, 11, 21)  # fecha de referencia del demo (fija para que los datos no cambien)
N_CONTRIBUYENTES = 300

NOMBRES = ("Maria", "Jose", "Juan", "Ana", "Carlos", "Rosa", "Luis", "Marta", "Pedro", "Elena", "Miguel", "Lucia", "Jorge",
           "Sofia", "Mario", "Carmen", "Oscar", "Gloria", "Edgar", "Claudia", "Byron", "Ingrid", "Hugo", "Wendy", "Erick",
           "Mildred", "Selvin", "Yesenia", "Otto", "Brenda")
APELLIDOS = ("Lopez", "Garcia", "Perez", "Hernandez", "Gonzalez", "Morales", "Ramirez", "Castillo", "Rodriguez", "Martinez",
             "Mendez", "Ajcalon", "Xicara", "Tzul", "Cux", "Chavez", "Monterroso", "Barrios", "Orellana", "Estrada",
             "Sic", "Coyoy", "Velasquez", "Recinos", "Pineda", "Quiej", "Son", "Batz", "Ixcot", "Samayoa")
CALLES = ("calle", "avenida")


def tasa(valor):
    """IUSI por millar segun el valor fiscal del inmueble."""
    return 0 if valor <= 2000 else 2 if valor <= 20000 else 6 if valor <= 70000 else 9


def inmueble(finca, cid, zona, direccion, valor):
    t = tasa(valor)
    return {"finca": finca, "contribuyente_id": cid, "zona": zona, "direccion": direccion, "valor_fiscal": round(valor, 2),
            "tasa_por_millar": t, "iusi_anual": round(valor * t / 1000, 2)}


def trimestres(inm, estados, fechas=(None, None, None, None)):
    anual = inm["iusi_anual"]
    base = round(anual / 4, 2)
    montos = [base, base, base, round(anual - 3 * base, 2)]
    return [{"finca": inm["finca"], "anio": 2026, "trimestre": q + 1, "monto": montos[q], "estado": estados[q],
             "fecha_pago": fechas[q] if estados[q] == "pagado" else None} for q in range(4)]


def generar():
    r = random.Random(SEMILLA)
    d = {"contribuyentes": [], "inmuebles": [], "trimestres": [], "ornato": [], "agua": [], "multas": [], "laip": [], "usuarios": []}
    dpis = set()
    for cid in range(1, N_CONTRIBUYENTES + 1):
        while True:
            dpi = "%04d %05d %04d" % (r.randint(1000, 2999), r.randint(10000, 99999), r.choice((101, 1701, 1708, 901)))
            if dpi not in dpis:
                dpis.add(dpi)
                break
        zona = r.randint(1, 6)
        d["contribuyentes"].append({
            "id": cid, "nombres": "%s %s" % (r.choice(NOMBRES), r.choice(NOMBRES)),
            "apellidos": "%s %s" % (r.choice(APELLIDOS), r.choice(APELLIDOS)), "dpi": dpi,
            "nit": "%d-%d" % (r.randint(100000, 9999999), r.randint(0, 9)), "telefono": "0000-%04d" % r.randint(0, 9999),
            "direccion": "%d%s %s %d-%02d, zona %d, Soke" % (r.randint(1, 12), "a", r.choice(CALLES), r.randint(1, 20), r.randint(1, 60), zona),
            "zona": zona, "nota": "DATO FICTICIO"})
    usadas = {"F-1024", "F-2048", "F-3072", "F-0000"}
    fecha = lambda m, dd: "2026-%02d-%02d" % (m, dd)
    for c in d["contribuyentes"]:
        for _ in range(r.choice((1, 1, 1, 2))):
            while True:
                finca = "F-%d" % r.randint(1001, 19999)
                if finca not in usadas:
                    usadas.add(finca)
                    break
            inm = inmueble(finca, c["id"], c["zona"], c["direccion"], r.choice((r.uniform(15000, 70000), r.uniform(70001, 450000))))
            d["inmuebles"].append(inm)
            est = ["pagado" if r.random() < .85 else "vencido", "pagado" if r.random() < .75 else "vencido",
                   "pagado" if r.random() < .6 else "vencido", "pagado" if r.random() < .3 else "pendiente"]
            d["trimestres"] += trimestres(inm, est, (fecha(3, r.randint(1, 31)), fecha(6, r.randint(1, 30)), fecha(9, r.randint(1, 30)), fecha(11, r.randint(1, 20))))
        d["ornato"].append({"dpi": c["dpi"], "anio": 2026, "monto": r.choice((15.00, 50.00, 75.00, 100.00, 150.00)), "pagado": int(r.random() < .55)})
        if r.random() < .8:
            d["agua"].append({"contador": "A-%05d" % (10000 + c["id"]), "contribuyente_id": c["id"], "saldo": round(r.choice((0, 0, r.uniform(25, 900))), 2)})
    # garantizados por el contrato (el propietario de F-1024 se muestra enmascarado como "M**** L****")
    d["contribuyentes"][0].update(nombres="Marta Elena", apellidos="Lopez Cux")
    fijos = [(inmueble("F-1024", 1, 3, "4a avenida 7-21, zona 3, Soke", 185000.00), ["pagado", "pagado", "pendiente", "pendiente"], ("2026-03-12", "2026-06-30", None, None)),
             (inmueble("F-2048", 2, 1, "2a calle 3-15, zona 1, Soke", 64500.00), ["pagado"] * 4, ("2026-02-20", "2026-05-18", "2026-08-21", "2026-11-05")),
             (inmueble("F-3072", 3, 5, "9a avenida 12-40, zona 5, Soke", 98000.00), ["pagado", "vencido", "vencido", "pendiente"], ("2026-03-30", None, None, None))]
    for inm, est, fe in fijos:
        d["inmuebles"].append(inm)
        d["trimestres"] += trimestres(inm, est, fe)
    d["inmuebles"].sort(key=lambda i: i["finca"])
    for n in range(1, 30):
        d["multas"].append({"boleta": "PMT-2026-%05d" % (100 + n), "placa": "P-%03d%s" % (r.randint(100, 999), "".join(r.choice("BCDFGHJKLMNPRSTVWXYZ") for _ in range(3))),
                            "monto": r.choice((150.00, 300.00, 500.00, 1000.00)), "estado": r.choice(("pendiente", "pendiente", "pagada"))})
    temas = ("Presupuesto municipal 2026 y su ejecucion", "Contratos de recoleccion de basura", "Actas del Concejo de los ultimos 6 meses",
             "Listado de obras en zona 3", "Planilla de personal temporal", "Costo del alumbrado publico", "Licencias de construccion otorgadas")
    for n in range(101, 153):
        f = HOY - datetime.timedelta(days=r.randint(1, 120) if n < 140 else r.randint(0, 8))
        estado = "resuelta" if n < 135 else r.choice(("en_tramite", "recibida", "prorrogada"))
        estado = {101: "resuelta", 140: "en_tramite"}.get(n, estado)
        c = d["contribuyentes"][n]
        d["laip"].append({"folio": "LAIP-2026-%04d" % n, "nombre": "%s %s" % (c["nombres"].split()[0], c["apellidos"].split()[0]),
                          "correo": None, "descripcion": r.choice(temas), "fecha": f.isoformat(), "vence": vence(f).isoformat(), "estado": estado})
    for usuario, nombre, clave, rol in (("admin", "Administrador del sistema", "admin123", "admin"), ("cajero1", "Cajero agencia central", "muni2014", "cajero"),
                                        ("cajero2", "Cajero mercado", "soke2015", "cajero"), ("catastro", "Oficina de catastro", "catastro", "consulta"),
                                        ("laip", "Unidad de informacion publica", "laip2016", "laip")):
        d["usuarios"].append({"usuario": usuario, "nombre": nombre, "clave_md5": hashlib.md5(clave.encode()).hexdigest(), "rol": rol})
    return d


def vence(fecha, dias=10):
    """Fecha limite: 10 dias habiles (lunes a viernes) despues de la fecha de la solicitud."""
    f = fecha
    while dias:
        f += datetime.timedelta(days=1)
        if f.weekday() < 5:
            dias -= 1
    return f


def saldo(d, finca):
    return round(sum(t["monto"] for t in d["trimestres"] if t["finca"] == finca and t["estado"] != "pagado"), 2)


def _v(x):
    if x is None:
        return "NULL"
    if isinstance(x, (int, float)):
        return "%.2f" % x if isinstance(x, float) else str(x)
    return "'" + str(x).replace("\\", "\\\\").replace("'", "''") + "'"


def _insert(tabla, filas, cols):
    out = []
    for i in range(0, len(filas), 100):
        out.append("INSERT INTO %s (%s) VALUES\n%s;" % (tabla, ", ".join(cols), ",\n".join("(" + ", ".join(_v(f[c]) for c in cols) + ")" for f in filas[i:i + 100])))
    return "\n".join(out)


def a_sql(d):
    partes = ["-- GENERADO por generar_datos.py (semilla %d). No editar a mano. TODOS LOS DATOS SON FICTICIOS." % SEMILLA, "USE sirec;", "SET NAMES utf8;",
              _insert("contribuyentes", d["contribuyentes"], ("id", "nombres", "apellidos", "dpi", "nit", "telefono", "direccion", "zona", "nota")),
              _insert("inmuebles", d["inmuebles"], ("finca", "contribuyente_id", "zona", "direccion", "valor_fiscal", "tasa_por_millar", "iusi_anual")),
              _insert("iusi_trimestres", d["trimestres"], ("finca", "anio", "trimestre", "monto", "estado", "fecha_pago")),
              _insert("boletos_ornato", d["ornato"], ("dpi", "anio", "monto", "pagado")),
              _insert("contadores_agua", d["agua"], ("contador", "contribuyente_id", "saldo")),
              _insert("multas_pmt", d["multas"], ("boleta", "placa", "monto", "estado")),
              _insert("solicitudes_laip", d["laip"], ("folio", "nombre", "correo", "descripcion", "fecha", "vence", "estado")),
              _insert("usuarios_sirec", d["usuarios"], ("usuario", "nombre", "clave_md5", "rol"))]
    return "\n\n".join(partes) + "\n"


if __name__ == "__main__":
    ruta = os.path.join(AQUI, "initdb", "02-datos.sql")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    d = generar()
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(a_sql(d))
    print("escrito %s: %d contribuyentes, %d inmuebles, %d solicitudes LAIP" % (ruta, len(d["contribuyentes"]), len(d["inmuebles"]), len(d["laip"])))
