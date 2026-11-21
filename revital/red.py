"""Colector de red de ReVital (PoC): descubre que servicios tiene una red de la institucion y que programa y version es cada uno.

Para cada IP del rango prueba una lista corta de puertos con una conexion TCP normal y lee el "banner" que el servicio
anuncia (SSH, FTP, SMTP, MySQL, HTTP Server...). No envia exploits, no prueba contrasenas, no escanea SYN ni usa
privilegios: solo conecta y lee. Solo stdlib (Python 3.8+). Produce inventario-red-<rango>.json (contrato comun).

  python -m revital.red 192.168.1.0/24 --entidad MUNI-GT --autorizo
  python -m revital.red 127.0.0.1 --puertos 21,22,80,3306 --autorizo

Reglas de seguridad: exige --autorizo; por defecto solo redes privadas/locales (--permitir-publico para otras);
maximo 256 equipos (--max-hosts); conexiones con tiempo corto y pocas en paralelo para no saturar equipos viejos.
Solo en redes propias o con autorizacion por escrito.
"""
import argparse, ipaddress, os, re, socket, ssl, sys, time
from concurrent.futures import ThreadPoolExecutor

from revital import inventory
from revital.crawler import TLS_OBSOLETAS, sondear_tls, tokens_ver

PUERTOS = (21, 22, 23, 25, 80, 110, 135, 139, 143, 443, 445, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 9200, 11211, 27017)
SERVICIOS = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 80: "HTTP", 110: "POP3", 135: "MSRPC", 139: "NetBIOS", 143: "IMAP", 443: "HTTPS",
             445: "SMB", 1433: "SQL Server", 1521: "Oracle", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
             8080: "HTTP", 8443: "HTTPS", 9200: "Elasticsearch", 11211: "Memcached", 27017: "MongoDB"}
TLS_PUERTOS = (443, 8443, 9443)
# servicios que no deberian estar abiertos a toda una red: se avisa (el texto reutiliza las recomendaciones de revital.cves)
SENSIBLES = {"Telnet": "Telnet (sin cifrar)", "FTP": "FTP (sin cifrar)", "MySQL": "base de datos MySQL", "SQL Server": "base de datos SQL Server",
             "Oracle": "base de datos Oracle", "PostgreSQL": "base de datos PostgreSQL", "MongoDB": "base de datos MongoDB", "Redis": "Redis (sin clave por defecto)",
             "Memcached": "Memcached", "Elasticsearch": "Elasticsearch", "VNC": "VNC (escritorio remoto sin cifrar)"}


# ------------------------------------------------------------------ objetivos
def resolver_objetivo(texto, max_hosts=256, permitir_publico=False):
    """'192.168.1.0/24, 10.0.0.5, servidor.local' -> lista de IPv4 (str). Lanza ValueError con un mensaje claro si no es seguro/valido."""
    ips = []
    for parte in [p.strip() for p in texto.split(",") if p.strip()]:
        try:
            red = ipaddress.ip_network(parte, strict=False)
        except ValueError:
            try:  # nombre de equipo: se resuelve y se trata como una sola IP
                red = ipaddress.ip_network(socket.gethostbyname(parte))
            except (OSError, ValueError):
                raise ValueError("No entiendo '%s': usa una IP, un rango como 192.168.1.0/24 o el nombre de un equipo." % parte)
        if red.version != 4:
            raise ValueError("Solo IPv4 por ahora: %s" % parte)
        if not permitir_publico and not (red.is_private or red.is_loopback or red.is_link_local):
            raise ValueError("%s no es una red privada. Escanear redes publicas requiere --permitir-publico y autorizacion escrita." % parte)
        if red.num_addresses > max_hosts + 2:
            raise ValueError("%s tiene %d direcciones; el maximo es %d (--max-hosts). Escanea por partes." % (parte, red.num_addresses, max_hosts))
        ips += [str(h) for h in (red.hosts() if red.prefixlen < 31 else red)]
    if not ips:
        raise ValueError("No hay equipos que escanear.")
    if len(ips) > max_hosts:
        raise ValueError("Son %d equipos; el maximo es %d (--max-hosts)." % (len(ips), max_hosts))
    return list(dict.fromkeys(ips))


# ------------------------------------------------------------------ lectura de banners
def _leer(s, tope=2048):
    datos = b""
    try:
        while len(datos) < tope:
            trozo = s.recv(1024)
            if not trozo:
                break
            datos += trozo
            s.settimeout(0.15)  # lo que ya llego esta; no se espera mucho mas
    except (socket.timeout, OSError):
        pass
    return datos


