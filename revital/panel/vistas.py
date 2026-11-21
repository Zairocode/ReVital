"""HTML del panel. JavaScript opcional y local (static/: GSAP + panel.js), sin nada de internet y sin variables CSS: se ve igual
en navegadores viejos y sin conexion."""
import html, re
from urllib.parse import quote

from revital.panel import cubos, datos, tablero

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
.hero{text-align:center;padding:26px 0 8px}
.hero .llaves{display:inline-flex;align-items:center;color:#cfcab4;font-size:15px;line-height:1.35}
.hero .llaves span{font-size:44px;font-weight:300;color:#8a8672;margin:0 14px;line-height:1}
.hero .llaves p{margin:0}
.hero h1{font-size:88px;line-height:1.02;font-weight:500;letter-spacing:-2.5px;color:#fbf6df;margin:18px 0 26px}
.buscar{display:flex;align-items:center;max-width:960px;margin:0 auto;border:1px solid #4a4a4e;border-radius:999px;padding:6px 6px 6px 22px;background:#121214}
.buscar:focus-within{border-color:#cfcab4}
.buscar svg{flex:0 0 18px;margin-right:12px}
.buscar input[type=text]{border:0;background:transparent;padding:12px 4px;font-size:16px;color:#f2f2f2;border-radius:0}
.buscar input[type=text]:focus{outline:0}
.buscar .dest{flex:1 1 auto}
.buscar .ent{flex:0 0 190px;border-left:1px solid #2e2e32;padding-left:16px}
.buscar .btn{border-radius:999px;margin-left:8px;padding:12px 18px 12px 22px;background:#fbf6df;color:#0e0e0f;white-space:nowrap;display:inline-flex;align-items:center}
.buscar .btn:hover{background:#fff}
.kbd{display:inline-block;background:#26262a;color:#a1a1a6;border-radius:6px;padding:2px 7px;font-size:12px;margin-left:8px}
.consent{color:#7d7d82;font-size:13px;text-align:center;margin:12px 0 28px}
.pills{display:flex;flex-wrap:wrap;align-items:center;margin:6px 0 14px}
.pill{display:inline-flex;align-items:center;background:#1a1a1c;color:#c9c9ce;border-radius:999px;padding:8px 16px;margin:0 8px 8px 0;font-weight:600;font-size:14px}
.pill:hover{color:#fff;background:#232326} .pill.act{background:#fbf6df;color:#0e0e0f}
.pt{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px} .pt.mal{background:#ff5a3c} .pt.bien{background:#34c38f} .pt.nd{background:#6b6b70}
.nd-t{font-size:10px;color:#8a8a8f;margin-left:8px;font-weight:700;letter-spacing:.4px} .pill.act .nd-t{color:#55554c}
.ent-cab{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin:4px 0 4px}
.ent-cab h2{margin:0;font-size:22px}
.escaneo{display:flex;align-items:center;background:#1a1a1c;border-radius:20px;padding:16px 20px;margin:0 auto 12px;max-width:960px}
.escaneo .punto{position:relative;width:12px;height:12px;margin:0 16px 0 4px;flex:0 0 12px}
.escaneo .punto i{position:absolute;left:0;top:0;width:12px;height:12px;border-radius:50%;background:#fbf6df}
.escaneo.listo .punto i{background:#34c38f} .escaneo.error .punto i{background:#ff5a3c}
.escaneo .barra{height:3px;background:#26262a;border-radius:3px;overflow:hidden;margin-top:8px;position:relative}
.escaneo .barra b{position:absolute;left:-40%;top:0;height:3px;width:40%;background:#fbf6df;animation:barrido 1.4s infinite ease-in-out}
@keyframes barrido{to{left:100%}}
.escaneo .txt{flex:1 1 auto} .escaneo details{margin-top:6px}
.vig{display:inline-block;margin:0 8px 0 0}
.switch{display:inline-flex;align-items:center;border:0;border-radius:999px;padding:8px 14px 8px 8px;background:#1a1a1c;color:#c9c9ce;font:600 13px "Instrument Sans","Segoe UI",Arial,sans-serif;cursor:pointer}
.switch i{display:inline-block;width:34px;height:20px;border-radius:999px;background:#3a3a3e;margin-right:10px;position:relative}
.switch i:after{content:"";position:absolute;top:3px;left:3px;width:14px;height:14px;border-radius:50%;background:#fff;transition:left .2s}
.switch.on i{background:#34c38f} .switch.on i:after{left:17px} .switch.on{color:#fff}
#carga{position:fixed;left:0;top:0;right:0;bottom:0;background:#0e0e0f;z-index:50;display:flex;flex-direction:column;align-items:center;justify-content:center;animation:salir .4s 1.6s forwards}
#carga.js{animation:none}
@keyframes salir{to{opacity:0;visibility:hidden}}
@media (max-width:760px){.hero h1{font-size:52px;letter-spacing:-1px}.buscar{flex-wrap:wrap;border-radius:22px}.buscar .ent{flex:1 1 100%;border-left:0;padding-left:0}}
@font-face{font-family:"Instrument Sans";font-weight:400;font-display:swap;src:url(/static/instrument-sans-latin-400-normal.woff2) format("woff2")}
@font-face{font-family:"Instrument Sans";font-weight:500;font-display:swap;src:url(/static/instrument-sans-latin-500-normal.woff2) format("woff2")}
@font-face{font-family:"Instrument Sans";font-weight:600;font-display:swap;src:url(/static/instrument-sans-latin-600-normal.woff2) format("woff2")}
@font-face{font-family:"Instrument Sans";font-weight:700;font-display:swap;src:url(/static/instrument-sans-latin-700-normal.woff2) format("woff2")}
body,.btn,input[type=text],select,.tb{font-family:"Instrument Sans","Segoe UI",system-ui,Arial,sans-serif}
#carga{animation:salir .4s 3.8s forwards}
#carga .cubos-c{margin-bottom:10px}
#carga .marca-c{font-size:88px;font-weight:500;letter-spacing:-2.5px;color:#fbf6df;line-height:1;padding:0 6px}
em.v{font-style:normal;color:#ff5a3c}
html{scroll-behavior:smooth} #tablero{scroll-margin-top:16px}
.hero form{margin:0}
@media print{.top,.tabs,.btn,.nav,.pie{display:none} body{background:#fff;color:#000}}
"""

LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38"><path d="M19 2 33 7v11c0 9-6 15-14 18C11 33 5 27 5 18V7Z" fill="#ff5a3c"/>'
        '<path d="M19 6 29 9.500V18c0 6.500-4 11-10 13.500C13 29 9 24.500 9 18V9.500Z" fill="#0e0e0f"/>'
        '<path d="M13.500 18.500 17.500 22.500 25 14" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def pagina(titulo, cuerpo, activo="inicio"):
    return ("<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s · ReVital</title><style>%s</style></head><body>"
            "<div id=\"carga\" aria-hidden=\"true\">%s<div class=\"marca-c\">Re<em class=\"v\">Vital</em></div></div>"
            "<div class=\"top\"><div class=\"in\"><a class=\"marca\" href=\"/\">%s<div><b>Re<em class=\"v\">Vital</em></b><span>una segunda vida segura para sistemas legacy</span></div></a>"
            "<div class=\"nav\"><a href=\"/\"%s>Análisis</a></div></div></div><div class=\"wrap\">%s</div>"
            "<div class=\"pie\">Panel local · solo este equipo (127.0.0.1) · sin conexión a internet · usar solo en sistemas propios o con autorización</div>"
            "<script src=\"/static/gsap.min.js\" defer></script><script src=\"/static/panel.js\" defer></script></body></html>"
            % (e(titulo), CSS, cubos.carga(), LOGO, ' class="act"' if activo == "inicio" else "", cuerpo))

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
        return '<span class="estado" style="background:#26262a;color:#c9c9ce">SIN DATOS</span>'
    return '<span class="estado si">CUMPLE</span>' if cumple else '<span class="estado no">NO CUMPLE</span>'


# ---------------------------------------------------------------- inicio
def inicio(ents, alertas, estado_s, mensaje="", trabajos=(), sel=""):
    x = next((z for z in ents if z["slug"] == sel), ents[0]) if ents else None
    b = ['<div class="hero"><div class="llaves"><span>{</span><p>Una segunda vida para los sistemas que sostienen tu institución:<br>'
         'conoce lo que tienen y ponlos a salvo.</p><span>}</span></div><h1><span>Re<em class="v">Vital</em>iza</span> <span>tu sistema</span></h1>' + form_analisis(bool(ents)) + "</div>"]
    b.append('<div id="tablero"></div>')
    if mensaje:
        b.append('<div class="aviso bien anim">%s</div>' % e(mensaje))
    for t in list(trabajos)[:3]:
        est = t["estado"]
        cls = "" if est == "en curso" else ("listo" if est == "listo" else "error")
        txt = {"en curso": "Analizando", "listo": "Listo", "error": "No se pudo analizar"}.get(est, est)
        extra = ('<div class="barra"><b></b></div>' if est == "en curso" else
                 ('<a style="margin-left:10px" href="/?e=%s#tablero">Ver resultado →</a>' % e(t["slug"]) if est == "listo" else
                  '<details><summary class="mut peq">Ver detalle</summary><pre style="max-height:200px">%s</pre></details>' % e(t["log"][-1500:])))
        b.append('<div class="escaneo anim %s"><div class="punto"><i class="pulso"></i><i></i></div><div class="txt"><b>%s</b> '
                 '<span class="mut">%s · %s%s</span>%s</div></div>'
                 % (cls, txt, e(t["destino"]), e(t["entidad"]), " · modo compatible (servidor viejo)" if t.get("compatible") else "", extra))
    graves = [a for a in alertas[:20] if a.get("severidad") in ("critica", "alta")]
    if graves:
        b.append('<div class="aviso mal anim"><b>Cambios importantes detectados por la vigilancia:</b> %s</div>' % e(graves[0].get("detalle", "")))
    if not ents:
        b.append('<div class="card anim" style="text-align:center"><h3>Todavía no hay análisis</h3><p class="mut">Escribe arriba la URL de un sitio o la carpeta '
                 'de una aplicación, o carga el caso de demostración (portal municipal ficticio).</p>'
                 '<form method="post" action="/demo"><button class="btn" type="submit">Cargar demostración</button></form></div>')
        return pagina("Análisis", "".join(b), "inicio")
    b.append('<div class="pills anim" id="sistemas">%s</div>' % "".join(
        '<a class="pill%s" href="/?e=%s#tablero"><i class="pt %s"></i>%s%s</a>' % (" act" if z is x else "", e(z["slug"]),
                                                                      "nd" if z["r"].get("sin_datos") else ("bien" if z["r"]["cumple"] else "mal"),
                                                                      e(z["entidad"]), ' <span class="nd-t">%s</span>' % ("SIN DATOS" if z["r"].get("sin_datos") else ("CUMPLE" if z["r"]["cumple"] else "NO CUMPLE")))
        for z in ents))
    h, r = x["h"], x["r"]
    b.append('<div class="ent-cab anim"><div><h2>%s</h2><p class="sub" style="margin:2px 0 0">Evaluado el %s · catálogo CISA KEV %s · %d componentes</p></div>'
             '<div>%s &nbsp; <a class="btn sec" href="/e/%s?tab=hallazgos">Ver detalle</a> <a class="btn sec" href="/zip/%s">Descargar (.zip)</a></div></div>'
             % (e(x["entidad"]), e(h.get("fecha_evaluacion", "")), e(h.get("catalogos", {}).get("kev_version", "?")), r["componentes"],
                estado_chip(r["cumple"], r.get("sin_datos")), e(x["slug"]), e(x["slug"])))
    if r.get("sin_datos"):  # un fallo nunca se presenta como "cumple" ni con un tablero verde
        b.append('<div class="aviso mal anim"><b>SIN DATOS: no se pudo evaluar.</b> No se detecto ningun componente (el objetivo no respondio o no '
                 'se pudo leer). Esto <b>no</b> significa que este libre de vulnerabilidades. Revisa el detalle y vuelve a analizar.</div>')
        return pagina("Análisis", "".join(b), "inicio")
    if h.get("sin_respuesta"):
        b.append('<div class="aviso mal anim"><b>Resultado incompleto:</b> %s no respondio. Los datos de ese objetivo faltan; no lo des por seguro.</div>'
                 % ", ".join("<code>%s</code>" % e(z.get("target", "")) for z in h["sin_respuesta"]))
    b.append(tablero.html_tablero(h))
    top = [z for z in sorted(h.get("hallazgos", []), key=lambda z: (datos.ORDEN_NIVEL.get(z.get("nivel_txt"), 9), -float(z.get("cvss") or 0))) if z.get("en_kev")][:5]
    if top:
        filas = "".join("<tr><td>%s</td><td><b>%s</b></td><td>%s %s</td><td class=\"peq\">%s</td></tr>" % (
            chip(z["nivel_txt"]), e(z["cve"]), e(z["producto"]), e(z["version"]), e(z.get("parche") or z.get("accion", ""))) for z in top)
        b.append('<h2>Qué parchear primero</h2><table class="anim"><tr><th>Prioridad</th><th>CVE</th><th>Componente</th><th>Cómo corregir</th></tr>%s</table>'
                 '<p><a href="/e/%s?tab=hallazgos">Ver todas las vulnerabilidades →</a></p>' % (filas, e(x["slug"])))
    return pagina("Análisis", "".join(b), "inicio")

def form_analisis(hay_datos=True):
    lupa = ('<svg width="18" height="18" viewBox="0 0 18 18"><circle cx="7.5" cy="7.5" r="6" fill="none" stroke="#cfcab4" stroke-width="1.700"/>'
            '<path d="m12 12 4.500 4.500" stroke="#cfcab4" stroke-width="1.700" stroke-linecap="round"/></svg>')
    return ('<form id="analizar" class="buscar" method="post" action="/analizar">%s'
            '<input class="dest" type="text" name="destino" placeholder="URL del sitio (http://...) o carpeta de la aplicación (C:\\inetpub\\portal)" required>'
            '<input class="ent" type="text" name="entidad" placeholder="Institución (ej. MUNI-GT)" required>'
            '<input type="hidden" name="autorizo" value="1"><button class="btn" type="submit">Analizar<span class="kbd">Enter</span></button></form>'
            '<p class="consent">Al analizar confirmas que tienes autorización sobre este sistema · Solo lectura: no se modifica nada</p>' % lupa)

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


def entidad(x, tab, alertas, hist, archivos, todos=False, filtro="", vigilada=False):
    h, r = x["h"], x["r"]
    vig = ('<form class="vig" method="post" action="/vigilar"><input type="hidden" name="slug" value="%s"><input type="hidden" name="activar" value="%s">'
           '<button class="switch%s" type="submit" title="Vuelve a analizar este sistema cada hora y avisa si algo cambia"><i></i>%s</button></form>'
           % (e(x["slug"]), "0" if vigilada else "1", " on" if vigilada else "", "Vigilando cada hora" if vigilada else "Vigilar cada hora"))
    cab = ('<p class="sub"><a href="/?e=%s#tablero">← Análisis</a></p><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
           '<div><h1>%s</h1><p class="sub" style="margin:0">Evaluado el %s · catálogo CISA KEV %s · %d componentes analizados</p></div>'
           '<div>%s%s &nbsp; <a class="btn" href="/zip/%s">Descargar documentación (.zip)</a></div></div>'
           % (e(x["slug"]), e(x["entidad"]), e(h.get("fecha_evaluacion", "")), e(h.get("catalogos", {}).get("kev_version", "?")), r["componentes"],
              vig, estado_chip(r["cumple"], r.get("sin_datos")), e(x["slug"])))
    if alertas and tab == "resumen":
        a = alertas[0]
        cab += ('<div class="aviso %s anim" style="margin-top:14px"><b>Último cambio (%s):</b> %s · <a href="/e/%s?tab=historial">ver todos los cambios</a></div>'
                % ("mal" if a.get("severidad") in ("critica", "alta") else "", e(a.get("ts", "")), e(a.get("detalle", "")), e(x["slug"])))
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
        if h.get("sin_respuesta"):
            msg = ('<div class="aviso mal"><b>Resultado incompleto:</b> %s no respondio. Los datos de ese objetivo faltan; no lo des por seguro.</div>'
                   % ", ".join("<code>%s</code>" % e(z.get("target", "")) for z in h["sin_respuesta"])) + msg
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
