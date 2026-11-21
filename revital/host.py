"""Colector de equipo (host) de ReVital: documenta ESTE equipo Windows (aunque sea viejo) -> inventario-host-<equipo>.json.

Lee del registro de Windows y de comandos del sistema (solo lectura, no instala ni cambia nada):
sistema operativo, IIS, .NET Framework, programas instalados con su version, parches (hotfixes), puertos en escucha y
configuraciones inseguras tipicas de equipos viejos (SMBv1, escritorio remoto, UAC, sistema sin soporte, sin parches).
Solo stdlib (winreg incluido en Python para Windows); Python 3.8+ en Windows 7 o posterior.

Uso:  python -m revital.host [--entidad X] [--out salida]      (o scripts\\revital-host.bat)
      python -m revital.host --demo                            (autoprueba con datos de ejemplo, en cualquier SO)
Solo en equipos propios o con autorizacion. Linux viejo: fuera de alcance por ahora.
"""
import argparse, os, platform, re, subprocess, sys, time

from revital import inventory

ES_WINDOWS = sys.platform.startswith("win")
UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
# version interna de Windows -> (nombre, fin de soporte de Microsoft)
SIN_SOPORTE = {"5.0": ("Windows 2000", "2010-07-13"), "5.1": ("Windows XP", "2014-04-08"),
               "5.2": ("Windows Server 2003 / XP x64", "2015-07-14"), "6.0": ("Windows Vista / Server 2008", "2017-04-11 (Vista) / 2020-01-14 (Server 2008)"),
               "6.1": ("Windows 7 / Server 2008 R2", "2020-01-14"), "6.2": ("Windows 8 / Server 2012", "2016-01-12 (8) / 2023-10-10 (Server 2012)"),
               "6.3": ("Windows 8.1 / Server 2012 R2", "2023-01-10 (8.1) / 2023-10-10 (Server 2012 R2)")}
PUERTOS_INSEGUROS = {21: "FTP (sin cifrar)", 23: "Telnet (sin cifrar)", 69: "TFTP", 512: "rexec", 513: "rlogin", 514: "rsh"}
# nombre que muestra Windows -> nombre canonico que entiende revital.cves (alias.json). El resto de programas queda como esta.
NORMALIZAR = [(r"^Adobe Flash Player", "Adobe Flash Player"), (r"^Adobe (Acrobat )?Reader", "Adobe Acrobat Reader"),
              (r"^Adobe Acrobat\b", "Adobe Acrobat"), (r"^WinRAR", "WinRAR"), (r"^7-Zip", "7-Zip"),
              (r"^Mozilla Firefox", "Mozilla Firefox"), (r"^Google Chrome", "Google Chrome")]
RUIDO = re.compile(r"^(Update for|Security Update|Hotfix|Service Pack)|\bKB\d{6,}\b|^Microsoft Visual C\+\+ \d{4} (Redistributable|x)", re.I)


# ------------------------------------------------------------------ lectura (solo Windows)
def _winreg():
    import winreg
    return winreg


def _valores(hive, ruta, vista=0):
    w = _winreg()
    out = {}
    try:
        k = w.OpenKey(hive, ruta, 0, w.KEY_READ | vista)
    except OSError:
        return out
    try:
        i = 0
        while True:
            try:
                n, v, _ = w.EnumValue(k, i)
            except OSError:
                break
            out[n] = v
            i += 1
    finally:
        w.CloseKey(k)
    return out


def _subclaves(hive, ruta, vista=0):
    w = _winreg()
    try:
        k = w.OpenKey(hive, ruta, 0, w.KEY_READ | vista)
    except OSError:
        return []
    out = []
    try:
        i = 0
        while True:
            try:
                out.append(w.EnumKey(k, i))
            except OSError:
                break
            i += 1
    finally:
        w.CloseKey(k)
    return out


