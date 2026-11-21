"""Vigilancia por entidad desde el panel (interruptor 'Vigilar cada hora').

Guarda los objetivos vigilados en salida/vigilancia.json (mismo formato que sentinela.json) y, mientras el panel esta
abierto, corre una vuelta del sentinela cuando toca. No cambia revital/sentinela.py: lo usa tal cual.
"""
import json, os, subprocess, sys, threading, time

from revital.panel import datos

CADA_MINUTOS = 60


def ruta(salida):
    return os.path.join(salida, "vigilancia.json")


def leer(salida):
    cfg = datos.leer(ruta(salida), None) or {}
    cfg.setdefault("cada_minutos", CADA_MINUTOS)
    cfg.setdefault("objetivos", [])
    cfg["salida"] = salida
    cfg.setdefault("al_detectar_cambio", "")
    return cfg


def _guardar(salida, cfg):
    os.makedirs(salida, exist_ok=True)
    with open(ruta(salida), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)


def vigilada(salida, entidad):
    return any(o.get("entidad", "").lower() == (entidad or "").lower() for o in leer(salida)["objetivos"])


def objetivos_de(salida, entidad):
    """Lo que ya se analizo de esa entidad (sitios web y carpetas) es lo que se vigila."""
    out = []
    for inv in datos.inventarios(salida, entidad):
        kind, target = inv.get("kind"), inv.get("target") or ""
        if kind in ("web", "codigo") and target:
            o = {"entidad": entidad, "tipo": kind, "destino": target}
            if kind == "web":
                o["insecure"] = target.lower().startswith("https://")  # servidores viejos: TLS 1.0 / certificados vencidos
            if o not in out:
                out.append(o)
    return out


def cambiar(salida, entidad, activar):
    cfg = leer(salida)
    cfg["objetivos"] = [o for o in cfg["objetivos"] if o.get("entidad", "").lower() != entidad.lower()]
    if activar:
        cfg["objetivos"] += objetivos_de(salida, entidad)
    _guardar(salida, cfg)
    return bool(activar and cfg["objetivos"])


def iniciar(salida, raiz, revisar_cada=30):
    """Hilo en segundo plano: si hay objetivos vigilados y paso el tiempo, corre una vuelta del sentinela."""
    def ciclo():
        while True:
            try:
                cfg = leer(salida)
                if cfg["objetivos"]:
                    ult = datos.leer(os.path.join(salida, "sentinela-estado.json"), {}) or {}
                    try:
                        hace = time.time() - time.mktime(time.strptime(ult.get("ultima_vuelta", ""), "%Y-%m-%d %H:%M:%S"))
                    except (ValueError, TypeError):
                        hace = 10 ** 9
                    if hace >= cfg["cada_minutos"] * 60 and not ult.get("analizando"):
                        subprocess.call([sys.executable, "-m", "revital.sentinela", "--config", ruta(salida), "--una-vez"], cwd=raiz,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:  # la vigilancia nunca debe tumbar el panel
                pass
            time.sleep(revisar_cada)
    t = threading.Thread(target=ciclo, daemon=True)
    t.start()
    return t