def sonda(ip, puerto, timeout=1.0, espera=0.6):
    """Conecta al puerto: None si esta cerrado; si no, lo que el servicio dijo (por si solo o ante un HEAD HTTP)."""
    try:
        s = socket.create_connection((ip, puerto), timeout=timeout)
    except OSError:
        return None
    tls = puerto in TLS_PUERTOS
    try:
        if tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
            try:
                ctx.set_ciphers("ALL:@SECLEVEL=0")
                ctx.minimum_version = ssl.TLSVersion.TLSv1
            except (ssl.SSLError, ValueError, AttributeError):
                pass
            s = ctx.wrap_socket(s, server_hostname=ip)
        s.settimeout(espera)
        datos = b"" if tls else _leer(s)  # los servicios que hablan primero (SSH, FTP, SMTP, MySQL) no necesitan que se les pregunte
        if not datos:
            try:
                s.sendall(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\nUser-Agent: ReVital-red/0.1\r\n\r\n")
                datos = _leer(s)
            except OSError:
                pass
        return {"puerto": puerto, "datos": datos, "tls": tls}
    except (ssl.SSLError, OSError):
        return {"puerto": puerto, "datos": b"", "tls": tls}
    finally:
        try:
            s.close()
        except OSError:
            pass


def identificar(puerto, datos):
    """(servicio, [(producto, version)]) a partir de lo que dijo el puerto. Se decide por el CONTENIDO; el numero de puerto es solo respaldo."""
    t = datos.decode("latin-1", "replace")
    prods = []
    if datos[:4] == b"SSH-":
        m = re.match(r"SSH-[\d.]+-([A-Za-z]+)[_-]([\d.]+)", t)
        if m:
            prods.append(("OpenSSH" if m.group(1).lower() == "openssh" else m.group(1), m.group(2).rstrip(".")))
        return "SSH", prods
    if datos[:1] == b"\xff":
        return "Telnet", prods
    if len(datos) > 6 and datos[4] == 0x0A and re.match(rb"\d+\.\d+", datos[5:]):  # saludo de MySQL/MariaDB
        v = datos[5:].split(b"\x00")[0].decode("latin-1", "replace")
        if "mariadb" in v.lower():
            m = re.search(r"(?:5\.5\.5-)?(\d+\.\d+\.\d+)", v)
            prods.append(("MariaDB", m.group(1) if m else ""))
        else:
            m = re.match(r"\d+\.\d+(?:\.\d+)?", v)
            prods.append(("MySQL", m.group(0) if m else ""))
        return "MySQL", prods
    if t.startswith("HTTP/"):
        cab = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in t.split("\r\n")[1:]) if v}
        for h in ("server", "x-powered-by"):
            if h in cab:
                prods += tokens_ver(cab[h])
        return "HTTPS" if puerto in TLS_PUERTOS else "HTTP", [(p, v) for p, v in prods if v]
    if t.startswith("220"):
        smtp = "smtp" in t.lower() or puerto in (25, 587)
        for rx, nombre in ((r"ProFTPD ([\d.]+[a-z]?)", "ProFTPD"), (r"\(vsFTPd ([\d.]+)\)", "vsFTPd"), (r"FileZilla Server (?:version )?([\d.]+)", "FileZilla Server"),
                           (r"Exim ([\d.]+)", "Exim"), (r"Sendmail ([\d./]+)", "Sendmail"), (r"Microsoft ESMTP MAIL Service, Version: ([\d.]+)", "Microsoft SMTP")):
            m = re.search(rx, t)
            if m:
                prods.append((nombre, m.group(1)))
        return ("SMTP" if smtp else "FTP"), prods
    if t.startswith("+OK"):
        return "POP3", prods
    if t.startswith("* OK"):
        return "IMAP", prods
    if t.startswith(("-ERR", "-DENIED", "-NOAUTH")):
        return "Redis", prods
    return SERVICIOS.get(puerto, "desconocido"), prods


