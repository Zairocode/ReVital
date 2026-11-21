"""Tablero estilo telemetria para la pestana Resumen de una entidad: verde = correcto, rojo = vulnerable.

Todo se dibuja en el servidor con SVG y CSS (sin JavaScript, sin librerias, sin internet), a partir del
hallazgos-<entidad>.json que produce revital.cves. Si falta un dato, el widget muestra 0 / "sin datos"; nunca falla.
"""
import html, math, time

e = html.escape
ROJO, VERDE, GRIS, GRIS2, BLANCO = "#e10600", "#22c55e", "#3a3a3a", "#262626", "#ffffff"

CSS = """
.tb{background:#050505;color:#fff;border-radius:16px;padding:26px 28px 8px;margin:0 0 22px;font-family:"Segoe UI",Arial,sans-serif}
.tb .fila{display:flex;flex-wrap:wrap;margin:0 -14px 18px}
.tb .w{flex:1 1 260px;padding:6px 14px 14px;min-width:240px}
.tb .w2{flex:2 1 420px}
.tb .lb{font-size:12px;font-weight:700;letter-spacing:.9px;text-transform:uppercase;color:#e5e5e5;margin:0 0 8px}
.tb .big{font-size:50px;font-weight:700;line-height:1;margin:6px 0 12px;letter-spacing:-1px}
.tb .big small{font-size:20px;font-weight:600;margin-left:4px;letter-spacing:0}
.tb .mut{color:#8a8a8a;font-size:13px} .tb .r{color:#e10600} .tb .g{color:#22c55e}
.tb .cab{display:flex;justify-content:space-between;align-items:flex-start}
.tb .ico{width:54px;height:54px;border-radius:50%;background:#fff;display:inline-block;text-align:center;flex:0 0 54px}
.tb .ico svg{margin-top:13px}
.tb .sep{border-left:1px solid #2f2f2f}
.tb .kv{font-size:12px;letter-spacing:.6px;color:#cfcfcf;margin:10px 0 0;text-transform:uppercase}
.tb .kv b{display:block;font-size:15px;letter-spacing:0;color:#fff;text-transform:none;line-height:1.35}
.tb .kv b.r{color:#e10600} .tb .kv b.g{color:#22c55e}
.tb table{background:transparent;border:0;font-size:14px} .tb td{border:0;padding:5px 6px 5px 0;color:#fff;vertical-align:middle}
.tb .ley{font-size:12px;letter-spacing:.6px;color:#cfcfcf;margin:6px 0 0}
.tb .ley span{display:inline-block;width:18px;height:3px;margin:0 6px 3px 14px;vertical-align:middle}
.tb .pie2{color:#6b6b6b;font-size:12px;padding:4px 0 10px}
"""

# Iconos (negro sobre el circulo blanco). Formas simples para que se vean igual en navegadores viejos.
ICONOS = {
    "escudo": '<path d="M14 2 24 6v8c0 6.500-4.300 10.500-10 12C8.300 24.500 4 20.500 4 14V6Z" fill="none" stroke="#000" stroke-width="2.600" stroke-linejoin="round"/>',
    "rayo": '<path d="M16 2 6 16h7l-2 10 10-14h-7Z" fill="#000"/>',
    "bicho": '<ellipse cx="14" cy="15" rx="6" ry="8" fill="#000"/><path d="M8 11 3 8M20 11l5-3M8 16H2m18 0h6M8 21l-5 3m17-3 5 3M11 7 9 3m8 4 2-4" stroke="#000" stroke-width="2.200" stroke-linecap="round"/>',
    "reloj": '<circle cx="14" cy="15" r="10" fill="none" stroke="#000" stroke-width="2.600"/><path d="M14 9v6l4 3" stroke="#000" stroke-width="2.600" fill="none" stroke-linecap="round"/>',
    "engrane": '<circle cx="14" cy="14" r="5" fill="none" stroke="#000" stroke-width="2.600"/><path d="M14 2v5M14 21v5M2 14h5M21 14h5M5.500 5.500l3.500 3.500M19 19l3.500 3.500M5.500 22.500 9 19M19 9l3.500-3.500" stroke="#000" stroke-width="2.600" stroke-linecap="round"/>',
}