def _cmd(args, timeout=90):
    """Salida del comando, o None si no existe / falla (distinto de 'corrio y no devolvio nada')."""
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True, errors="replace", timeout=timeout)
        return (p.stdout or "") if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def leer_equipo():
    """Datos crudos de este equipo (Windows). La interpretacion esta en a_inventario(), que se puede probar en cualquier SO."""
    w = _winreg()
    lm, cu = w.HKEY_LOCAL_MACHINE, w.HKEY_CURRENT_USER
    v64, v32 = w.KEY_WOW64_64KEY, w.KEY_WOW64_32KEY
    cur = _valores(lm, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", v64)
    iis = _valores(lm, r"SOFTWARE\Microsoft\InetStp", v64)
    dotnet = []
    ndp = r"SOFTWARE\Microsoft\NET Framework Setup\NDP"
    for sub in _subclaves(lm, ndp, v64):
        for ruta in (ndp + "\\" + sub, ndp + "\\" + sub + r"\Full"):
            d = _valores(lm, ruta, v64)
            if d.get("Version") and d.get("Install", 1) == 1:
                dotnet.append(str(d["Version"]))
    progs = []
    for hive, vista in ((lm, v64), (lm, v32), (cu, 0)):
        for sub in _subclaves(hive, UNINSTALL, vista):
            d = _valores(hive, UNINSTALL + "\\" + sub, vista)
            if d.get("DisplayName") and not d.get("SystemComponent") and not d.get("ParentKeyName"):
                progs.append({"nombre": str(d["DisplayName"]).strip(), "version": str(d.get("DisplayVersion", "")).strip(),
                              "editor": str(d.get("Publisher", "")).strip()})
    ie = _valores(lm, r"SOFTWARE\Microsoft\Internet Explorer", v64)
    smb = _valores(lm, r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", v64).get("SMB1")
    seg = {"smb1": smb,
           "rdp_bloqueado": _valores(lm, r"SYSTEM\CurrentControlSet\Control\Terminal Server", v64).get("fDenyTSConnections"),
           "uac": _valores(lm, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", v64).get("EnableLUA")}
    return {"equipo": platform.node(), "os": cur, "iis": iis, "ie": {"version": str(ie.get("svcVersion") or ie.get("Version") or "")}, "dotnet": dotnet, "programas": progs, "seguridad": seg,
            "hotfixes": _hotfixes(), "puertos": _puertos()}


def _hotfixes():
    """Parches instalados: lista (puede estar vacia) o None si no se pudo consultar.
    wmic existe en Windows viejo pero Microsoft lo quito de Windows 11: se usa PowerShell como respaldo."""
    txt = _cmd(["wmic", "qfe", "get", "HotFixID,InstalledOn", "/format:csv"])
    if txt is not None:
        out = []
        for linea in txt.splitlines():
            p = [x.strip() for x in linea.split(",")]
            if len(p) >= 3 and re.match(r"^KB\d+$", p[-2], re.I):
                out.append({"id": p[-2].upper(), "fecha": p[-1]})
        if out:
            return out
    ps = ("Get-HotFix | ForEach-Object { $_.HotFixID + ',' + $(if ($_.InstalledOn) { $_.InstalledOn.ToString('yyyy-MM-dd') } else { '' }) }")
    txt2 = _cmd(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps])
    if txt2 is None:
        return [] if txt is not None else None
    return [{"id": a.upper(), "fecha": b} for a, _, b in (l.strip().partition(",") for l in txt2.splitlines()) if re.match(r"^KB\d+$", a, re.I)]


def _fecha(s):
    """'2024-05-14' o '5/14/2024' -> time.struct_time (o None)."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return time.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _puertos():
    """Puertos TCP en escucha (netstat). La palabra del estado depende del idioma: se reconoce por el destino ':0'."""
    out, vistos = [], set()
    for linea in (_cmd(["netstat", "-ano", "-p", "tcp"]) or "").splitlines():
        p = linea.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[2].endswith(":0"):
            local = p[1]
            puerto = int(local.rsplit(":", 1)[1])
            if (local, puerto) not in vistos:
                vistos.add((local, puerto))
                out.append({"direccion": local.rsplit(":", 1)[0], "puerto": puerto, "pid": p[-1]})
    return sorted(out, key=lambda x: x["puerto"])


# ------------------------------------------------------------------ interpretacion (pura, testeable)
def nombre_os(cur):
    """'Windows 7 Professional' -> 'Windows 7'; 'Windows Server 2008 R2 Standard' -> 'Windows Server 2008 R2'."""
    n = re.sub(r"^Microsoft\s+", "", str(cur.get("ProductName", "")).strip())
    m = re.match(r"^(Windows Server (?:20\d\d(?: R2)?)|Windows (?:XP|Vista|7|8\.1|8|10|11))", n)
    base = m.group(1) if m else (n or "Windows")
    if base == "Windows 10" and int(str(cur.get("CurrentBuild") or cur.get("CurrentBuildNumber") or 0) or 0) >= 22000:
        base = "Windows 11"  # el registro de Windows 11 todavia dice "Windows 10"
    return base


def a_inventario(raw, entidad="", ahora=None):
    """Datos crudos -> inventario en el contrato comun (+ alertas de configuracion en extra.alertas)."""
    ahora = ahora or time.strftime("%Y-%m-%d")
    cur = raw.get("os", {})
    inv = inventory.nuevo("host", raw.get("equipo") or "equipo", entidad)
    comps = []

    def add(prod, ver, fuente, donde):
        comps.append(inventory.componente(prod, ver, fuente, donde))

    build = str(cur.get("CurrentBuild") or cur.get("CurrentBuildNumber") or "")
    # Windows 10/11 siguen escribiendo CurrentVersion=6.3 por compatibilidad: la version real esta en CurrentMajorVersionNumber
    mayor = cur.get("CurrentMajorVersionNumber")
    interno = ("%s.%s" % (mayor, cur.get("CurrentMinorVersionNumber", 0))) if mayor else str(cur.get("CurrentVersion", ""))
    nombre = nombre_os(cur)
    add(nombre, ("%s.%s" % (interno, build)).strip(".") if interno else build, "registro: CurrentVersion", "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion")
    iis = raw.get("iis") or {}
    if iis.get("MajorVersion") is not None:
        add("Microsoft IIS", "%s.%s" % (iis.get("MajorVersion"), iis.get("MinorVersion", 0)), "registro: InetStp", "HKLM\\SOFTWARE\\Microsoft\\InetStp")
    for v in sorted(set(raw.get("dotnet") or [])):
        add(".NET Framework", v, "registro: NET Framework Setup\\NDP", "HKLM\\SOFTWARE\\Microsoft\\NET Framework Setup\\NDP")
    ie = str((raw.get("ie") or {}).get("version", "")).split(".")[0]
    if ie.isdigit() and nombre != "Windows 11":  # en Windows 11 Internet Explorer es solo un resto del sistema: seria ruido
        add("Internet Explorer", ie, "registro: Internet Explorer", "HKLM\\SOFTWARE\\Microsoft\\Internet Explorer")
    vistos = set()
    for p in raw.get("programas") or []:
        p = dict(p, nombre=next((c for rx, c in NORMALIZAR if re.search(rx, p["nombre"], re.I)), p["nombre"]))
        if RUIDO.search(p["nombre"]) or (p["nombre"], p["version"]) in vistos:
            continue
        vistos.add((p["nombre"], p["version"]))
        add(p["nombre"], p["version"], "registro: programas instalados" + (" (%s)" % p["editor"] if p.get("editor") else ""), "Programas y caracteristicas")

    alertas = []
    fin = SIN_SOPORTE.get(interno)
    if fin:
        alertas.append("%s: sin soporte de Microsoft desde %s (ya no recibe parches de seguridad)" % (fin[0], fin[1]))
    if nombre == "Windows 10":
        alertas.append("Windows 10: sin soporte de Microsoft desde 2025-10-14 (ya no recibe parches de seguridad, salvo suscripcion ESU)")
    seg = raw.get("seguridad") or {}
    viejo = interno in ("5.0", "5.1", "5.2", "6.0", "6.1", "6.2", "6.3")
    if seg.get("smb1") == 1 or (seg.get("smb1") is None and viejo):
        alertas.append("SMBv1 habilitado (protocolo vulnerable a EternalBlue/WannaCry): desactivarlo si ningun equipo antiguo lo necesita")
    if seg.get("rdp_bloqueado") == 0:
        alertas.append("Escritorio remoto (RDP) habilitado: restringirlo con firewall/VPN y exigir autenticacion a nivel de red")
    if seg.get("uac") == 0:
        alertas.append("Control de cuentas de usuario (UAC) desactivado")
    for pt in raw.get("puertos") or []:
        if pt["puerto"] in PUERTOS_INSEGUROS and pt.get("direccion") not in ("127.0.0.1", "[::1]"):
            alertas.append("Servicio inseguro escuchando: %s (puerto %d)" % (PUERTOS_INSEGUROS[pt["puerto"]], pt["puerto"]))
    hf = raw.get("hotfixes")  # None = no se pudo consultar: no se acusa de nada que no se sepa
    if hf is not None and not hf and viejo:
        alertas.append("Sin parches de seguridad registrados (no hay hotfixes instalados): el equipo no recibe actualizaciones")
    fechas = [f for f in (_fecha(h.get("fecha", "")) for h in hf or []) if f]
    if fechas:
        ult = max(fechas)
        dias = int((time.mktime(_fecha(ahora)) - time.mktime(ult)) / 86400)
        if dias > 180:
            alertas.append("Sin parches de seguridad recientes: el ultimo se instalo el %s (hace %d dias)" % (time.strftime("%Y-%m-%d", ult), dias))
    inv["components"] = comps
    inv["extra"] = {"sistema": {"nombre": cur.get("ProductName", ""), "version_interna": interno, "build": build,
                                "service_pack": cur.get("CSDVersion", ""), "edicion": cur.get("EditionID", ""),
                                "arquitectura": platform.machine()},
                    "hotfixes": hf or [], "hotfixes_total": None if hf is None else len(hf), "puertos_escucha": raw.get("puertos") or [],
                    "programas_total": len(raw.get("programas") or []), "alertas": alertas, "fecha_lectura": ahora}
    return inv


def to_markdown(inv):
    x = inv["extra"]
    s = x["sistema"]
    out = ["# Reporte ReVital (equipo): %s" % inv["target"], "", "Entidad: %s" % (inv["entidad"] or "-"), "Generado: %s" % inv["generado"], "",
           "## Sistema", "", "- %s (version interna %s, build %s) %s" % (s.get("nombre", "?"), s.get("version_interna", "?"), s.get("build", "?"), s.get("service_pack", "")),
           "- Parches (hotfixes) instalados: %s" % ("no se pudo consultar" if x["hotfixes_total"] is None else x["hotfixes_total"]), "- Programas instalados: %d" % x["programas_total"]]
    if x["alertas"]:
        out += ["", "## Alertas de configuracion", ""] + ["- " + a for a in x["alertas"]]
    out += ["", "## Componentes", "", "| Producto | Version | Fuente |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % (c["producto"].replace("|", "/"), c["version"], c["fuente"].replace("|", "/")) for c in inv["components"]]
    if x["puertos_escucha"]:
        out += ["", "## Puertos TCP en escucha", ""] + ["- %s:%d (PID %s)" % (p["direccion"], p["puerto"], p["pid"]) for p in x["puertos_escucha"]]
    return "\n".join(out) + "\n"


def demo():
    """Un Windows 7 SP1 tipico de oficina publica, sin leer nada del equipo: prueba la interpretacion en cualquier SO."""
    raw = {"equipo": "PC-CONTA-01", "os": {"ProductName": "Windows 7 Professional", "CurrentVersion": "6.1", "CurrentBuild": "7601", "CSDVersion": "Service Pack 1", "EditionID": "Professional"},
           "iis": {"MajorVersion": 7, "MinorVersion": 5}, "ie": {"version": "8.0.7601.17514"}, "dotnet": ["3.5.30729.5420", "4.0.30319", "3.5.30729.5420"],
           "programas": [{"nombre": "Java 7 Update 45", "version": "7.0.450", "editor": "Oracle Corporation"},
                         {"nombre": "Security Update for Microsoft .NET Framework 3.5 (KB2604115)", "version": "1", "editor": ""},
                         {"nombre": "Adobe Reader 9.5.0", "version": "9.5.0", "editor": "Adobe Systems"},
                         {"nombre": "Adobe Reader 9.5.0 - Espa\u00f1ol", "version": "9.5.0", "editor": "Adobe Systems"},
                         {"nombre": "WinRAR 5.00 (64-bit)", "version": "5.00.0", "editor": "win.rar GmbH"}],
           "seguridad": {"smb1": None, "rdp_bloqueado": 0, "uac": 1}, "hotfixes": [],
           "puertos": [{"direccion": "0.0.0.0", "puerto": 23, "pid": "4"}, {"direccion": "127.0.0.1", "puerto": 21, "pid": "9"}, {"direccion": "0.0.0.0", "puerto": 445, "pid": "4"}]}
    inv = a_inventario(raw, "MUNI-GT", "2026-11-21")
    prods = {(c["producto"], c["version"]) for c in inv["components"]}
    assert ("Windows 7", "6.1.7601") in prods and ("Microsoft IIS", "7.5") in prods, prods
    assert (".NET Framework", "3.5.30729.5420") in prods and sum(1 for c in inv["components"] if c["producto"] == ".NET Framework") == 2
    assert ("Java 7 Update 45", "7.0.450") in prods and sum(1 for c in inv["components"] if c["producto"] == "Adobe Acrobat Reader") == 1, "los nombres de un mismo programa se unen"
    assert ("WinRAR", "5.00.0") in prods and ("Internet Explorer", "8") in prods, prods
    assert not any("KB2604115" in c["producto"] for c in inv["components"]), "los parches no son programas"
    a = " | ".join(inv["extra"]["alertas"])
    for clave in ("sin soporte de Microsoft desde 2020-01-14", "SMBv1", "Escritorio remoto", "Telnet (sin cifrar) (puerto 23)", "Sin parches de seguridad"):
        assert clave in a, (clave, a)
    assert "FTP" not in a, "un puerto solo local no es una exposicion"
    assert nombre_os({"ProductName": "Windows 10 Pro", "CurrentBuild": "22621"}) == "Windows 11"
    # Windows 11 de verdad (CurrentVersion=6.3 por compatibilidad): sin falsas alarmas de "sin soporte", SMBv1 ni "sin parches"
    w11 = a_inventario({"equipo": "PC", "os": {"ProductName": "Windows 10 Pro", "CurrentVersion": "6.3", "CurrentMajorVersionNumber": 10, "CurrentMinorVersionNumber": 0, "CurrentBuild": "26200"},
                        "hotfixes": None, "seguridad": {"smb1": None, "rdp_bloqueado": 1, "uac": 1}, "puertos": []}, "X", "2026-11-21")
    assert w11["extra"]["alertas"] == [] and w11["components"][0]["version"] == "10.0.26200" and w11["extra"]["hotfixes_total"] is None, w11["extra"]
    assert "no se pudo consultar" in to_markdown(w11)
    # parches viejos: avisa con la fecha del ultimo
    viejo = a_inventario({"equipo": "PC", "os": {"ProductName": "Windows 7", "CurrentVersion": "6.1", "CurrentBuild": "7601"},
                          "hotfixes": [{"id": "KB1", "fecha": "2019-03-01"}, {"id": "KB2", "fecha": "11/12/2019"}], "seguridad": {"smb1": 0}}, "X", "2026-11-21")
    assert any("ultimo se instalo el 2019-11-12" in a for a in viejo["extra"]["alertas"]), viejo["extra"]["alertas"]
    assert not any("SMBv1" in a for a in viejo["extra"]["alertas"]), "SMB1=0 significa desactivado"
    assert _fecha("5/14/2024") and _fecha("2024-05-14") and _fecha("basura") is None
    assert nombre_os({"ProductName": "Windows Server 2008 R2 Standard"}) == "Windows Server 2008 R2"
    assert "## Alertas de configuracion" in to_markdown(inv)
    print("ok")


def main():
    ap = argparse.ArgumentParser(description="Colector de equipo Windows de ReVital")
    ap.add_argument("--entidad", default="")
    ap.add_argument("--out", default="salida")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not ES_WINDOWS:
        sys.exit("host.py lee el registro de Windows: ejecutalo en el equipo Windows a documentar (Linux viejo esta fuera de alcance). Prueba la logica con --demo.")
    inv = a_inventario(leer_equipo(), a.entidad)
    j = inventory.guardar(inv, a.out)
    md = os.path.join(a.out, "reporte-%s-host-%s.md" % (a.entidad or "sin-entidad", inventory.slug(inv["target"])))
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(inv))
    print("listo: %s y %s (%d componentes, %d alertas)" % (j, md, len(inv["components"]), len(inv["extra"]["alertas"])))


if __name__ == "__main__":
    main()