def escanear(ips, puertos=PUERTOS, timeout=1.0, espera=0.6, hilos=16, pausa=0.0):
    """Prueba cada par (equipo, puerto) con pocas conexiones a la vez. -> lista de equipos con algun puerto abierto."""
    def uno(par):
        if pausa:
            time.sleep(pausa)
        return par, sonda(par[0], par[1], timeout, espera)
    abiertos = {}
    with ThreadPoolExecutor(max_workers=max(1, hilos)) as ex:
        for (ip, p), r in ex.map(uno, [(ip, p) for ip in ips for p in puertos]):
            if r is not None:
                serv, prods = identificar(p, r["datos"])
                linea = r["datos"].decode("latin-1", "replace").splitlines()[0].strip()[:120] if r["datos"].strip() else ""
                abiertos.setdefault(ip, []).append({"puerto": p, "servicio": serv, "tls": r["tls"], "banner": re.sub(r"[^\x20-\x7e]", ".", linea), "productos": prods})
    return [{"ip": ip, "puertos": sorted(ps, key=lambda x: x["puerto"])} for ip, ps in sorted(abiertos.items(), key=lambda kv: tuple(int(o) for o in kv[0].split(".")))]


# ------------------------------------------------------------------ inventario
def a_inventario(equipos, objetivo, entidad="", tls=None):
    """Equipos escaneados -> inventario en el contrato comun (+ alertas de servicios expuestos en extra.alertas)."""
    inv = inventory.nuevo("red", objetivo, entidad)
    comps, vistos, alertas = [], set(), []
    for h in equipos:
        for p in h["puertos"]:
            donde = "%s:%d" % (h["ip"], p["puerto"])
            for prod, ver in p["productos"]:
                k = (prod, ver, donde)
                if k not in vistos:
                    vistos.add(k)
                    comps.append(inventory.componente(prod, ver, "banner del servicio %s (puerto %d)" % (p["servicio"], p["puerto"]), donde))
            if p["servicio"] in SENSIBLES:
                alertas.append("Servicio inseguro expuesto: %s en %s (puerto %d) accesible desde la red" % (SENSIBLES[p["servicio"]], h["ip"], p["puerto"]))
            elif p["servicio"] == "RDP":
                alertas.append("Escritorio remoto (RDP) accesible desde la red en %s (puerto %d)" % (h["ip"], p["puerto"]))
            elif p["servicio"] == "SMB":
                alertas.append("Servicio inseguro expuesto: SMB/archivos compartidos en %s (puerto %d) accesible desde la red" % (h["ip"], p["puerto"]))
            for v in (tls or {}).get(donde, []):
                if v in TLS_OBSOLETAS:
                    comps.append(inventory.componente("TLS", v.replace("TLSv", ""), "protocolo obsoleto aceptado por el servidor", donde))
    inv["components"] = comps
    inv["extra"] = {"equipos": equipos, "alertas": alertas, "equipos_con_servicios": len(equipos),
                    "puertos_abiertos": sum(len(h["puertos"]) for h in equipos)}
    return inv


def to_markdown(inv):
    x = inv["extra"]
    out = ["# Reporte ReVital (red): %s" % inv["target"], "", "Entidad: %s" % (inv["entidad"] or "-"), "Generado: %s" % inv["generado"], "",
           "Equipos con servicios abiertos: %d · puertos abiertos: %d" % (x["equipos_con_servicios"], x["puertos_abiertos"])]
    if x["alertas"]:
        out += ["", "## Servicios expuestos", ""] + ["- " + a for a in x["alertas"]]
    out += ["", "## Equipos y servicios", "", "| Equipo | Puerto | Servicio | Programa y version | Banner |", "|---|---|---|---|---|"]
    for h in x["equipos"]:
        for p in h["puertos"]:
            prod = ", ".join(("%s %s" % pv).strip() for pv in p["productos"]) or "-"
            out.append("| %s | %d | %s | %s | %s |" % (h["ip"], p["puerto"], p["servicio"], prod.replace("|", "/"), p["banner"].replace("|", "/")))
    return "\n".join(out) + "\n"


