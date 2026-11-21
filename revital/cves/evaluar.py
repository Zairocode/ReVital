"""Cruce: componentes de los inventarios -> CVE que afectan su version -> en KEV? -> nivel de prioridad."""
import json, os

from revital.cves import normalizar, versiones

AQUI = os.path.dirname(os.path.abspath(__file__))

NIVELES = {1: "CRITICO", 2: "URGENTE (vencido)", 3: "URGENTE", 4: "ALTO", 5: "MEDIO", 6: "BAJO"}
MOTIVOS = {1: "En CISA KEV y usado en campanas de ransomware",
           2: "En CISA KEV y ya paso la fecha limite de CISA",
           3: "En CISA KEV: se explota activamente",
           4: "No esta en KEV, pero CVSS critico",
           5: "No esta en KEV, CVSS alto",
           6: "No esta en KEV, CVSS medio o bajo"}


def cargar_reglas(path=None):
    with open(path or os.path.join(AQUI, "reglas.json"), encoding="utf-8") as f:
        return json.load(f)


def componentes(inventarios, alias):
    """Une los componentes de varios inventarios (misma entidad) quitando duplicados.
    Mismo producto+version visto por varias fuentes -> una fila con todas las evidencias.
    'Drupal 7' (meta generator) se descarta si tambien se vio 'Drupal 7.57'; 'PHP' sin version, si se vio con version."""
    grupos = {}
    for inv in inventarios:
        for c in inv.get("components", []):
            oficial, cpes = normalizar.identificar(c["producto"], alias)
            nombre = oficial or c["producto"].strip()
            ver = (c.get("version") or "").strip()
            g = grupos.setdefault((normalizar.clave(nombre), ver), {
                "producto": nombre, "detectado_como": c["producto"], "version": ver, "cpe": cpes,
                "evidencia": []})
            ev = {"kind": inv.get("kind", ""), "target": inv.get("target", ""),
                  "fuente": c.get("fuente", ""), "donde": c.get("donde", "")}
            if ev not in g["evidencia"]:
                g["evidencia"].append(ev)
    out = []
    for (k, ver), g in grupos.items():
        otras = [v for (k2, v) in grupos if k2 == k and v != ver]
        mejor = [v for v in otras if v.startswith(ver + ".")] if ver and versiones.es_rama(ver) else otras if not ver else []
        if mejor:  # 'PHP' sin version o 'Drupal 7' cuando ya sabemos 7.0.28 / 7.57: su evidencia pasa a esa fila
            destino = grupos[(k, sorted(mejor, key=versiones.partes)[-1])]
            destino["evidencia"] += [e for e in g["evidencia"] if e not in destino["evidencia"]]
            continue
        out.append(g)
    return sorted(out, key=lambda g: (g["producto"].lower(), versiones.partes(g["version"])))


def nivel(en_kev, k, cvss, hoy, reglas):
    if en_kev:
        if k.get("knownRansomwareCampaignUse", "").lower() == "known":
            return 1
        if k.get("dueDate", "9999") < hoy:
            return 2
        return 3
    cvss = cvss or 0
    return 4 if cvss >= reglas["umbral_alto"] else 5 if cvss >= reglas["umbral_medio"] else 6