def icono(nombre):
    return '<span class="ico"><svg width="28" height="28" viewBox="0 0 28 28">%s</svg></span>' % ICONOS[nombre]


def _corta(t, n):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."


def _f(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


# ---------------------------------------------------------------- piezas SVG

def barra(n, total=24, estilo="seg", ancho=240):
    """Barra segmentada. n = cuantos segmentos rojos (1 por hallazgo, con tope). n == 0 -> toda verde (todo bien)."""
    llenos = min(n, total)
    color = (lambda i: ROJO if i < llenos else GRIS) if n else (lambda i: VERDE)
    if estilo == "punto":
        paso = ancho / float(total)
        return '<svg width="%d" height="12">%s</svg>' % (ancho, "".join(
            '<circle cx="%s" cy="6" r="4" fill="%s"/>' % (_f(paso * i + paso / 2), color(i)) for i in range(total)))
    if estilo == "fino":
        paso = ancho / float(total)
        return '<svg width="%d" height="26">%s</svg>' % (ancho, "".join(
            '<rect x="%s" y="0" width="%s" height="26" rx="1.500" fill="%s"/>' % (_f(paso * i), _f(paso * .55), color(i))
            for i in range(total)))
    total = 6 if total > 6 else total  # estilo "seg": pocos trazos gruesos, como en un indicador de desgaste
    llenos = min(n, total)
    paso = ancho / float(total)
    return '<svg width="%d" height="10">%s</svg>' % (ancho, "".join(
        '<rect x="%s" y="0" width="%s" height="10" rx="5" fill="%s"/>' % (
            _f(paso * i), _f(paso - 8), (ROJO if i < llenos else GRIS) if n else VERDE) for i in range(total)))


def anillo(ok, total, ticks=60, r=62):
    """Anillo de marcas: verde = componentes seguros, rojo = vulnerables."""
    verdes = int(round(ticks * (ok / float(total)))) if total else ticks
    c, out = r + 14, []
    for i in range(ticks):
        a = -math.pi / 2 + 2 * math.pi * i / ticks
        x1, y1 = c + (r - 12) * math.cos(a), c + (r - 12) * math.sin(a)
        x2, y2 = c + r * math.cos(a), c + r * math.sin(a)
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3.200" stroke-linecap="round"/>' % (
            _f(x1), _f(y1), _f(x2), _f(y2), VERDE if i < verdes else ROJO))
    escudo = ('<g transform="translate(%s %s) scale(1.400)">%s</g>' % (_f(c - 19.6), _f(c - 19.6),
              ICONOS["escudo"].replace("#000", BLANCO)))
    return '<svg width="%d" height="%d">%s%s</svg>' % (2 * c, 2 * c, "".join(out), escudo)


def semicirculo(valor, bien):
    """Medidor de media luna con aguja (valor 0..1 = proporcion de componentes seguros)."""
    cx, cy, r, out = 110, 98, 88, []
    for i in range(41):
        a = math.pi + math.pi * i / 40
        largo = 14 if i % 5 == 0 else 8
        x1, y1 = cx + (r - largo) * math.cos(a), cy + (r - largo) * math.sin(a)
        x2, y2 = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#bdbdbd" stroke-width="2"/>' % (_f(x1), _f(y1), _f(x2), _f(y2)))
    a = math.pi + math.pi * max(0.0, min(1.0, valor))
    nx, ny = cx + (r - 2) * math.cos(a), cy + (r - 2) * math.sin(a)
    col = VERDE if bien else ROJO
    out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (
        _f(cx + (r - 22) * math.cos(a)), _f(cy + (r - 22) * math.sin(a)), _f(nx), _f(ny), col))
    out.append('<circle cx="%d" cy="%d" r="6" fill="%s"/>' % (cx, cy, col))
    out.append('<text x="%d" y="%d" text-anchor="middle" fill="%s" font-size="22" font-weight="700" '
               'font-family="Segoe UI,Arial,sans-serif">%s</text>' % (cx, cy + 30, col, "CUMPLE" if bien else "NO CUMPLE"))
    out.append('<text x="%d" y="%d" text-anchor="middle" fill="#9a9a9a" font-size="11" letter-spacing="1" '
               'font-family="Segoe UI,Arial,sans-serif">CATALOGO CISA KEV</text>' % (cx, cy + 48))
    return '<svg width="220" height="152">%s</svg>' % "".join(out)


