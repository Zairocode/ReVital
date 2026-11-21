"""python -m revital.panel [--salida salida] [--puerto 8765] [--abrir]

Panel local para entrar, ver y descargar la documentacion y los hallazgos. Solo escucha en 127.0.0.1 (este equipo).
"""
import argparse, sys, threading, webbrowser

from revital.panel import app


def main():
    ap = argparse.ArgumentParser(description="Panel local de ReVital")
    ap.add_argument("--salida", default="salida", help="carpeta con los resultados (por defecto: salida)")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--config", default="sentinela.json", help="configuracion del sentinela (para el boton Vigilar ahora)")
    ap.add_argument("--abrir", action="store_true", help="abre el navegador")
    a = ap.parse_args()
    try:
        srv = app.crear(a.salida, a.puerto, a.config)
    except OSError as e:
        sys.exit("No pude abrir el puerto %d (%s). Prueba con --puerto 8766." % (a.puerto, e))
    url = "http://127.0.0.1:%d/" % a.puerto
    print("ReVital panel en %s  (Ctrl+C para cerrar). Solo accesible desde este equipo." % url)
    if a.abrir:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\npanel cerrado")


if __name__ == "__main__":
    main()
