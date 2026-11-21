"""HTML del panel. Sin JavaScript obligatorio, sin fuentes ni librerias de internet y sin variables CSS: asi se ve igual
en navegadores viejos y sin conexion."""
import html, re
from urllib.parse import quote

from revital.panel import datos, tablero

e = html.escape
COLOR = {"CRITICO": ("#ffffff", "#e10600"), "URGENTE (vencido)": ("#ffffff", "#b30500"), "URGENTE": ("#ffffff", "#8a0400"),
         "ALTO (exploit publico)": ("#ff6b62", "#2a0a08"), "ALTO": ("#ff8a80", "#1f0d0c"), "MEDIO": ("#e5e5e5", "#262626"), "BAJO": ("#9a9a9a", "#1a1a1a")}
SEV_ALERTA = {"critica": ("#ffffff", "#e10600"), "alta": ("#ffffff", "#8a0400"), "media": ("#ff8a80", "#1f0d0c"), "info": ("#9a9a9a", "#1a1a1a")}

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#050505;color:#f2f2f2;font:15px/1.55 "Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif}
a{color:#ffffff;text-decoration:none;font-weight:600} a:hover{color:#e10600;text-decoration:none}
.top{background:#000;border-bottom:1px solid #1f1f1f;color:#fff;padding:0}
.top .in{max-width:1180px;margin:0 auto;padding:14px 22px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap}
.marca{display:flex;align-items:center;color:#fff} .marca:hover{color:#fff}
.marca svg{margin-right:12px} .marca b{font-size:22px;letter-spacing:.3px} .marca span{display:block;font-size:11px;color:#8a8a8a;letter-spacing:.8px;text-transform:uppercase;font-weight:600}
.nav a{color:#bdbdbd;margin-left:6px;padding:8px 14px;font-weight:700;font-size:12px;letter-spacing:.9px;text-transform:uppercase;display:inline-block;border-bottom:2px solid transparent}
.nav a:hover{color:#fff} .nav a.act{color:#fff;border-bottom-color:#e10600}
.wrap{max-width:1180px;margin:0 auto;padding:24px 22px}
h1{font-size:30px;margin:4px 0 2px;font-weight:700;letter-spacing:-.3px} h3{font-size:15px;margin:0 0 6px}
h2{font-size:13px;margin:30px 0 12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#e5e5e5}
.sub{color:#8a8a8a;margin:0 0 18px}
.card{background:#0d0d0d;border:1px solid #1f1f1f;border-radius:14px;padding:20px}
.grid{display:flex;flex-wrap:wrap;margin:0 -9px}
.grid>.card,.grid>.k{margin:9px;flex:1 1 300px}
.k{background:#0d0d0d;border:1px solid #1f1f1f;border-radius:14px;padding:16px 18px;flex:1 1 150px;min-width:150px}
.k .n{font-size:40px;font-weight:700;line-height:1.1;letter-spacing:-.5px} .k .t{color:#9a9a9a;font-size:11px;font-weight:700;letter-spacing:.8px;text-transform:uppercase}
.k.mal{border-top:3px solid #e10600} .k.mal .n{color:#e10600} .k.bien{border-top:3px solid #22c55e} .k.bien .n{color:#22c55e}
.k.med{border-top:3px solid #e10600} .k.med .n{color:#e10600} .k.neu{border-top:3px solid #3a3a3a}
.chip{display:inline-block;border-radius:99px;padding:2px 11px;font-size:11px;font-weight:700;letter-spacing:.5px;white-space:nowrap;text-transform:uppercase}
.estado{display:inline-block;border-radius:99px;padding:5px 14px;font-weight:800;font-size:12px;letter-spacing:.9px}
.si{background:#22c55e;color:#03140a} .no{background:#e10600;color:#fff}
.btn{display:inline-block;background:#fff;color:#050505;border:0;border-radius:99px;padding:9px 18px;font:700 13px "Segoe UI",Arial,sans-serif;letter-spacing:.4px;cursor:pointer}
.btn:hover{background:#e10600;color:#fff} .btn.sec{background:transparent;color:#e5e5e5;border:1px solid #3a3a3a} .btn.sec:hover{border-color:#fff;color:#fff;background:transparent}
.tabs{border-bottom:1px solid #1f1f1f;margin:20px 0 20px} .tabs a{display:inline-block;padding:10px 16px;color:#8a8a8a;font-weight:700;font-size:12px;letter-spacing:.9px;text-transform:uppercase;border-bottom:2px solid transparent;margin-bottom:-1px}
.tabs a.act{color:#fff;border-bottom-color:#e10600} .tabs a:hover{color:#fff}
table{width:100%;border-collapse:collapse;background:#0d0d0d;border:1px solid #1f1f1f;border-radius:14px;overflow:hidden;font-size:14px}
th{background:#0d0d0d;text-align:left;padding:11px 12px;color:#8a8a8a;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.9px;border-bottom:1px solid #1f1f1f}
td{padding:10px 12px;border-bottom:1px solid #1a1a1a;vertical-align:top;color:#e5e5e5} tr:last-child td{border-bottom:0}
details.h{background:#0d0d0d;border:1px solid #1f1f1f;border-radius:12px;margin:0 0 8px;padding:0}
details.h summary{cursor:pointer;padding:12px 14px;list-style:none} details.h summary::-webkit-details-marker{display:none}
details.h summary b{margin:0 8px} details.h[open]{border-color:#e10600}
details.h .cu{padding:2px 16px 14px;color:#d4d4d4;border-top:1px solid #1a1a1a}
details summary{cursor:pointer}
.cu p{margin:8px 0} .mut{color:#8a8a8a} .peq{font-size:13px}
.aviso{background:#0d0d0d;border:1px solid #1f1f1f;border-left:4px solid #8a8a8a;border-radius:10px;padding:12px 16px;margin:0 0 16px;color:#e5e5e5}
.aviso.mal{border-left-color:#e10600} .aviso.mal b{color:#ff3b30} .aviso.bien{border-left-color:#22c55e} .aviso.bien b{color:#22c55e}
label{display:block;font-weight:700;margin:12px 0 5px;font-size:11px;letter-spacing:.9px;text-transform:uppercase;color:#bdbdbd}
input[type=text],select{width:100%;padding:10px 12px;border:1px solid #2f2f2f;border-radius:10px;font:14px "Segoe UI",Arial,sans-serif;background:#000;color:#fff}
input[type=text]:focus,select:focus{border-color:#e10600;outline:0}
.fila{display:flex;flex-wrap:wrap;margin:0 -8px} .fila>div{padding:0 8px;flex:1 1 220px}
.chk{font-weight:400;display:block;margin:10px 0;text-transform:none;letter-spacing:0;font-size:14px;color:#e5e5e5} .chk input{margin-right:8px}
pre{background:#000;color:#e5e5e5;border:1px solid #1f1f1f;border-radius:10px;padding:14px;overflow:auto;font:13px/1.45 Consolas,"Courier New",monospace}
code{background:#1a1a1a;color:#f2f2f2;border-radius:4px;padding:1px 5px;font:13px Consolas,"Courier New",monospace}
.md{background:#0d0d0d;border:1px solid #1f1f1f;border-radius:14px;padding:6px 26px 20px;color:#e5e5e5}
.md h1{font-size:24px;margin-top:18px} .md h2{font-size:13px} .md table{margin:10px 0} .md a{color:#fff;text-decoration:underline}
.pie{color:#5a5a5a;text-align:center;font-size:11px;letter-spacing:.6px;text-transform:uppercase;padding:28px 0}
.tl{border-left:2px solid #2f2f2f;margin:6px 0 6px 8px;padding:0 0 0 16px} .tl .ev{margin:0 0 12px}
@media (max-width:640px){.nav a{margin:4px 4px 0 0} h1{font-size:24px}}
@media print{.top,.tabs,.btn,.nav,.pie{display:none} body{background:#fff;color:#000}}
/* tarjetas HUD: rojo = vulnerable, verde = correcto, gris = neutro */
body{background-color:#05070a;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:34px 34px}
.top{background:#000}
.card,.k,details.h,.md,.aviso{position:relative;border:1px solid #2c2c2c;border-radius:4px;background:#0b0c0f;background:linear-gradient(135deg,rgba(255,255,255,.05),rgba(255,255,255,.015))}
.card:before,.k:before,details.h:before,.md:before,.aviso:before{content:"";position:absolute;top:-1px;right:-1px;border-style:solid;border-width:0 16px 16px 0;border-color:transparent #5a5a5a transparent transparent}
.card:after,.k:after,details.h:after,.md:after,.aviso:after{content:"";position:absolute;bottom:-1px;left:-1px;border-style:solid;border-width:16px 0 0 16px;border-color:transparent transparent transparent #5a5a5a}
.card.mal,.k.mal,.k.med,details.h,.aviso.mal{border-color:rgba(225,6,0,.65);background:#140405;background:linear-gradient(135deg,rgba(225,6,0,.22),rgba(225,6,0,.04))}
.card.mal:before,.k.mal:before,.k.med:before,details.h:before,.aviso.mal:before{border-right-color:#e10600}
.card.mal:after,.k.mal:after,.k.med:after,details.h:after,.aviso.mal:after{border-left-color:#e10600}
.card.bien,.k.bien,.aviso.bien{border-color:rgba(34,197,94,.6);background:#04120a;background:linear-gradient(135deg,rgba(34,197,94,.2),rgba(34,197,94,.04))}
.card.bien:before,.k.bien:before,.aviso.bien:before{border-right-color:#22c55e}
.card.bien:after,.k.bien:after,.aviso.bien:after{border-left-color:#22c55e}
.k{border-top-width:1px} .aviso{border-left-width:1px}
.card.mal h3{color:#ff3b30} .card.bien h3{color:#22c55e}
details.h[open]{border-color:#e10600;background:#1a0506;background:linear-gradient(135deg,rgba(225,6,0,.3),rgba(225,6,0,.06))}
details.h .cu{border-top-color:rgba(225,6,0,.3)}
table{border-color:rgba(225,6,0,.45);border-radius:4px;background:#0b0c0f;background:linear-gradient(135deg,rgba(225,6,0,.1),rgba(255,255,255,.015))}
th{background:rgba(225,6,0,.12);color:#ff6b62;border-bottom-color:rgba(225,6,0,.35)}
td{border-bottom-color:rgba(255,255,255,.06)}
.btn{border-radius:3px} .btn.sec{border-radius:3px} .estado,.chip{border-radius:3px}
pre{border-color:rgba(225,6,0,.35);border-radius:3px}
input[type=text],select{border-radius:3px}
"""

LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38"><path d="M19 2 33 7v11c0 9-6 15-14 18C11 33 5 27 5 18V7Z" fill="#ffffff"/>'
        '<path d="M19 6 29 9.500V18c0 6.500-4 11-10 13.500C13 29 9 24.500 9 18V9.500Z" fill="#050505"/>'
        '<path d="M13.500 18.500 17.500 22.500 25 14" stroke="#22c55e" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def pagina(titulo, cuerpo, activo="inicio"):
    nav = "".join('<a href="%s"%s>%s</a>' % (h, ' class="act"' if k == activo else "", t)
                  for k, h, t in (("inicio", "/", "Inicio"), ("sentinela", "/sentinela", "Sentinela"), ("trabajos", "/trabajos", "Análisis")))
    return ("<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s · ReVital</title><style>%s</style></head><body>"
            "<div class=\"top\"><div class=\"in\"><a class=\"marca\" href=\"/\">%s<div><b>ReVital</b><span>una segunda vida segura para sistemas legacy</span></div></a>"
            "<div class=\"nav\">%s</div></div></div><div class=\"wrap\">%s</div>"
            "<div class=\"pie\">Panel local · solo este equipo (127.0.0.1) · sin conexión a internet · usar solo en sistemas propios o con autorización</div></body></html>"
            % (e(titulo), CSS, LOGO, nav, cuerpo))


def chip(nivel):
    fg, bg = COLOR.get(nivel, ("#9a9a9a", "#1a1a1a"))
    return '<span class="chip" style="color:%s;background:%s">%s</span>' % (fg, bg, e(nivel))


def chip_sev(sev):
    fg, bg = SEV_ALERTA.get(sev, ("#9a9a9a", "#1a1a1a"))
    return '<span class="chip" style="color:%s;background:%s">%s</span>' % (fg, bg, e(sev))


def kb(n):
    return "%d B" % n if n < 1024 else "%.1f KB" % (n / 1024.0) if n < 1048576 else "%.1f MB" % (n / 1048576.0)


def kpi(n, texto, clase="neu"):
    return '<div class="k %s"><div class="n">%s</div><div class="t">%s</div></div>' % (clase, e(str(n)), e(texto))


def estado_chip(cumple):
    return '<span class="estado si">CUMPLE</span>' if cumple else '<span class="estado no">NO CUMPLE</span>'


# ---------------------------------------------------------------- inicio
def inicio(ents, alertas, estado_s, mensaje=""):
    b = ["<h1>Panel de ReVital</h1><p class=\"sub\">Qué tecnología corre, qué se está explotando hoy y qué parchear primero.</p>"]
    if mensaje:
        b.append('<div class="aviso bien">%s</div>' % e(mensaje))
    graves = [a for a in alertas[:20] if a.get("severidad") in ("critica", "alta")]
    if graves:
        b.append('<div class="aviso mal"><b>El sentinela detectó %d cambio(s) importante(s)</b> recientemente. <a href="/sentinela">Ver qué cambió</a></div>' % len(graves))
    if not ents:
        b.append('<div class="card"><h3>Todavía no hay análisis</h3><p class="mut">Corre un análisis desde abajo, o carga el caso de demostración (portal municipal ficticio) para ver cómo se ve.</p>'
                 '<form method="post" action="/demo"><button class="btn" type="submit">Cargar demostración</button></form></div>')
    else:
        b.append('<div class="grid">')
        for x in ents:
            r = x["r"]
            b.append('<div class="card %s"><div style="display:flex;justify-content:space-between;align-items:center"><h3 style="font-size:18px;margin:0">%s</h3>%s</div>'
                     '<p class="mut peq" style="margin:2px 0 12px">Evaluado el %s · catálogo KEV %s</p>'
                     '<div class="fila" style="margin:0 -4px 6px"><div style="padding:0 4px"><div style="font-size:26px;font-weight:800;color:%s">%d</div><div class="mut peq">KEV abiertas</div></div>'
                     '<div style="padding:0 4px"><div style="font-size:26px;font-weight:800">%d</div><div class="mut peq">con ransomware</div></div>'
                     '<div style="padding:0 4px"><div style="font-size:26px;font-weight:800">%d</div><div class="mut peq">componentes</div></div></div>'
                     '<a class="btn" href="/e/%s">Abrir</a> <a class="btn sec" href="/zip/%s">Descargar documentación</a></div>'
                     % ("bien" if r["cumple"] else "mal", e(x["entidad"]), estado_chip(r["cumple"]), e(x["h"].get("fecha_evaluacion", "")),
                        e(x["h"].get("catalogos", {}).get("kev_version", "?")), "#e10600" if r["kev"] else "#22c55e",
                        r["kev"], r["ransomware"], r["componentes"], e(x["slug"]), e(x["slug"])))
        b.append("</div>")
    b.append("<h2>Nuevo análisis</h2>" + form_analisis())
    return pagina("Inicio", "".join(b), "inicio")


def form_analisis():
    return ('<div class="card"><form method="post" action="/analizar"><div class="fila">'
            '<div><label>Qué analizar</label><select name="tipo"><option value="web">Sitio web (URL)</option><option value="codigo">Carpeta de una aplicación (código)</option></select></div>'
            '<div><label>URL o ruta de la carpeta</label><input type="text" name="destino" placeholder="http://localhost:8080  ·  C:\\inetpub\\portal" required></div>'
            '<div><label>Entidad (institución)</label><input type="text" name="entidad" placeholder="MUNI-GT" required></div></div>'
            '<label class="chk"><input type="checkbox" name="insecure" value="1">El servidor es muy viejo (acepta TLS 1.0 o tiene certificado vencido)</label>'
            '<label class="chk"><input type="checkbox" name="autorizo" value="1" required>Tengo autorización para analizar este sistema</label>'
            '<button class="btn" type="submit">Analizar</button> <span class="mut peq">Solo lectura: no modifica el sistema analizado.</span></form></div>')


# ---------------------------------------------------------------- entidad
def _tabs(slug, tab):
    return '<div class="tabs">%s</div>' % "".join('<a href="/e/%s?tab=%s"%s>%s</a>' % (e(slug), k, ' class="act"' if k == tab else "", t)
                                                  for k, t in (("resumen", "Resumen"), ("hallazgos", "Hallazgos"), ("inventario", "Inventario"),
                                                               ("docs", "Documentación"), ("historial", "Cambios")))


def _hallazgo(x, abierto=False):
    ev = "".join("<li><code>%s</code> · %s · %s</li>" % (e(v.get("donde", "")), e(v.get("fuente", "")), e(v.get("kind", ""))) for v in x.get("evidencia", [])[:6])
    kev = ('<span class="chip" style="color:#fff;background:#e10600">EN KEV</span> ' if x.get("en_kev") else "")
    rw = ('<span class="chip" style="color:#ff6b62;background:#2a0a08">ransomware</span> ' if x.get("ransomware") == "Known" else "")
    extra = ""
    if x.get("en_kev"):
        extra = '<p><b>Qué hacer (CISA):</b> %s<br><span class="mut">Fecha límite de CISA: %s%s · en KEV desde %s</span></p>' % (
            e(x.get("accion", "")), e(x.get("fecha_limite", "")), " (<b>vencida</b>)" if x.get("vencido") else "", e(x.get("agregado_kev", "")))
    # lo accionable (lo que agrega revital.cves): como parchear, como mitigar mientras tanto, regla WAF copiable y exploits publicos
    if x.get("parche"):
        extra += '<p><b>Cómo parchear:</b> %s</p>' % e(x["parche"])
    if x.get("mitigacion"):
        extra += '<p><b>Mitigación mientras tanto:</b> %s</p>' % e(x["mitigacion"])
    if x.get("regla"):
        extra += '<p class="peq"><b>Regla lista para copiar:</b></p><pre>%s</pre>' % e(x["regla"])
    exps = x.get("exploits") or []
    if exps:
        extra += ('<p class="peq"><b>Exploits públicos conocidos (%d, índice de Exploit-DB):</b> sirven para entender la urgencia; ReVital no los descarga ni los ejecuta.</p><ul class="peq">%s</ul>'
                  % (len(exps), "".join("<li>EDB-%s · %s · %s</li>" % (e(str(z[0])), e(str(z[3])) if len(z) > 3 else "", e(str(z[4])) if len(z) > 4 else "") for z in exps[:5])))
    return ('<details class="h"%s><summary>%s <b>%s</b> %s %s %s<span class="mut">%s %s · CVSS %s</span></summary><div class="cu">'
            '<p><b>%s</b></p><p>%s</p>%s<p class="mut peq"><b>Por qué esta prioridad:</b> %s · confianza: %s</p>'
            '<p class="peq"><b>Dónde lo vimos:</b></p><ul class="peq">%s</ul></div></details>'
            % (" open" if abierto else "", chip(x.get("nivel_txt", "")), e(x["cve"]), kev, rw, "", e(x["producto"]), e(x["version"]), e(str(x.get("cvss", "-"))),
               e(x.get("nombre") or x["cve"]), e((x.get("descripcion") or "")[:600]), extra, e(x.get("motivo", "")), e(x.get("confianza", "")), ev))


def _config(items):
    """Alertas de configuracion insegura (web.config con debug=true, TLS obsoleto...)."""
    if not items:
        return ""
    return ("<h2>Configuración insegura detectada</h2>" + "".join(
        '<div class="card mal" style="margin-bottom:10px"><b>%s</b> · %s<br><span class="mut peq">%s</span></div>'
        % (e(i.get("tipo", "")), e(i.get("detalle", "")), ("Qué hacer: " + e(i["recomendacion"])) if i.get("recomendacion") else "") for i in items))


def entidad(x, tab, alertas, hist, archivos, todos=False, filtro=""):
    h, r = x["h"], x["r"]
    cab = ('<p class="sub"><a href="/">← Todas las entidades</a></p><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
           '<div><h1>%s</h1><p class="sub" style="margin:0">Evaluado el %s · catálogo CISA KEV %s · %d componentes analizados</p></div>'
           '<div>%s &nbsp; <a class="btn" href="/zip/%s">Descargar documentación (.zip)</a></div></div>'
           % (e(x["entidad"]), e(h.get("fecha_evaluacion", "")), e(h.get("catalogos", {}).get("kev_version", "?")), r["componentes"], estado_chip(r["cumple"]), e(x["slug"])))
    cuerpo = ""
    if tab == "hallazgos":
        hall = sorted(h.get("hallazgos", []), key=lambda z: (datos.ORDEN_NIVEL.get(z.get("nivel_txt"), 9), -float(z.get("cvss") or 0)))
        if filtro == "ransomware":
            hall = [z for z in hall if z.get("ransomware") == "Known"]
        elif filtro == "kev":
            hall = [z for z in hall if z.get("en_kev")]
        elif filtro == "otras":
            hall = [z for z in hall if not z.get("en_kev")]
        fl = "".join('<a class="btn%s" style="margin:0 6px 8px 0" href="/e/%s?tab=hallazgos&amp;f=%s">%s</a>' % ("" if f == filtro else " sec", e(x["slug"]), f, t)
                     for f, t in (("", "Todas"), ("kev", "Solo KEV (%d)" % r["kev"]), ("ransomware", "Con ransomware (%d)" % r["ransomware"]), ("otras", "No KEV (%d)" % r["otras"])))
        lim = len(hall) if todos else 60
        cuerpo = ("<p class=\"mut\">Ordenadas por prioridad. «KEV» = CISA confirma que se está explotando ahora mismo. Toca una fila para ver el detalle y la evidencia.</p>"
                  + fl + "".join(_hallazgo(z, i == 0) for i, z in enumerate(hall[:lim])))
        if len(hall) > lim:
            cuerpo += '<p><a class="btn sec" href="/e/%s?tab=hallazgos&amp;f=%s&amp;todos=1">Mostrar las %d restantes</a></p>' % (e(x["slug"]), e(filtro), len(hall) - lim)
        cond = h.get("condicionales", [])
        if cond:
            cuerpo += "<h2>Dependen de la configuración (verificar antes de descartar)</h2>" + "".join(_hallazgo(z) for z in cond)
    elif tab == "inventario":
        eol = {c["producto"] + "|" + c["version"] for c in h.get("eol", [])}
        sin = {c["producto"] + "|" + c["version"] for c in h.get("sin_mapeo", [])}
        filas = ""
        for c in sorted(h.get("componentes", []), key=lambda z: z["producto"].lower()):
            k = c["producto"] + "|" + c["version"]
            marca = ('<span class="chip" style="color:#ff6b62;background:#2a0a08">fuera de soporte</span> ' if k in eol else "") + \
                    ('<span class="chip" style="color:#9a9a9a;background:#1a1a1a">sin catálogo</span>' if k in sin else "")
            ev = "".join("<li><code>%s</code> · %s</li>" % (e(v.get("donde", "")), e(v.get("fuente", ""))) for v in c.get("evidencia", [])[:8])
            filas += ("<tr><td><b>%s</b><br><span class=\"mut peq\">detectado como: %s</span></td><td>%s</td><td>%s</td>"
                      "<td><details><summary class=\"peq\">%d evidencia(s)</summary><ul class=\"peq\">%s</ul></details></td></tr>"
                      % (e(c["producto"]), e(c.get("detectado_como", "")), e(c["version"] or "versión desconocida"), marca, len(c.get("evidencia", [])), ev))
        cuerpo = ('<p class="mut">Cada componente muestra cómo y dónde lo detectamos, para poder comprobarlo.</p><table><tr><th>Componente</th><th>Versión</th><th>Estado</th><th>Evidencia</th></tr>%s</table>' % filas)
    elif tab == "docs":
        filas = "".join('<tr><td>%s</td><td><b>%s</b></td><td>%s</td><td>%s</td><td><a href="/ver/%s">Ver</a> · <a href="/descargar/%s">Descargar</a></td></tr>'
                        % (e(a["tipo"]), e(a["nombre"]), kb(a["bytes"]), e(a["fecha"]), quote(a["nombre"]) if a["nombre"].endswith((".md", ".json")) else "", quote(a["nombre"]))
                        for a in archivos)
        cuerpo = ('<p class="mut">Toda la documentación que generó ReVital para esta entidad. Los <code>.md</code> se leen en pantalla; los <code>.json</code> sirven para otros sistemas.</p>'
                  '<p><a class="btn" href="/zip/%s">Descargar todo (.zip)</a></p><table><tr><th>Tipo</th><th>Archivo</th><th>Tamaño</th><th>Fecha</th><th></th></tr>%s</table>'
                  % (e(x["slug"]), filas or '<tr><td colspan="5" class="mut">No hay archivos.</td></tr>'))
    elif tab == "historial":
        cuerpo = _historial(alertas, hist)
    else:
        top = [z for z in sorted(h.get("hallazgos", []), key=lambda z: (datos.ORDEN_NIVEL.get(z.get("nivel_txt"), 9), -float(z.get("cvss") or 0))) if z.get("en_kev")][:5]
        msg = ('<div class="aviso mal"><b>%d vulnerabilidades explotadas activamente sin parchear.</b> %d se usan en campañas de ransomware y %d ya pasaron la fecha límite de CISA.</div>' % (r["kev"], r["ransomware"], r["vencidas"])
               if r["kev"] else '<div class="aviso bien"><b>No hay vulnerabilidades del catálogo KEV abiertas</b> en lo que se analizó.</div>')
        ks = "".join((kpi(r["kev"], "KEV abiertas", "mal" if r["kev"] else "bien"), kpi(r["ransomware"], "usadas en ransomware", "mal" if r["ransomware"] else "bien"),
                      kpi(r["vencidas"], "con fecha límite vencida", "med" if r["vencidas"] else "bien"), kpi(r["otras"], "otras conocidas (no KEV)"),
                      kpi(r["condicionales"], "dependen de configuración"), kpi(r["eol"], "fuera de soporte", "med" if r["eol"] else "bien")))
        filas = "".join("<tr><td>%s</td><td><b>%s</b></td><td>%s %s</td><td class=\"peq\">%s</td></tr>" % (chip(z["nivel_txt"]), e(z["cve"]), e(z["producto"]), e(z["version"]), e(z.get("accion", ""))) for z in top)
        recientes = datos_alertas_mini(alertas)
        cuerpo = (tablero.html_tablero(h) + msg + '<div class="grid" style="margin:0 -9px">%s</div><h2>Qué parchear primero</h2><table><tr><th>Prioridad</th><th>CVE</th><th>Componente</th><th>Acción requerida (CISA)</th></tr>%s</table>'
                  '<p><a href="/e/%s?tab=hallazgos">Ver todas las vulnerabilidades →</a></p>%s%s' % (ks, filas, e(x["slug"]), _config(h.get("configuracion")), recientes))
    return pagina(x["entidad"], cab + _tabs(x["slug"], tab) + cuerpo, "inicio")


def datos_alertas_mini(alertas):
    if not alertas:
        return ""
    return "<h2>Cambios recientes (sentinela)</h2>" + _lista_alertas(alertas[:5])


def _lista_alertas(alertas):
    return "".join('<div class="ev">%s <b>%s</b> <span class="mut peq">%s · %s</span><br>%s</div>' % (chip_sev(a.get("severidad", "info")), e(a.get("tipo", "")), e(a.get("ts", "")), e(a.get("entidad", "")), e(a.get("detalle", ""))) for a in alertas)


def _historial(alertas, hist):
    if not hist and not alertas:
        return '<div class="card"><p class="mut">Todavía no hay cambios registrados. Cuando el sentinela vuelva a analizar y encuentre diferencias, aparecerán aquí con el antes y el después.</p><p><a href="/sentinela">Configurar el sentinela</a></p></div>'
    b = ["<p class=\"mut\">Lo que cambió entre una vigilancia y la siguiente.</p>"]
    if alertas:
        b.append('<div class="tl">%s</div>' % _lista_alertas(alertas))
    b.append("<h2>Revisiones</h2><table><tr><th>Fecha</th><th>Componentes</th><th>KEV abiertas</th><th>Cumplimiento</th><th>Cambios</th></tr>")
    for s in hist:
        f = s.get("foto", {})
        b.append("<tr><td>%s%s</td><td>%d</td><td>%d</td><td>%s</td><td>%d</td></tr>" % (e(s.get("ts", "")), " <span class=\"mut peq\">(línea base)</span>" if s.get("linea_base") else "",
                                                                                         len(f.get("componentes", {})), len(f.get("kev", {})), estado_chip(f.get("cumple", False)), len(s.get("eventos", []))))
    b.append("</table>")
    return "".join(b)


# ---------------------------------------------------------------- sentinela
def sentinela(estado_s, alertas, config_ejemplo):
    if estado_s:
        marcha = estado_s.get("en_marcha")
        b = ['<div class="aviso %s"><b>%s</b>%s</div>' % ("bien" if marcha else "", "Sentinela en marcha" if marcha else "Sentinela detenido",
                                                           (" · cada %s min · última vuelta: %s · próxima: %s" % (e(str(estado_s.get("cada_minutos", "?"))), e(str(estado_s.get("ultima_vuelta", "—"))), e(str(estado_s.get("proxima_vuelta", "—"))))) if marcha else
                                                           " · última vuelta: %s" % e(str(estado_s.get("ultima_vuelta", "—"))))]
        objs = estado_s.get("objetivos") or []
        if objs:
            b.append("<h2>Qué vigila</h2><table><tr><th>Entidad</th><th>Tipo</th><th>Destino</th><th>Última vez</th></tr>%s</table>" % "".join(
                "<tr><td>%s</td><td>%s</td><td><code>%s</code></td><td>%s</td></tr>" % (e(o.get("entidad", "")), e(o.get("tipo", "")), e(o.get("destino", "")),
                                                                                         "OK" if o.get("ok") else "<span style=\"color:#e10600\"><b>falló</b> %s</span>" % e(o.get("detalle", ""))) for o in objs))
    else:
        b = ['<div class="aviso"><b>El sentinela todavía no se ha ejecutado.</b> Vigila en segundo plano y avisa cuando algo cambia.</div>']
    b.append('<h2>Alertas</h2>' + ('<div class="tl">%s</div>' % _lista_alertas(alertas) if alertas else '<p class="mut">Sin alertas todavía.</p>'))
    b.append('<h2>Cómo activarlo</h2><div class="card"><p>1. Copia <code>revital/sentinela.ejemplo.json</code> como <code>sentinela.json</code> y pon tus objetivos.<br>'
             '2. Déjalo corriendo (puede ser en el mismo equipo viejo):</p><pre>python -m revital.sentinela --config sentinela.json</pre>'
             '<p>Cada vuelta vuelve a analizar, compara con la anterior y registra lo nuevo aquí. Si defines <code>al_detectar_cambio</code>, ejecuta ese comando propio con los detalles.</p>'
             '<form method="post" action="/vigilar-ahora"><button class="btn" type="submit">Vigilar ahora (una vuelta)</button></form>'
             '<p class="mut peq">Ejemplo de configuración:</p><pre>%s</pre></div>' % e(config_ejemplo))
    return pagina("Sentinela", "<h1>Sentinela</h1><p class=\"sub\">Vigila los sistemas y avisa cuando aparece un componente nuevo, cambia una versión o se abre una vulnerabilidad explotada.</p>" + "".join(b), "sentinela")


# ---------------------------------------------------------------- trabajos y documentos
def trabajos(lista):
    if not lista:
        cuerpo = '<p class="mut">Todavía no lanzaste ningún análisis desde el panel.</p>'
    else:
        cuerpo = "".join('<div class="card" style="margin-bottom:12px"><div style="display:flex;justify-content:space-between"><b>%s · %s</b><span class="estado %s">%s</span></div>'
                         '<p class="mut peq" style="margin:2px 0">%s · iniciado %s</p><pre style="max-height:220px">%s</pre>%s</div>'
                         % (e(t["entidad"]), e(t["tipo"]), "si" if t["estado"] == "listo" else ("no" if t["estado"] == "error" else ""), e(t["estado"]), e(t["destino"]), e(t["inicio"]), e(t["log"][-1800:]),
                            ('<a class="btn" href="/e/%s">Ver resultado</a>' % e(t["slug"])) if t["estado"] == "listo" else "") for t in lista)
    return pagina("Análisis", "<h1>Análisis</h1><p class=\"sub\">Lo que se está analizando o se analizó desde este panel.</p>" + cuerpo + "<h2>Nuevo análisis</h2>" + form_analisis(), "trabajos")


def md_a_html(t):
    """Markdown minimo de los reportes: titulos, tablas, listas, negritas, codigo y citas."""
    def inline(s):
        s = e(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    out, tabla, lista = [], [], False
    def cerrar():
        nonlocal tabla, lista
        if tabla:
            filas = [f for f in tabla if not re.match(r"^\s*\|[\s:|-]+\|\s*$", f)]
            def celdas(f):
                return [c.strip() for c in f.strip().strip("|").split("|")]
            if filas:
                out.append("<table><tr>%s</tr>%s</table>" % ("".join("<th>%s</th>" % inline(c) for c in celdas(filas[0])),
                                                             "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in celdas(f)) for f in filas[1:])))
            tabla = []
        if lista:
            out.append("</ul>")
            lista = False
    for linea in t.splitlines():
        if linea.strip().startswith("|"):
            if lista:
                cerrar()
            tabla.append(linea)
            continue
        cerrar()
        m = re.match(r"^(#{1,4})\s+(.*)", linea)
        if m:
            out.append("<h%d>%s</h%d>" % (len(m.group(1)), inline(m.group(2)), len(m.group(1))))
        elif re.match(r"^\s*[-*]\s+", linea):
            out.append("<ul>") if not lista else None
            lista = True
            out.append("<li>%s</li>" % inline(re.sub(r"^\s*[-*]\s+", "", linea)))
        elif linea.startswith(">"):
            out.append('<div class="aviso">%s</div>' % inline(linea.lstrip("> ")))
        elif linea.strip():
            out.append("<p>%s</p>" % inline(linea))
    cerrar()
    return "".join(out)


def documento(nombre, texto, slug=None):
    cuerpo = md_a_html(texto) if nombre.endswith(".md") else "<pre>%s</pre>" % e(texto[:200000])
    volver = '<p class="sub"><a href="%s">← Volver</a> · <a class="btn sec" href="/descargar/%s">Descargar</a></p>' % ("/e/%s?tab=docs" % e(slug) if slug else "/", quote(nombre))
    return pagina(nombre, volver + '<div class="md">%s</div>' % cuerpo)


def error(codigo, texto):
    return pagina("Error", '<div class="card"><h1>%s</h1><p>%s</p><p><a href="/">Volver al inicio</a></p></div>' % (codigo, e(texto)))
