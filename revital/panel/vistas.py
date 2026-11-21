"""HTML del panel. Sin JavaScript obligatorio, sin fuentes ni librerias de internet y sin variables CSS: asi se ve igual
en navegadores viejos y sin conexion."""
import html, re
from urllib.parse import quote

from revital.panel import datos, tablero

e = html.escape
COLOR = {"CRITICO": ("#ff6b57", "rgba(255,90,60,.16)"), "URGENTE (vencido)": ("#ff6b57", "rgba(255,90,60,.12)"),
         "URGENTE": ("#ff8a75", "rgba(255,90,60,.10)"), "ALTO (exploit publico)": ("#ffa38f", "rgba(255,90,60,.08)"),
         "ALTO": ("#d4d4d8", "#26262a"), "MEDIO": ("#b4b4ba", "#232326"), "BAJO": ("#8a8a8f", "#202023")}
SEV_ALERTA = {"critica": ("#ff6b57", "rgba(255,90,60,.16)"), "alta": ("#ff8a75", "rgba(255,90,60,.10)"), "media": ("#d4d4d8", "#26262a"), "info": ("#8a8a8f", "#202023")}

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#0e0e0f;color:#f2f2f2;font:15px/1.55 "Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif}
a{color:#ffffff;text-decoration:none;font-weight:600} a:hover{color:#ff7a5c}
.top{background:#0e0e0f;color:#fff;padding:0}
.top .in{max-width:1200px;margin:0 auto;padding:16px 22px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap}
.marca{display:flex;align-items:center;color:#fff} .marca:hover{color:#fff}
.marca svg{margin-right:12px} .marca b{font-size:19px;font-weight:700} .marca span{display:block;font-size:12px;color:#7d7d80}
.nav a{color:#a1a1a6;margin-left:6px;padding:9px 16px;border-radius:12px;font-weight:600;font-size:14px;display:inline-block}
.nav a:hover{color:#fff;background:#1a1a1c} .nav a.act{color:#ff7a5c;background:#1c1c1e}
.wrap{max-width:1200px;margin:0 auto;padding:18px 22px 24px}
h1{font-size:26px;margin:4px 0 2px;font-weight:700} h3{font-size:16px;margin:0 0 6px;font-weight:600}
h2{font-size:17px;margin:30px 0 12px;font-weight:600;color:#f2f2f2}
.sub{color:#7d7d80;margin:0 0 18px;font-size:14px}
.card{background:#1a1a1c;border-radius:20px;padding:22px}
.grid{display:flex;flex-wrap:wrap;margin:0 -9px}
.grid>.card,.grid>.k{margin:9px;flex:1 1 300px}
.k{background:#1a1a1c;border-radius:20px;padding:18px 20px;flex:1 1 150px;min-width:150px}
.k .n{font-size:32px;font-weight:700;line-height:1.15;color:#fff} .k .t{color:#9a9a9f;font-size:13px}
.k.mal .n,.k.med .n{color:#ff6b57} .k.bien .n{color:#34c38f}
.chip{display:inline-block;border-radius:8px;padding:2px 9px;font-size:12px;font-weight:600;white-space:nowrap}
.estado{display:inline-block;border-radius:8px;padding:5px 12px;font-weight:700;font-size:12px}
.si{background:rgba(52,195,143,.14);color:#34c38f} .no{background:rgba(255,90,60,.14);color:#ff6b57}
.btn{display:inline-block;background:#f2f2f2;color:#0e0e0f;border:0;border-radius:12px;padding:9px 16px;font:600 14px "Segoe UI",Arial,sans-serif;cursor:pointer}
.btn:hover{background:#ffffff;color:#0e0e0f} .btn.sec{background:#262628;color:#e5e5e5} .btn.sec:hover{background:#303033;color:#fff}
.tabs{margin:18px 0 18px;background:#1a1a1c;border-radius:14px;padding:5px;display:inline-block}
.tabs a{display:inline-block;padding:8px 16px;color:#a1a1a6;font-weight:600;font-size:14px;border-radius:10px}
.tabs a.act{color:#fff;background:#2a2a2d} .tabs a:hover{color:#fff}
table{width:100%;border-collapse:separate;border-spacing:0;background:#1a1a1c;border-radius:20px;overflow:hidden;font-size:14px;padding:10px 14px}
th{background:#232326;text-align:left;padding:10px 12px;color:#a1a1a6;font-size:12px;font-weight:600;letter-spacing:.3px;text-transform:uppercase}
th:first-child{border-radius:10px 0 0 10px} th:last-child{border-radius:0 10px 10px 0}
td{padding:12px;border-bottom:1px solid #26262a;vertical-align:top;color:#e5e5e5} tr:last-child td{border-bottom:0}
details.h{background:#1a1a1c;border-radius:16px;margin:0 0 10px;padding:0}
details.h summary{cursor:pointer;padding:14px 16px;list-style:none} details.h summary::-webkit-details-marker{display:none}
details.h summary b{margin:0 8px} details.h[open]{background:#1e1e21}
details.h .cu{padding:4px 18px 16px;color:#d4d4d8;border-top:1px solid #2a2a2e}
details summary{cursor:pointer}
.cu p{margin:8px 0} .mut{color:#8a8a8f} .peq{font-size:13px}
.aviso{background:#1a1a1c;border-radius:16px;padding:14px 18px;margin:0 0 16px;color:#e5e5e5}
.aviso.mal b{color:#ff6b57} .aviso.bien b{color:#34c38f}
label{display:block;font-weight:600;margin:12px 0 6px;font-size:13px;color:#a1a1a6}
input[type=text],select{width:100%;padding:11px 13px;border:1px solid #2a2a2e;border-radius:12px;font:14px "Segoe UI",Arial,sans-serif;background:#111113;color:#fff}
input[type=text]:focus,select:focus{border-color:#55555c;outline:0}
.fila{display:flex;flex-wrap:wrap;margin:0 -8px} .fila>div{padding:0 8px;flex:1 1 220px}
.chk{font-weight:400;display:block;margin:10px 0;font-size:14px;color:#d4d4d8} .chk input{margin-right:8px}
pre{background:#111113;color:#e5e5e5;border-radius:12px;padding:14px;overflow:auto;font:13px/1.45 Consolas,"Courier New",monospace}
code{background:#26262a;color:#f2f2f2;border-radius:6px;padding:1px 6px;font:13px Consolas,"Courier New",monospace}
.md{background:#1a1a1c;border-radius:20px;padding:8px 28px 22px;color:#e5e5e5}
.md h1{font-size:24px;margin-top:18px} .md table{margin:10px 0;background:#141416} .md a{color:#fff;text-decoration:underline}
.pie{color:#5a5a5f;text-align:center;font-size:12px;padding:26px 0}
.tl{border-left:2px solid #2a2a2e;margin:6px 0 6px 8px;padding:0 0 0 16px} .tl .ev{margin:0 0 12px}
@media (max-width:640px){.nav a{margin:4px 4px 0 0} h1{font-size:22px}}
@media print{.top,.tabs,.btn,.nav,.pie{display:none} body{background:#fff;color:#000}}
"""

LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38"><path d="M19 2 33 7v11c0 9-6 15-14 18C11 33 5 27 5 18V7Z" fill="#ff5a3c"/>'
        '<path d="M19 6 29 9.500V18c0 6.500-4 11-10 13.500C13 29 9 24.500 9 18V9.500Z" fill="#0e0e0f"/>'
        '<path d="M13.500 18.500 17.500 22.500 25 14" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


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
    fg, bg = COLOR.get(nivel, ("#8a8a8f", "#202023"))
    return '<span class="chip" style="color:%s;background:%s">%s</span>' % (fg, bg, e(nivel))


def chip_sev(sev):
    fg, bg = SEV_ALERTA.get(sev, ("#8a8a8f", "#202023"))
    return '<span class="chip" style="color:%s;background:%s">%s</span>' % (fg, bg, e(sev))


def kb(n):
    return "%d B" % n if n < 1024 else "%.1f KB" % (n / 1024.0) if n < 1048576 else "%.1f MB" % (n / 1048576.0)


def kpi(n, texto, clase="neu"):
    return '<div class="k %s"><div class="n">%s</div><div class="t">%s</div></div>' % (clase, e(str(n)), e(texto))


def estado_chip(cumple, sin_datos=False):
    if sin_datos:
        return '<span class="estado" style="background:#e2e8f0;color:#334155">SIN DATOS</span>'
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
                     % ("bien" if r["cumple"] else "mal", e(x["entidad"]), estado_chip(r["cumple"], r.get("sin_datos")), e(x["h"].get("fecha_evaluacion", "")),
                        e(x["h"].get("catalogos", {}).get("kev_version", "?")), "#ff6b57" if r["kev"] else "#34c38f",
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
    kev = ('<span class="chip" style="color:#ff6b57;background:rgba(255,90,60,.16)">EN KEV</span> ' if x.get("en_kev") else "")
    rw = ('<span class="chip" style="color:#ff8a75;background:rgba(255,90,60,.10)">ransomware</span> ' if x.get("ransomware") == "Known" else "")
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
           % (e(x["entidad"]), e(h.get("fecha_evaluacion", "")), e(h.get("catalogos", {}).get("kev_version", "?")), r["componentes"], estado_chip(r["cumple"], r.get("sin_datos")), e(x["slug"])))
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
            marca = ('<span class="chip" style="color:#ff8a75;background:rgba(255,90,60,.10)">fuera de soporte</span> ' if k in eol else "") + \
                    ('<span class="chip" style="color:#8a8a8f;background:#202023">sin catálogo</span>' if k in sin else "")
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
        if r.get("sin_datos"):
            return pagina(x["entidad"], cab + _tabs(x["slug"], tab) + '<div class="aviso mal"><b>SIN DATOS: no se pudo evaluar.</b> '
                          'No se detecto ningun componente (el objetivo no respondio o no se pudo leer). Esto <b>no</b> significa que este libre de '
                          'vulnerabilidades. Revisa la pestana Documentacion para ver el error y vuelve a analizar.</div>', "inicio")
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
                                                                                         "OK" if o.get("ok") else "<span style=\"color:#ff6b57\"><b>falló</b> %s</span>" % e(o.get("detalle", ""))) for o in objs))
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