def evaluar(inventarios, catalogo, alias, reglas, hoy):
    """-> dict con componentes, hallazgos (confirmados), condicionales, posibles, eol y pendientes."""
    kev, nvd, idx = catalogo["kev"], catalogo["nvd"], catalogo["indice"]
    res = {"componentes": componentes(inventarios, alias), "hallazgos": [], "condicionales": [],
           "posibles": [], "eol": [], "configuracion": configuracion(inventarios, reglas), "notas_colectores": [],
           "sin_version": [], "sin_mapeo": []}
    res["notas_colectores"] = [c for c in res["configuracion"] if c["tipo"] == "nota"]
    res["configuracion"] = [c for c in res["configuracion"] if c["tipo"] != "nota"]
    protocolos = reglas.get("protocolos_obsoletos", {})
    for comp in res["componentes"]:
        ver = comp["version"]
        proto = protocolos.get(normalizar.clave(comp["producto"]), {})
        if proto:  # 'TLS 1.0' no es software con CVE: es un protocolo inseguro que el servidor acepta
            if ver in proto:
                res["configuracion"].append({"tipo": "Protocolo obsoleto",
                                             "detalle": "El servidor acepta %s %s" % (comp["producto"], ver),
                                             "recomendacion": proto[ver], "evidencia": comp["evidencia"]})
            continue
        if not comp["cpe"]:
            res["sin_mapeo"].append(comp)
            continue
        fin = normalizar.eol(comp["producto"], ver, alias, hoy)
        if fin:
            res["eol"].append(dict(comp, rama=fin[0], fin_soporte=fin[1]))
        if not ver or not versiones.valida(ver):
            res["sin_version"].append(dict(comp, kev_del_producto=sorted(
                {c for cpe in comp["cpe"] for c, _ in idx.get(cpe, []) if c in kev})))
            continue
        rama = versiones.es_rama(ver)
        vistos = set()
        for cpe in comp["cpe"]:
            for cve, rango in idx.get(cpe, []):
                if cve in vistos:
                    continue
                aplica = versiones.rama_toca_rango(ver, rango) if rama else versiones.en_rango(ver, rango)
                if not aplica:
                    continue
                vistos.add(cve)
                k, n = kev.get(cve), nvd.get(cve, {})
                h = {"cve": cve, "producto": comp["producto"], "version": ver, "evidencia": comp["evidencia"],
                     "en_kev": bool(k), "cvss": n.get("cvss"), "severidad": n.get("severidad", ""),
                     "descripcion": n.get("descripcion", ""), "confianza": "posible" if rama else "confirmado"}
                if k:
                    h.update(nombre=k.get("vulnerabilityName", ""), ransomware=k.get("knownRansomwareCampaignUse", ""),
                             agregado_kev=k.get("dateAdded", ""), fecha_limite=k.get("dueDate", ""),
                             vencido=k.get("dueDate", "9999") < hoy, accion=k.get("requiredAction", ""))
                h["nivel"] = nivel(bool(k), k or {}, h["cvss"], hoy, reglas)
                h["nivel_txt"], h["motivo"] = NIVELES[h["nivel"]], MOTIVOS[h["nivel"]]
                if cve in reglas["condicionales"]:
                    h["condicion"] = reglas["condicionales"][cve]
                    res["condicionales"].append(h)
                elif rama:
                    if h["en_kev"]:  # con solo la rama, listar todo seria ruido: solo lo explotado
                        res["posibles"].append(h)
                else:
                    res["hallazgos"].append(h)
    orden = lambda h: (h["nivel"], -(h["cvss"] or 0), h["cve"])
    for k in ("hallazgos", "condicionales", "posibles"):
        res[k].sort(key=orden)
    return res


def configuracion(inventarios, reglas):
    """Alertas de configuracion que los colectores dejan en extra.alertas (ej. web.config con debug=true)."""
    out, recs, notas = [], reglas.get("alertas", {}), reglas.get("notas_colector", [])
    for inv in inventarios:
        for a in (inv.get("extra") or {}).get("alertas", []) or []:
            low = a.lower()
            ev = [{"kind": inv.get("kind", ""), "target": inv.get("target", ""),
                   "fuente": "colector " + inv.get("kind", ""), "donde": inv.get("target", "")}]
            tipo = "nota" if any(n in low for n in notas) else "Configuracion insegura"
            rec = next((r for k, r in recs.items() if k in low.replace(" ", "").replace('"', "")
                        or k in low), "")
            item = {"tipo": tipo, "detalle": a, "recomendacion": rec, "evidencia": ev}
            if item not in out:
                out.append(item)
    return out


def por_entidad(inventarios, entidad=None):
    """Agrupa inventarios por su campo 'entidad' (cada entidad tiene su reporte)."""
    grupos = {}
    for inv in inventarios:
        e = (inv.get("entidad") or "").strip() or "sin-entidad"
        if entidad and normalizar.clave(e) != normalizar.clave(entidad):
            continue
        grupos.setdefault(e, []).append(inv)
    return grupos