def curva(conteos, ancho=430, alto=150):
    """Area suave (curva por los puntos) con marcador en el pico. conteos = lista de valores por casilla."""
    n, tope = len(conteos), max(conteos) or 1
    xs = [20 + (ancho - 40) * i / float(n - 1) for i in range(n)]
    ys = [alto - 18 - (alto - 48) * v / float(tope) for v in conteos]
    d = "M%s %s" % (_f(xs[0]), _f(ys[0]))
    for i in range(n - 1):  # curva de Catmull-Rom convertida a Bezier: suave y pasa por cada punto
        p0, p1 = (xs[max(i - 1, 0)], ys[max(i - 1, 0)]), (xs[i], ys[i])
        p2, p3 = (xs[i + 1], ys[i + 1]), (xs[min(i + 2, n - 1)], ys[min(i + 2, n - 1)])
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += " C%s %s %s %s %s %s" % (_f(c1[0]), _f(c1[1]), _f(c2[0]), _f(c2[1]), _f(p2[0]), _f(p2[1]))
    area = d + " L%s %d L%s %d Z" % (_f(xs[-1]), alto - 18, _f(xs[0]), alto - 18)
    pico = max(range(n), key=lambda i: conteos[i])
    guias = "".join('<line x1="%s" y1="%s" x2="%s" y2="%d" stroke="#7a7a7a" stroke-dasharray="3 4"/>' % (
        _f(xs[i]), _f(ys[i] + 6), _f(xs[i]), alto - 18) for i in range(1, n - 1, 2))
    etiquetas = "".join('<text x="%s" y="%d" fill="#8a8a8a" font-size="11" text-anchor="middle" '
                        'font-family="Segoe UI,Arial,sans-serif">%d</text>' % (_f(xs[i]), alto - 2, i) for i in range(0, n, 2))
    return ('<svg width="%d" height="%d"><defs><linearGradient id="tbg" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#e10600" stop-opacity=".85"/><stop offset="1" stop-color="#e10600" stop-opacity="0"/>'
            '</linearGradient></defs><path d="%s" fill="url(#tbg)"/>%s<path d="%s" fill="none" stroke="%s" stroke-width="3"/>'
            '<line x1="%s" y1="%s" x2="%s" y2="%d" stroke="#fff" stroke-dasharray="3 4"/>'
            '<circle cx="%s" cy="%s" r="8" fill="#050505" stroke="#fff" stroke-width="2.500"/><circle cx="%s" cy="%s" r="4" fill="#fff"/>%s</svg>'
            % (ancho, alto, area, guias, d, ROJO, _f(xs[pico]), _f(ys[pico] + 9), _f(xs[pico]), alto - 18,
               _f(xs[pico]), _f(ys[pico]), _f(xs[pico]), _f(ys[pico]), etiquetas))


