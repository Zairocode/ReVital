"""Reporte final por entidad: salida/reporte-<entidad>.md (para el jefe de TI) + hallazgos-<entidad>.json."""
import json, os, time

from revital import inventory


def _celda(t):
    return str(t if t is not None else "").replace("|", "/").replace("\n", " ")


def _donde(comp_o_h):
    ev = comp_o_h["evidencia"]
    txt = "; ".join("%s (%s)" % (e["donde"], e["fuente"]) for e in ev[:2])
    return txt + (" y %d mas" % (len(ev) - 2) if len(ev) > 2 else "")


def _corto(t, n=160):
    t = (t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."


def markdown(entidad, inventarios, res, info, hoy, reglas):
    h, cond = res["hallazgos"], res["condicionales"]
    kev = [x for x in h if x["en_kev"]]
    ransom = [x for x in kev if x["nivel"] == 1]
    vencidos = [x for x in kev if x.get("vencido")]
    con_ver = [c for c in res["componentes"] if c["version"]]
    L = ["# Reporte ReVital: %s" % entidad, "",
         "Generado: %s | Fecha de evaluacion: %s" % (time.strftime("%Y-%m-%d %H:%M"), hoy), ""]
    if info["ejemplo"]:
        L += ["> **Aviso:** este reporte uso **catalogos de ejemplo** (datos reducidos para la demo). "
              "Para un reporte real hacen falta `catalogos/kev.json` y `catalogos/nvd-kev.json` (ver `catalogos/LEEME.md`).", ""]
    L += ["Objetivos analizados:", ""] + ["- `%s` (%s), inventario del %s" % (i["target"], i["kind"], i["generado"])
                                         for i in inventarios]
    L += ["", "Catalogos: CISA KEV version %s (%s, `%s`); NVD: %s (%d CVE)." % (
        info["kev_version"] or "?", info["kev_fecha"] or "?", info.get("kev_fuente", ""), info["nvd_fuente"],
        info["nvd_cves"]), ""]

    L += ["## Resumen", "",
          "| Indicador | Valor |", "|---|---|",
          "| Componentes detectados | %d (%d con version) |" % (len(res["componentes"]), len(con_ver)),
          "| Vulnerabilidades del catalogo CISA KEV abiertas | **%d** |" % len(kev),
          "| ...usadas en ransomware | **%d** |" % len(ransom),
          "| ...con fecha limite de CISA vencida | %d |" % len(vencidos),
          "| Otras vulnerabilidades conocidas (no KEV) | %d |" % (len(h) - len(kev)),
          "| Dependen de configuracion (verificar) | %d |" % len(cond),
          "| Componentes fuera de soporte del fabricante | %d |" % len(res["eol"]),
          "| Configuraciones inseguras (protocolos, web.config...) | %d |" % len(res.get("configuracion", [])), ""]
    if kev:
        L += ["**Cumplimiento: NO CUMPLE.** Hay %d vulnerabilidades del catalogo KEV sin parchear. "
              "CISA exige remediarlas antes de su fecha limite." % len(kev), ""]
    else:
        L += ["**Cumplimiento:** no se detectaron vulnerabilidades del catalogo KEV en los componentes con version conocida. "
              "Revisar la seccion de componentes sin version.", ""]

    L += ["## 1. Que parchear primero (catalogo CISA KEV)", ""]
    if kev:
        L += ["| # | Prioridad | CVE | Componente | Por que | Accion requerida (CISA) | Fecha limite | Evidencia |",
              "|---|---|---|---|---|---|---|---|"]
        for n, x in enumerate(kev, 1):
            L.append("| %d | **%s** | %s | %s %s | %s. %s | %s | %s%s | %s |" % (
                n, x["nivel_txt"], x["cve"], x["producto"], x["version"], x["motivo"], _celda(x.get("nombre")),
                _celda(x.get("accion")), x.get("fecha_limite", ""), " (vencida)" if x.get("vencido") else "",
                _celda(_donde(x))))
    else:
        L.append("Ninguna.")
    L.append("")

    L += ["## 2. Dependen de configuracion (verificar antes de descartar)", ""]
    if cond:
        L += ["| CVE | Componente | En KEV | Que verificar |", "|---|---|---|---|"]
        L += ["| %s | %s %s | %s | %s |" % (x["cve"], x["producto"], x["version"], "si" if x["en_kev"] else "no",
                                           _celda(x["condicion"])) for x in cond]
    else:
        L.append("Ninguna.")
    L.append("")

    L += ["## 3. Fuera de soporte (no recibiran mas parches: planificar migracion)", ""]
    if res["eol"]:
        L += ["| Componente | Version | Rama sin soporte desde | Evidencia |", "|---|---|---|---|"]
        L += ["| %s | %s | %s (rama %s) | %s |" % (c["producto"], c["version"], c["fin_soporte"], c["rama"],
                                               _celda(_donde(c))) for c in res["eol"]]
    else:
        L.append("Ninguno detectado.")
    L.append("")

    L += ["## 4. Configuracion insegura (corregir sin necesidad de parche)", ""]
    if res.get("configuracion"):
        L += ["| Tipo | Hallazgo | Recomendacion | Evidencia |", "|---|---|---|---|"]
        L += ["| %s | %s | %s | %s |" % (c["tipo"], _celda(c["detalle"]), _celda(c["recomendacion"] or "Revisar"),
                                       _celda(_donde(c))) for c in res["configuracion"]]
    else:
        L.append("Ninguna detectada.")
    L.append("")

    otras = [x for x in h if not x["en_kev"]]
    tope = reglas.get("max_no_kev_en_reporte", 20)
    L += ["## 5. Otras vulnerabilidades conocidas (no estan en KEV)", ""]
    if otras:
        L += ["| Prioridad | CVE | Componente | CVSS | Descripcion |", "|---|---|---|---|---|"]
        L += ["| %s | %s | %s %s | %s | %s |" % (x["nivel_txt"], x["cve"], x["producto"], x["version"],
                                              x["cvss"] if x["cvss"] is not None else "?", _celda(_corto(x["descripcion"])))
              for x in otras[:tope]]
        if len(otras) > tope:
            L.append("\n%d mas en `hallazgos-*.json`." % (len(otras) - tope))
    elif info.get("solo_kev"):
        L.append("No evaluado: el catalogo NVD usado (`catalogos/nvd-kev.json`) solo trae CVE que estan en KEV. "
                 "Para ver tambien las demas: `python -m revital.cves --actualizar`.")
    else:
        L.append("Ninguna.")
    L.append("")

    L += ["## 6. Revision manual", ""]
    if res["posibles"]:
        L += ["Version incompleta (solo la rama); podrian estar afectados por:", ""]
        L += ["- %s %s: %s (KEV)" % (x["producto"], x["version"], x["cve"]) for x in res["posibles"]]
        L.append("")
    if res["sin_version"]:
        L += ["Sin version detectada (no se puede confirmar ni descartar):", ""]
        L += ["- %s (%s)%s" % (c["producto"], _donde(c), "; el producto tiene %d CVE en KEV" % len(c["kev_del_producto"])
                                 if c["kev_del_producto"] else "") for c in res["sin_version"]]
        L.append("")
    if res["sin_mapeo"]:
        L += ["Sin equivalencia en NVD (agregar a `revital/cves/alias.json` si aplica):", ""]
        L += ["- %s %s (%s)" % (c["producto"], c["version"], _donde(c)) for c in res["sin_mapeo"]]
        L.append("")
    if res.get("notas_colectores"):
        L += ["Avisos de los colectores (cobertura incompleta):", ""]
        L += ["- %s (%s)" % (c["detalle"], _donde(c)) for c in res["notas_colectores"]]
        L.append("")
    if not (res["posibles"] or res["sin_version"] or res["sin_mapeo"] or res.get("notas_colectores")):
        L += ["Nada pendiente.", ""]

    L += ["## 7. Inventario", "", "| Componente | Version | Detectado como | Fuente | Donde |", "|---|---|---|---|---|"]
    for c in res["componentes"]:
        for e in c["evidencia"]:
            L.append("| %s | %s | %s | %s (%s) | %s |" % (c["producto"], c["version"] or "?", c["detectado_como"],
                                                         _celda(e["fuente"]), e["kind"], _celda(e["donde"])))
    L += ["", "## Metodo", "",
          "1. Los colectores detectan producto y version, con su fuente y lugar como evidencia.",
          "2. Cada producto se traduce al nombre oficial de NVD (CPE) con `alias.json`.",
          "3. Se buscan los CVE cuyo rango de versiones afectadas (NVD) incluye la version detectada.",
          "4. Se marca cuales estan en el catalogo CISA KEV (explotacion activa confirmada).",
          "5. Prioridad: KEV + ransomware > KEV con fecha vencida > KEV > CVSS >= %.1f > CVSS >= %.1f > resto." % (
              reglas["umbral_alto"], reglas["umbral_medio"]),
          "", "ReVital solo lee: no modifica el sistema analizado. Usar solo con autorizacion.", ""]
    return "\n".join(L)


def guardar(entidad, inventarios, res, info, hoy, reglas, out="salida"):
    os.makedirs(out, exist_ok=True)
    nombre = inventory.slug(entidad) or "sin-entidad"
    md = os.path.join(out, "reporte-%s.md" % nombre)
    js = os.path.join(out, "hallazgos-%s.json" % nombre)
    with open(md, "w", encoding="utf-8") as f:
        f.write(markdown(entidad, inventarios, res, info, hoy, reglas))
    with open(js, "w", encoding="utf-8") as f:
        json.dump(dict(res, entidad=entidad, fecha_evaluacion=hoy, catalogos=info), f, indent=2, ensure_ascii=False)
    return md, js
