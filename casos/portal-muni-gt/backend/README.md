# Servidor de la muni (backend SIREC) — caso MUNI-GT

El "servidor de la muni" detrás del portal MuniSoke GT: software **real y vulnerable**, datos **ficticios**. Sirve para que ReVital, soltado sobre él, haga saltar las alertas del demo. Diseño y decisiones: `docs/features/backend-sirec.md`; contrato de la API: `docs/features/sirec-api.md`.

> ⚠️ Deliberadamente vulnerable (Struts S2-045, Log4Shell, ProFTPD mod_copy, Exim). Por defecto escucha solo en `127.0.0.1`; para el demo se publica **solo** en la IP de Tailscale con `docker/compose.override.yml` (local, no se sube). **Nunca** en `0.0.0.0` ni en internet. SIREC no tiene salida a internet (red `sirec_priv` interna).

| Carpeta | Servicio | Puerto | Qué hace saltar en ReVital |
|---|---|---|---|
| `db/` | MySQL 5.5.62 (oficial) + esquema y datos ficticios | 3306 | Base de datos expuesta a la red |
| — | Redis 5.0.7 (oficial) sin clave | 6379 | Redis expuesto |
| `sirec/` | SIREC 3.2.1: Tomcat 8.5.19 + Struts 2.3.31 + Spring 5.3.17 + Log4j 2.14.1 | vía proxy `/sirec/` | KEV en el código (colector `codigo`) |
| `correo/` | Exim 4.89 compilado de la fuente | 25 | KEV CVE-2018-6789, CVE-2019-10149 |
| `ftp/` | ProFTPD 1.3.5 compilado de la fuente, con `mod_copy` (perfil `cambio`, arranca apagado) | 21 | FTP expuesto + KEV CVE-2015-3306; y el **cambio en vivo** |

## Levantar y verificar
```bash
cd casos/portal-muni-gt/docker
docker compose up -d --build                      # portal + servidor de la muni (FTP queda apagado)
bash verificar-backend.sh 100.91.166.18           # Exim, MySQL, Redis y SIREC arriba; FTP apagado
bash verificar.sh http://100.91.166.18:8088       # el portal sigue 6/6
SIREC_BASE=http://100.91.166.18:8088 python3 ../backend/test_sirec_api.py   # contrato de la API
```
Pruebas sin Docker: `python3 casos/portal-muni-gt/backend/db/test_datos.py` (datos ficticios y semilla del contrato). Si cambias el generador: `python3 db/generar_datos.py` (reescribe `db/initdb/02-datos.sql`).

## Guion del demo (≈3 min), desde la raíz del repo
1. **Inventario y alertas** (antes de presentar, o en vivo):
   ```bash
   python -m revital.red 100.91.166.18 --puertos 21,25,3306,6379,8088 --entidad MUNI-GT --autorizo
   python -m revital.crawler http://100.91.166.18:8088 --entidad MUNI-GT
   python -m revital.codigo casos/portal-muni-gt/backend/sirec --entidad MUNI-GT
   python -m revital.cves --entidad MUNI-GT
   python -m revital.panel --abrir
   ```
   En el panel: MySQL y Redis expuestos, Exim con KEV, Struts/Log4Shell/Spring4Shell en el código, Drupal y Apache 2.4.49 en el portal.
   No incluir los puertos 22 ni 443 del equipo anfitrión: no son de la muni.
2. **Sentinela vigilando**: `python -m revital.sentinela --config casos/portal-muni-gt/docker/sentinela.demo.json` (vuelta cada minuto; la primera es la línea base).
3. **Cambio en vivo**: "el proveedor habilitó FTP para subir las actas":
   ```bash
   cd casos/portal-muni-gt/docker && docker compose --profile cambio up -d ftp
   ```
   En la siguiente vuelta el panel avisa: *Apareció ProFTPD 1.3.5* y *Vulnerabilidad explotada nueva: CVE-2015-3306*.
4. Al terminar: `docker compose --profile cambio stop ftp` para dejarlo listo para la próxima.

## Datos ficticios
300 contribuyentes, 371 inmuebles con IUSI por trimestre, boletos de ornato, contadores de agua, multas PMT, 52 solicitudes LAIP y 5 operadores con clave en MD5 sin sal (p. ej. `cajero1` / `muni2014` en `/sirec/login.action`). Nombres armados combinando nombres y apellidos comunes; DPI, NIT, teléfonos y fincas inventados; cada contribuyente lleva `nota = 'DATO FICTICIO'`.