def lineas(etiquetas_x, series, ancho=470, alto=190):
    """Grafico de lineas: series = [(nombre, color, [valores])]. Eje Y desde 0."""
    tope = max([max(v) for _, _, v in series if v] + [1])
    tope = int(math.ceil(tope / 4.0) * 4) or 4
    x0, x1, y0, y1 = 40, ancho - 14, 12, alto - 34
    n = len(etiquetas_x)
    px = lambda i: x0 + (x1 - x0) * (i / float(n - 1) if n > 1 else .5)
    py = lambda v: y1 - (y1 - y0) * v / float(tope)
    out = []
    for k in range(5):
        v = tope * k / 4.0
        out.append('<text x="%d" y="%s" fill="#cfcfcf" font-size="12" text-anchor="end" font-family="Segoe UI,Arial,sans-serif">%d</text>'
                   % (x0 - 10, _f(py(v) + 4), v))
    for i, et in enumerate(etiquetas_x):
        out.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#555" stroke-dasharray="3 4"/>' % (_f(px(i)), y0, _f(px(i)), y1))
        out.append('<text x="%s" y="%d" fill="#cfcfcf" font-size="12" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif">%s</text>'
                   % (_f(px(i)), alto - 12, e(et)))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#888"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#888"/>'
               % (x0, y0, x0, y1, x0, y1, x1, y1))
    for _, color, vals in series:
        pts = " ".join("%s,%s" % (_f(px(i)), _f(py(v))) for i, v in enumerate(vals))
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round"/>' % (pts, color))
    return '<svg width="%d" height="%d">%s</svg>' % (ancho, alto, "".join(out))


# ---------------------------------------------------------------- calculos

def _dias(desde, hasta):
    try:
        a = time.mktime(time.strptime(desde[:10], "%Y-%m-%d"))
        b = time.mktime(time.strptime(hasta[:10], "%Y-%m-%d"))
        return int(round((b - a) / 86400.0))
    except (ValueError, TypeError):
        return None


def _clave(c):
    return "%s|%s" % (c.get("producto", ""), c.get("version", ""))


def resumen(h):
    hall = h.get("hallazgos", []) or []
    kev = [x for x in hall if x.get("en_kev")]
    comps = h.get("componentes", []) or []
    eol = {_clave(c) for c in h.get("eol", []) or []}
    por_comp = {}
    for x in hall:
        d = por_comp.setdefault(_clave(x), {"kev": 0, "total": 0})
        d["total"] += 1
        d["kev"] += 1 if x.get("en_kev") else 0
    filas = []
    for c in comps:
        k = _clave(c)
        d = por_comp.get(k, {"kev": 0, "total": 0})
        filas.append({"nombre": ("%s %s" % (c.get("producto", ""), c.get("version", ""))).strip(), "kev": d["kev"],
                      "total": d["total"], "eol": k in eol, "vulnerable": bool(d["total"]) or k in eol})
    filas.sort(key=lambda f: (-f["kev"], -f["total"], f["nombre"].lower()))
    hoy = h.get("fecha_evaluacion") or time.strftime("%Y-%m-%d")
    vencidas = [x for x in kev if x.get("vencido")]
    mas_vieja = min(vencidas or kev, key=lambda x: x.get("fecha_limite") or "9999") if kev else None
    cvss = [0] * 11
    for x in hall:
        try:
            cvss[min(10, int(round(float(x.get("cvss")))))] += 1
        except (TypeError, ValueError):
            pass
    anios = sorted({(x.get("agregado_kev") or "")[:4] for x in kev if x.get("agregado_kev")})
    if anios:
        anios = [str(a) for a in range(int(anios[0]), int(hoy[:4]) + 1)]
    acum = lambda pred: [sum(1 for x in kev if (x.get("agregado_kev") or "9999")[:4] <= a and pred(x)) for a in anios]
    return {"kev": len(kev), "ransomware": sum(1 for x in kev if x.get("ransomware") == "Known"),
            "exploit": sum(1 for x in kev if x.get("exploits")), "msf": sum(1 for x in kev if x.get("exploit_metasploit")),
            "vencidas": len(vencidas), "filas": filas, "seguros": sum(1 for f in filas if not f["vulnerable"]),
            "comps": len(filas), "hoy": hoy, "mas_vieja": mas_vieja, "cvss": cvss, "anios": anios,
            "linea_kev": acum(lambda x: True), "linea_exp": acum(lambda x: bool(x.get("exploits"))),
            "eol": h.get("eol", []) or [], "config": h.get("configuracion", []) or [], "total": len(hall)}