def demo():
    """Interpreta banners reales de equipos viejos, sin tocar la red."""
    assert identificar(22, b"SSH-2.0-OpenSSH_5.3\r\n") == ("SSH", [("OpenSSH", "5.3")])
    assert identificar(21, b"220 ProFTPD 1.3.3c Server (Debian) [10.0.0.5]\r\n") == ("FTP", [("ProFTPD", "1.3.3c")])
    assert identificar(21, b"220 (vsFTPd 2.3.4)\r\n") == ("FTP", [("vsFTPd", "2.3.4")])
    assert identificar(25, b"220 mail.example ESMTP Exim 4.69 Mon, 01 Jan 2024\r\n") == ("SMTP", [("Exim", "4.69")])
    assert identificar(23, b"\xff\xfd\x18\xff\xfd\x20") == ("Telnet", [])
    assert identificar(3306, b"\x4a\x00\x00\x00\x0a5.1.73\x00\x01\x00\x00\x00") == ("MySQL", [("MySQL", "5.1.73")])
    assert identificar(3306, b"\x4a\x00\x00\x00\x0a5.5.5-10.1.48-MariaDB\x00\x01") == ("MySQL", [("MariaDB", "10.1.48")])
    h = identificar(80, b"HTTP/1.1 200 OK\r\nServer: Apache/2.2.15 (CentOS) PHP/5.3.3\r\n\r\n")
    assert h == ("HTTP", [("Apache", "2.2.15"), ("PHP", "5.3.3")]), h
    assert identificar(9999, b"") == ("desconocido", []) and identificar(445, b"") == ("SMB", [])
    for malo, causa in (("8.8.8.0/24", "privada"), ("10.0.0.0/8", "maximo"), ("no-existe.invalido", "entiendo")):
        try:
            resolver_objetivo(malo)
            raise AssertionError("debia rechazarse: " + malo)
        except ValueError as e:
            assert causa in str(e), (malo, str(e))
    assert resolver_objetivo("192.168.1.0/30") == ["192.168.1.1", "192.168.1.2"] and resolver_objetivo("127.0.0.1") == ["127.0.0.1"]
    assert resolver_objetivo("8.8.8.8", permitir_publico=True) == ["8.8.8.8"]
    print("ok")


def main():
    ap = argparse.ArgumentParser(description="Colector de red de ReVital (solo conecta y lee banners)")
    ap.add_argument("objetivo", nargs="?", help="IP, rango (192.168.1.0/24), nombre de equipo, o varios separados por coma")
    ap.add_argument("--entidad", default="")
    ap.add_argument("--out", default="salida")
    ap.add_argument("--puertos", default="", help="lista separada por comas (por defecto %d puertos comunes)" % len(PUERTOS))
    ap.add_argument("--timeout", type=float, default=1.0, help="segundos para conectar")
    ap.add_argument("--hilos", type=int, default=16, help="equipos en paralelo (poco, para no saturar equipos viejos)")
    ap.add_argument("--pausa", type=float, default=0.0, help="segundos de espera antes de cada equipo")
    ap.add_argument("--max-hosts", type=int, default=256)
    ap.add_argument("--permitir-publico", action="store_true", help="permite redes que no son privadas (requiere autorizacion escrita)")
    ap.add_argument("--autorizo", action="store_true", help="confirmo que tengo autorizacion para escanear este objetivo")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.objetivo:
        ap.error("falta el objetivo (ej. 192.168.1.0/24)")
    if not a.autorizo:
        sys.exit("Escanear una red solo es legitimo con autorizacion. Si la tienes, repite el comando con --autorizo. No se envio ningun paquete.")
    try:
        ips = resolver_objetivo(a.objetivo, a.max_hosts, a.permitir_publico)
        puertos = tuple(int(p) for p in a.puertos.split(",") if p.strip()) if a.puertos else PUERTOS
    except ValueError as e:
        sys.exit("No se escaneo nada: %s" % e)
    print("Se probaran %d equipo(s) x %d puerto(s) en %s. Solo conecta y lee banners." % (len(ips), len(puertos), a.objetivo))
    equipos = escanear(ips, puertos, a.timeout, hilos=a.hilos, pausa=a.pausa)
    tls = {}
    for h in equipos:  # protocolos TLS viejos en los puertos cifrados
        for p in h["puertos"]:
            if p["puerto"] in TLS_PUERTOS:
                tls["%s:%d" % (h["ip"], p["puerto"])] = list(sondear_tls(h["ip"], p["puerto"], 3))
    inv = a_inventario(equipos, a.objetivo, a.entidad, tls)
    j = inventory.guardar(inv, a.out)
    md = os.path.join(a.out, "reporte-%s-red-%s.md" % (a.entidad or "sin-entidad", inventory.slug(a.objetivo)))
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(inv))
    print("listo: %s y %s (%d equipos, %d puertos abiertos, %d alertas)" % (j, md, len(equipos), inv["extra"]["puertos_abiertos"], len(inv["extra"]["alertas"])))


if __name__ == "__main__":
    main()
