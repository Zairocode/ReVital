# Cómo probar ReVital

Tres formas, de la más simple a la compartida. Para todas necesitas Python 3.8+ (y Docker solo para el caso de demo).

## 1. Local, todo en tu máquina (lo más simple y recomendado)

```bash
git clone https://github.com/Zairocode/ReVital && cd ReVital

# Caso de demo: portal MuniSoke GT (Drupal 7.57 + Apache 2.4.49)
cd casos/portal-muni-gt/docker && docker compose up -d --build && bash instalar_drupal.sh
cd ../../..

# Pipeline de 3 capas
python -m revital.crawler http://localhost:8080 --entidad MUNI-GT --out salida   # Capa 1
python -m revital.cves --out salida --entidad MUNI-GT                            # Capa 2
python -m revital.panel --abrir                                                  # Capa 3
```

¿Sin Docker? El pipeline corre sin red con el caso de ejemplo:
```bash
python -m revital.cves --demo      # debe terminar en "ok"
python tests/test_cves.py          # pruebas
```

Verificar que el objetivo está arriba y vulnerable:
```bash
bash casos/portal-muni-gt/docker/verificar.sh
```

## 2. Compartir el objetivo MuniSoke para que otros lo escaneen (Tailscale)

El objetivo (Docker) **sí** es para acceso remoto; está hecho para que le apunten escáneres.

1. Instala Tailscale en cada máquina y únelas al mismo Tailnet.
2. En la ACL, permite que esas máquinas lleguen al equipo que corre el Docker (p. ej. `phobos`).
3. Comparte la URL por la IP de Tailscale, p. ej. `http://100.x.x.x:8080`.
4. Cada quien ya puede apuntar su crawler: `python -m revital.crawler http://100.x.x.x:8080 --entidad MUNI-GT`.

> ⚠️ El objetivo es **deliberadamente vulnerable**. Solo por Tailscale/LAN. **Nunca** lo expongas a internet.

## 3. Ver el panel desde otra máquina (túnel)

El panel escucha **solo en `127.0.0.1`** a propósito (los hallazgos son sensibles) y rechaza con 403 cualquier otro host. Para verlo remoto sin romper eso, usa un túnel:

```bash
# en tu máquina, contra el equipo que corre el panel:
ssh -L 8765:127.0.0.1:8765 usuario@host
# luego abre en tu navegador:  http://127.0.0.1:8765
```
(o `tailscale serve` si usan Tailscale). No lo expongas con un bind a `0.0.0.0`.

## Problemas comunes

- **El crawler da inventario vacío / "timed out":** el objetivo no respondió (sitio caído, lento o red bloqueada). No es que falten vulnerabilidades. Sube el tiempo con `--timeout 40`, prueba `https://`, o confirma con `curl -I <url>`.
- **No detecta vulnerabilidades:** asegúrate de correr **la Capa 2** (`python -m revital.cves`), no solo el crawler; y revisa que el inventario traiga **versiones**. KEV es un subconjunto pequeño: para CVEs fuera de KEV, corre `python -m revital.cves --actualizar`.
- **Puerto ocupado:** `python -m revital.panel --puerto 8766`.
- **Mac con chip Apple:** descomenta `platform: linux/amd64` en `casos/portal-muni-gt/docker/docker-compose.yml`.

> Usar ReVital solo contra sistemas propios o con autorización por escrito.