# ---------------------------------------------------------------- tablero

def _stat(titulo, n, ico, estilo, extra=""):
    cls = "r" if n else "g"
    return ('<div class="w"><div class="cab"><div class="lb">%s</div>%s</div><div class="big %s">%d</div>%s'
            '<div class="mut" style="margin-top:8px">%s</div></div>' % (e(titulo), icono(ico), cls, n, barra(n, 24, estilo), extra))


def html_tablero(h):
    s = resumen(h)
    b = ['<style>%s</style><div class="tb">' % CSS]

    # fila 1: tres indicadores grandes
    b.append('<div class="fila">')
    b.append(_stat("Explotadas hoy (KEV)", s["kev"], "bicho", "seg",
                   "sin parchear" if s["kev"] else "ninguna vulnerabilidad explotada: correcto"))
    b.append(_stat("Usadas en ransomware", s["ransomware"], "rayo", "punto",
                   "secuestran datos con estas fallas" if s["ransomware"] else "ninguna"))
    b.append(_stat("Con exploit publico", s["exploit"], "escudo", "fino",
                   ("%d con modulo de Metasploit" % s["msf"]) if s["exploit"] else "sin codigo de ataque publicado"))
    b.append('</div>')

    # fila 2: anillo de componentes, plazo CISA y medidor de cumplimiento
    peor = next((f for f in s["filas"] if f["vulnerable"]), None)
    b.append('<div class="fila">')
    b.append('<div class="w"><div class="lb">Componentes seguros</div><div style="display:flex;align-items:center">'
             '<div style="margin-right:18px"><div class="big %s" style="margin-bottom:4px">%d<small>/ %d</small></div>'
             '<div class="kv">Mas expuesto<b class="r">%s</b></div></div>%s</div></div>'
             % ("g" if s["seguros"] == s["comps"] else "r", s["seguros"], s["comps"],
                e(peor["nombre"]) if peor else '<span class="g">ninguno</span>', anillo(s["seguros"], s["comps"])))
    mv = s["mas_vieja"]
    if mv:
        dias = _dias(mv.get("fecha_limite", ""), s["hoy"])
        plazo = ('<div class="kv">CVE<b>%s</b></div><div class="kv">En KEV desde<b>%s</b></div>'
                 '<div class="kv">Fecha limite CISA<b>%s</b></div><div class="kv">%s<b class="%s">%s</b></div>'
                 % (e(mv["cve"]), e(mv.get("agregado_kev", "?")), e(mv.get("fecha_limite", "?")),
                    "Dias de atraso" if mv.get("vencido") else "Dias restantes", "r" if mv.get("vencido") else "g",
                    abs(dias) if dias is not None else "?"))
    else:
        plazo = '<div class="kv">Sin vulnerabilidades KEV<b class="g">Al dia con CISA</b></div>'
    b.append('<div class="w"><div class="lb">Plazo CISA mas atrasado</div>%s</div>' % plazo)
    seg = s["seguros"] / float(s["comps"]) if s["comps"] else 1.0
    b.append('<div class="w" style="text-align:center"><div class="lb">Cumplimiento</div>%s'
             '<div style="display:flex;justify-content:center;margin-top:4px">'
             '<div style="padding:0 18px"><div class="mut">SEGUROS</div><div style="font-size:22px;font-weight:700" class="g">%d%%</div></div>'
             '<div class="sep"></div><div style="padding:0 18px"><div class="mut">VULNERABLES</div>'
             '<div style="font-size:22px;font-weight:700" class="%s">%d%%</div></div></div></div>'
             % (semicirculo(seg, not s["kev"]), round(seg * 100), "r" if seg < 1 else "g", 100 - round(seg * 100)))
    b.append('</div>')

    # fila 3: curva de gravedad y riesgo por componente
    b.append('<div class="fila">')
    alta = sum(s["cvss"][7:])
    b.append('<div class="w w2"><div class="lb">Gravedad de lo encontrado (CVSS 0-10)</div><div style="display:flex;align-items:center;flex-wrap:wrap">%s'
             '<div style="margin-left:14px"><div style="font-size:24px;font-weight:800" class="%s">%s</div>'
             '<div style="font-weight:700">EXPOSICION</div><div class="mut">%d de %d con CVSS 7 o mas</div></div></div></div>'
             % (curva(s["cvss"]) if s["total"] else '<div class="mut" style="width:430px">sin hallazgos</div>',
                "r" if alta else "g", "ALTA" if alta else "BAJA", alta, s["total"]))
    filas = "".join('<tr><td style="width:170px;font-size:13px">%s%s</td><td style="width:150px">%s</td>'
                    '<td style="text-align:right;white-space:nowrap;padding-left:10px" class="%s">%s</td></tr>'
                    % (e(f["nombre"]), ' <span class="r" style="font-size:11px">EOL</span>' if f["eol"] else "",
                       barra(f["kev"] if f["kev"] else 1, 20, "fino", 150) if f["vulnerable"]
                       else barra(0, 20, "fino", 150), "r" if f["vulnerable"] else "g",
                       ("%d KEV" % f["kev"]) if f["kev"] else ("%d CVE" % f["total"] if f["total"] else ("sin soporte" if f["eol"] else "OK")))
                    for f in s["filas"][:8])
    b.append('<div class="w"><div class="lb">Riesgo por componente</div><table>%s</table>%s</div>'
             % (filas or '<tr><td class="mut">sin componentes</td></tr>',
                '<div class="mut">y %d mas en Inventario</div>' % (len(s["filas"]) - 8) if len(s["filas"]) > 8 else ""))
    b.append('</div>')

    # fila 4: fuera de soporte, configuracion, linea de tiempo
    b.append('<div class="fila">')
    eol = "".join('<div class="kv">%s %s<b class="r">sin soporte desde<br>%s</b></div>' % (
        e(c.get("producto", "")), e(c.get("version", "")), e(c.get("fin_soporte", "?"))) for c in s["eol"][:3])
    b.append('<div class="w" style="flex:1 1 200px"><div class="cab"><div class="lb">Fuera de soporte</div>%s</div>'
             '<div class="big %s">%d</div>%s</div>' % (icono("reloj"), "r" if s["eol"] else "g", len(s["eol"]),
                                                       eol or '<div class="kv"><b class="g">todo con soporte</b></div>'))
    conf = "".join('<div class="kv">%s<b class="r">%s</b></div>' % (e(c.get("tipo", "")), e(_corta(c.get("detalle") or "", 44)))
                   for c in s["config"][:3])
    b.append('<div class="w sep" style="flex:1 1 200px"><div class="cab"><div class="lb">Configuracion insegura</div>%s</div>'
             '<div class="big %s">%d</div>%s</div>' % (icono("engrane"), "r" if s["config"] else "g", len(s["config"]),
                                                       conf or '<div class="kv"><b class="g">sin alertas</b></div>'))
    if len(s["anios"]) >= 2:
        graf = lineas(s["anios"], [("KEV", ROJO, s["linea_kev"]), ("Con exploit", BLANCO, s["linea_exp"])])
    else:
        graf = '<div class="mut" style="padding:30px 0">sin historial suficiente</div>'
    b.append('<div class="w w2"><div class="lb">Vulnerabilidades explotadas acumuladas (por ano de ingreso a KEV)</div>%s'
             '<div class="ley"><span style="background:#e10600"></span>EXPLOTADAS (KEV)<span style="background:#fff"></span>CON EXPLOIT PUBLICO</div></div>'
             % graf)
    b.append('</div>')
    b.append('<div class="pie2">Verde = correcto · Rojo = vulnerable · Datos: CISA KEV, NVD y Exploit-DB (indice). Evaluado el %s.</div></div>'
             % e(s["hoy"]))
    return "".join(b)
