# Backend legacy de MuniSoke (SIREC) para el demo
Estado: listo en local (backend + frontend probados juntos); sin subir
Rama: `feat/backend-sirec`

## Objetivo
Detrás del portal Drupal, MuniSoke tiene el "servidor de la muni" típico de una municipalidad guatemalteca: un sistema de recaudación hecho a medida hace años, la base de datos de contribuyentes, un FTP para subir actas y un correo. Todo es **software real y vulnerable** (no simulado), con **datos ficticios**. ReVital, al soltarse sobre ese servidor, debe hacer saltar las 4 clases de alerta del demo.

## Servicios (todos reales)
| Servicio | Software real | Puerto | Qué alerta produce en ReVital | Colector |
|---|---|---|---|---|
| BD de contribuyentes | MySQL **5.5.62** (imagen oficial), root remoto con clave débil | 3306 | *Servicio inseguro expuesto: base de datos MySQL* · fuera de soporte | red |
| SIREC (recaudación IUSI, boleto de ornato, multas) | Tomcat **8.5.19** + app Java propia con **Struts 2.3.31**, **Log4j 2.14.1**, **Spring 5.3.17**, compilada con Maven | sin puerto propio: vía proxy `/sirec/` | KEV: CVE-2017-5638 (Struts), CVE-2021-44228 (Log4Shell), CVE-2022-22965 (Spring4Shell) | código (+ web: Struts por `.action`) |
| FTP de actas y transparencia | ProFTPD **1.3.5** compilado de fuente con `mod_copy` | 21 | KEV CVE-2015-3306 · *FTP sin cifrar expuesto* | red |
| Correo de la muni | Exim **4.89** compilado de fuente | 25 | KEV CVE-2018-6789, CVE-2019-10149 | red |
| Caché de sesiones de SIREC | Redis **5.0.7** sin contraseña | 6379 | *Redis (sin clave por defecto) expuesto* | red |

Versiones elegidas porque **el cruce actual de ReVital ya las marca** (probado hoy con `revital.cves` sobre un inventario de prueba). MySQL y Redis no tienen KEV por versión: su alerta es estar expuestos a la red.

## Las 4 alertas del demo
1. **Servicios expuestos** — `revital.red` contra el servidor: MySQL, FTP y Redis abiertos a la red.
2. **KEV por banner** — ProFTPD 1.3.5 y Exim 4.89 anuncian su versión; el cruce los marca como explotados (CISA KEV).
3. **Código del backend** — `revital.codigo` sobre `backend/sirec/` (`pom.xml`): Struts, Log4j y Spring con KEV.
4. **Cambio en vivo** — el FTP arranca **apagado**. Durante la presentación se enciende ("el proveedor habilitó FTP para subir actas") y el **sentinela** avisa en el panel: *Apareció ProFTPD 1.3.5* + *Vulnerabilidad explotada nueva: CVE-2015-3306*.

## Datos ficticios (MySQL `sirec`)
Tablas: `contribuyentes` (nombre, DPI ficticio, NIT, dirección en zonas de Soke), `inmuebles` (finca, valor fiscal, IUSI anual), `pagos` (IUSI, ornato, agua, multas PMT), `solicitudes_laip` (folio, fecha, plazo de 10 días, estado), `usuarios_sirec` (operadores con contraseña en **MD5 sin sal**, realista en sistemas de esa época). ~300 contribuyentes generados por script con semilla fija; cada registro dice que es ficticio. ReVital no lee el contenido: los datos muestran *qué está en riesgo* en el pitch.

## Fuera de alcance
- ReVital no se conecta a la BD ni lee su contenido.
- No se escriben exploits ni se demuestran ataques; solo se detecta.
- Webmin, Samba, Elasticsearch: posibles después, no en esta entrega.

## Seguridad
Estos servicios **sí son explotables** (por ejemplo, Struts S2-045 y ProFTPD mod_copy). Por eso:
- Por defecto escuchan solo en `127.0.0.1`. Para el demo, `compose.override.yml` (local, no se sube) los publica solo en la IP de Tailscale, igual que el proxy actual.
- Red de Docker propia, sin salida a internet para SIREC y la BD.
- Nunca se publican en `0.0.0.0` ni en internet.

## Cambios en ReVital
- `revital.sentinela`: hoy solo vigila objetivos `web` y `codigo`. Se agrega `red` (llama a `revital.red ... --autorizo` con los puertos indicados). Con prueba primero.
- `revital.codigo`: no leía un `pom.xml` con la cabecera estándar de Maven (`xsi:schemaLocation` quedaba sin declarar). Corregido con prueba.
- Pendiente (opcional): el crawler no ve la versión de Tomcat porque no pide una página de error dentro de `/sirec/`; las KEV de Tomcat no salen.

## Plan (cada tarea con evidencia al cerrar)
- [x] T1 — sentinela soporta objetivos `red` — `tests/test_sentinela.py` ok (FTP que aparece → `componente_nuevo` + `kev_nueva` CVE-2015-3306).
- [x] T2 — MySQL 5.5.62 + esquema + datos ficticios — `backend/db/test_datos.py` ok; cargado en `mysql:5.5.62` (300 contribuyentes, saldos del contrato exactos).
- [x] T3 — SIREC en Tomcat 8.5.19 — `test_sirec_api.py` ok contra `http://100.91.166.18:8088`; login Struts `cajero1` ok; Redis cachea `iusi:*`.
- [x] T4 — ProFTPD 1.3.5 — banner `220 ProFTPD 1.3.5 Server (FTP MuniSoke)`, `mod_copy` compilado, KEV CVE-2015-3306.
- [x] T5 — Exim 4.89 — banner `ESMTP Exim 4.89`, KEV CVE-2018-6789 y CVE-2019-10149.
- [x] T6 — Redis 5.0.7 sin contraseña — `PING → PONG` desde la tailnet; alerta "Redis expuesto".
- [x] T7 — compose (FTP en perfil `cambio`, SIREC en red interna) + override de Tailscale — `docker compose config` ok; todo publicado solo en 100.91.166.18.
- [x] T8 — `docker/verificar-backend.sh` (4/4 OK) y `docker/sentinela.demo.json`.
- [x] T9 — punta a punta: red + web + código + cves en una entidad → MySQL/Redis expuestos, Exim, Struts/Log4j/Spring, Drupal/Apache; encender FTP → alerta del sentinela.
- [x] T10 — guion del demo en `casos/portal-muni-gt/backend/README.md`.
- [x] T11 — frontend de Antigravity (`feat/frontend-sirec`) probado en el navegador contra SIREC real: IUSI (F-1024, F-2048, F-0000), órdenes de agua, multa, ornato y finca al día, LAIP + seguimiento; 0 errores en consola; portal 6/6.

Orden por valor si falta tiempo: T2 → T6 → T1 → T7/T8 (ya hay alertas 1) → T4 (alertas 2 y 4) → T3 (alerta 3) → T5.

## Decisiones
- 2026-11-21 — Servicios reales, no simulados (decisión del equipo). Más lento de construir; se compensa ordenando por valor.
- 2026-11-21 — Datos ficticios realistas de una muni; ReVital no lee la BD.

## Siguiente paso
Subir las dos ramas y abrir los PRs (backend y frontend).
