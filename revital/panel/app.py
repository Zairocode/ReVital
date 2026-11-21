"""Servidor del panel (solo stdlib). Escucha SOLO en 127.0.0.1: los hallazgos son informacion sensible."""
import json, os, re, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from revital import inventory
from revital.panel import datos, vigilancia, vistas

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TIPOS = {".md": "text/markdown; charset=utf-8", ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8"}
ENTIDAD_OK = re.compile(r"^[\w .\-]{1,60}$")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TIPOS_STATIC = {".js": "application/javascript; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
SSL_FALLA = re.compile(r"ssl|certificate|tlsv|wrong version|handshake|unsupported protocol", re.I)


class Panel(object):
    """Estado compartido: carpeta de salida y trabajos lanzados desde la pantalla."""

    def __init__(self, salida, config="sentinela.json"):
        self.salida, self.config = os.path.abspath(salida), config
        self.trabajos, self.lock = [], threading.Lock()

    def correr(self, args, log_extra=None):
        p = subprocess.Popen([sys.executable, "-m"] + args, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        out = p.communicate()[0] or ""
        return p.returncode, out

    def lanzar(self, tipo, destino, entidad, insecure):
        t = {"tipo": "Sitio web" if tipo == "web" else "Código", "destino": destino, "entidad": entidad, "estado": "en curso",
             "inicio": time.strftime("%Y-%m-%d %H:%M:%S"), "log": "", "slug": inventory.slug(entidad) or "sin-entidad"}
        with self.lock:
            self.trabajos.insert(0, t)

        def hacer():
            if tipo == "web":
                cmd = ["revital.crawler", destino, "--entidad", entidad, "--out", self.salida, "--delay", "0.2"] + (["--insecure"] if insecure else [])
            else:
                cmd = ["revital.codigo", destino, "--entidad", entidad, "--out", self.salida]
            try:
                rc, out = self.correr(cmd)
                t["log"] += out
                if tipo == "web" and not insecure and self.fallo_tls(destino):
                    # servidor viejo (TLS 1.0, certificado vencido/autofirmado): se reintenta en modo compatible
                    t["log"] += "\nServidor viejo detectado: se reintenta en modo compatible (TLS 1.0 / certificado no valido).\n"
                    t["compatible"] = True
                    rc, out = self.correr(cmd + ["--insecure"])
                    t["log"] += out
                if rc == 0:
                    rc2, out2 = self.correr(["revital.cves", "--out", self.salida, "--entidad", entidad])
                    t["log"] += "\n" + out2
                    rc = rc2
                t["estado"] = "listo" if rc == 0 else "error"
            except Exception as ex:  # el panel no debe caerse por un analisis fallido
                t["log"] += "\nError: %s" % ex
                t["estado"] = "error"
        threading.Thread(target=hacer, daemon=True).start()
        return t

    def fallo_tls(self, destino):
        """El crawler no pudo entrar a la pagina de inicio por un problema de TLS/certificado."""
        inv = datos.leer(os.path.join(self.salida, "inventario-web-%s.json" % inventory.slug(destino)), {}) or {}
        pags = (inv.get("extra") or {}).get("pages") or []
        return bool(pags) and all(p.get("error") for p in pags) and any(SSL_FALLA.search(p.get("error", "")) for p in pags)

    def firma(self):
        """Cambia cuando cambia algo que el panel muestra: sirve para recargar la pantalla sola."""
        partes = []
        if os.path.isdir(self.salida):
            for n in sorted(os.listdir(self.salida)):
                if n.endswith((".json", ".jsonl", ".md")):
                    try:
                        partes.append("%s:%d" % (n, os.path.getmtime(os.path.join(self.salida, n))))
                    except OSError:
                        pass
        with self.lock:
            partes += ["%s:%s" % (t["inicio"], t["estado"]) for t in self.trabajos]
        return str(abs(hash("|".join(partes))))


def crear(salida="salida", puerto=8765, config="sentinela.json"):
    panel = Panel(salida, config)
    vigilancia.iniciar(panel.salida, RAIZ)

    class H(BaseHTTPRequestHandler):
        server_version = "ReVital"

        def log_message(self, *a):
            pass

        # ---- utilidades
        def _host_ok(self):
            h = (self.headers.get("Host") or "").lower()
            return h in ("127.0.0.1:%d" % puerto, "localhost:%d" % puerto, "[::1]:%d" % puerto)

        def _enviar(self, codigo, cuerpo, tipo="text/html; charset=utf-8", extra=None):
            b = cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(b)

        def _redir(self, destino):
            self.send_response(303)
            self.send_header("Location", destino)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _err(self, codigo, texto):
            self._enviar(codigo, vistas.error(codigo, texto))

        # ---- GET
        def do_GET(self):
            if not self._host_ok():
                return self._err(403, "Este panel solo responde en este equipo (127.0.0.1).")
            u = urlparse(self.path)
            q = parse_qs(u.query)
            ruta = unquote(u.path)
            sal = panel.salida
            if ruta == "/":
                with panel.lock:
                    pass
                msg = (q.get("msg") or [""])[0]
                with panel.lock:
                    lista = list(panel.trabajos)
                return self._enviar(200, vistas.inicio(datos.entidades(sal), datos.alertas(sal), datos.estado_sentinela(sal), msg,
                                                       trabajos=lista, sel=(q.get("e") or [""])[0]))
            if ruta.startswith("/e/"):
                x = datos.entidad(sal, ruta[3:])
                if not x:
                    return self._err(404, "No hay una entidad con ese nombre.")
                tab = (q.get("tab") or ["resumen"])[0]
                nombre = x["entidad"]
                return self._enviar(200, vistas.entidad(x, tab, datos.alertas(sal, entidad=nombre), datos.historial(sal, x["slug"]),
                                                        datos.archivos(sal, x["slug"], nombre), todos=("todos" in q), filtro=(q.get("f") or [""])[0],
                                                        vigilada=vigilancia.vigilada(sal, nombre)))
            if ruta.startswith("/static/"):
                nombre = ruta[len("/static/"):]
                ext = os.path.splitext(nombre)[1].lower()
                if nombre != os.path.basename(nombre) or ext not in TIPOS_STATIC or nombre not in os.listdir(STATIC):
                    return self._err(404, "Archivo no encontrado.")
                with open(os.path.join(STATIC, nombre), "rb") as fh:
                    return self._enviar(200, fh.read(), TIPOS_STATIC[ext])
            if ruta == "/api/estado":
                with panel.lock:
                    curso = sum(1 for t in panel.trabajos if t["estado"] == "en curso")
                return self._enviar(200, json.dumps({"v": panel.firma(), "en_curso": curso}), "application/json; charset=utf-8")
            if ruta.startswith("/ver/") or ruta.startswith("/descargar/"):
                nombre = ruta.split("/", 2)[2]
                p = datos.ruta_segura(sal, nombre)
                ext = os.path.splitext(nombre)[1].lower()
                if not p or ext not in TIPOS:
                    return self._err(404, "Archivo no encontrado.")
                with open(p, "rb") as f:
                    raw = f.read()
                if ruta.startswith("/descargar/"):
                    return self._enviar(200, raw, TIPOS[ext], {"Content-Disposition": 'attachment; filename="%s"' % nombre.replace('"', "")})
                slug = None
                for x in datos.entidades(sal):
                    if nombre in [a["nombre"] for a in datos.archivos(sal, x["slug"], x["entidad"])]:
                        slug = x["slug"]
                        break
                return self._enviar(200, vistas.documento(nombre, raw.decode("utf-8", "replace"), slug))
            if ruta.startswith("/zip/"):
                x = datos.entidad(sal, ruta[5:])
                if not x:
                    return self._err(404, "No hay una entidad con ese nombre.")
                return self._enviar(200, datos.zip_de(sal, x["slug"], x["entidad"]), "application/zip",
                                    {"Content-Disposition": 'attachment; filename="ReVital-%s.zip"' % x["slug"]})
            if ruta == "/sentinela":
                ej = os.path.join(RAIZ, "revital", "sentinela.ejemplo.json")
                try:
                    with open(ej, encoding="utf-8") as f:
                        txt = f.read()
                except OSError:
                    txt = "{}"
                return self._enviar(200, vistas.sentinela(datos.estado_sentinela(sal), datos.alertas(sal, 60), txt))
            if ruta == "/trabajos":
                with panel.lock:
                    lista = list(panel.trabajos)
                return self._enviar(200, vistas.trabajos(lista))
            if ruta == "/favicon.ico":
                return self._enviar(204, b"")
            return self._err(404, "Página no encontrada.")

        # ---- POST
        def do_POST(self):
            if not self._host_ok():
                return self._err(403, "Este panel solo responde en este equipo (127.0.0.1).")
            origen = self.headers.get("Origin") or ""
            if origen and urlparse(origen).netloc.lower() not in ("127.0.0.1:%d" % puerto, "localhost:%d" % puerto):
                return self._err(403, "Origen no permitido.")
            n = int(self.headers.get("Content-Length") or 0)
            if n > 65536:
                return self._err(413, "Formulario demasiado grande.")
            f = parse_qs(self.rfile.read(n).decode("utf-8", "replace"))

            def campo(k):
                return (f.get(k) or [""])[0].strip()
            ruta = urlparse(self.path).path
            if ruta == "/analizar":
                tipo, destino, ent = campo("tipo"), campo("destino"), campo("entidad")
                if not tipo:  # un solo buscador: una URL es un sitio web; lo demas, una carpeta
                    tipo = "web" if re.match(r"^https?://", destino, re.I) else "codigo"
                if not campo("autorizo"):
                    return self._err(400, "Hay que confirmar que tienes autorización para analizar este sistema.")
                if tipo not in ("web", "codigo") or not ENTIDAD_OK.match(ent):
                    return self._err(400, "Tipo o nombre de entidad no válido (letras, números, espacios, punto y guion; máx. 60).")
                if tipo == "web" and not re.match(r"^https?://[^\s]+$", destino):
                    return self._err(400, "La URL debe empezar con http:// o https://")
                if tipo == "codigo" and not os.path.isdir(destino):
                    return self._err(400, "La carpeta no existe en este equipo: %s" % destino)
                panel.lanzar(tipo, destino, ent, bool(campo("insecure")))
                return self._redir("/?e=%s" % (inventory.slug(ent) or ""))
            if ruta == "/demo":
                rc, out = panel.correr(["revital.cves", "--demo", "--out", panel.salida])
                return self._redir("/?msg=" + ("Demostración cargada." if rc == 0 else "No se pudo cargar la demostración."))
            if ruta == "/vigilar":
                x = datos.entidad(panel.salida, campo("slug"))
                if not x:
                    return self._err(404, "No hay una entidad con ese nombre.")
                vigilancia.cambiar(panel.salida, x["entidad"], campo("activar") == "1")
                return self._redir("/e/%s" % x["slug"])
            if ruta == "/vigilar-ahora":
                cfg = panel.config if os.path.isfile(panel.config) else os.path.join(RAIZ, "sentinela.json")
                if not os.path.isfile(cfg):
                    return self._redir("/sentinela?aviso=sin-config")
                subprocess.Popen([sys.executable, "-m", "revital.sentinela", "--config", cfg, "--una-vez"], cwd=RAIZ,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._redir("/sentinela")
            return self._err(404, "Página no encontrada.")

    srv = ThreadingHTTPServer(("127.0.0.1", puerto), H)
    srv.panel = panel
    return srv
