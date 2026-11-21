# ReVital

Se suelta sobre una app, un servidor o una institución, documenta qué tecnología hay (aunque sea legacy), y recomienda qué CVEs y reglas CISA (KEV) priorizar para parchear. Entrega un `.md`/`.txt` por entidad con inventario y cumplimiento.

Solo stdlib de Python 3.8+ (corre en Windows 7). Linux viejo: fuera de scope por ahora. Usar solo contra sistemas propios o con autorización.

## Arquitectura
```
 colectores (cada uno -> salida/inventario-<kind>-<destino>.json, formato en revital/inventory.py)
   web     : crawler de URL                       (rama crawler)
   red     : rango/hosts de una institución       (rama crawler)
   codigo  : carpeta de una app legacy            (rama directorios)
   host    : equipo/servidor Windows viejo local  (rama adaptaciones-windows)
        │
        ▼
 evaluación: componentes -> CVE (NVD) -> ¿en CISA KEV?    (rama reglas-cisa-cves)
        │
        ▼
 reporte por entidad: salida/reporte-<entidad>.md
   inventario + hallazgos priorizados + cumplimiento
```

## Contrato (`inventory.py`)
`{kind, target, entidad, generado, components:[{producto, version, fuente, donde}], extra:{}}`
Los colectores solo llenan `components` (y lo que quieran en `extra`). Nadie lee el JSON de otro más allá de esto.

## Panel y sentinela (entrar, ver, descargar y vigilar)
```
python -m revital.panel --abrir                          # panel en http://127.0.0.1:8765 (solo este equipo)
python -m revital.sentinela --config sentinela.json      # vigila en bucle y avisa de cambios
```
- **Panel:** resumen por entidad (cumple / no cumple, qué parchear primero), hallazgos con evidencia, inventario, documentación para ver o descargar (`.zip`) y lanzar análisis desde la pantalla. Sin JavaScript, sin internet y sin librerías: corre en equipos viejos (Python 3.8). Solo escucha en `127.0.0.1`.
- **Sentinela:** vuelve a analizar cada `cada_minutos`, compara con la vez anterior y avisa si aparece un componente nuevo, cambia una versión, se abre una KEV o un objetivo deja de responder. Los avisos se ven en el panel y puede ejecutar un comando propio (`al_detectar_cambio`). Ejemplo: `revital/sentinela.ejemplo.json`.
## Documentar un equipo Windows viejo (host)
```
scripts\revital-host.bat MI-INSTITUCION        # doble clic o consola; solo lectura
python -m revital.host --entidad MI-INSTITUCION   # lo mismo sin el .bat
python -m revital.cves --entidad MI-INSTITUCION   # cruza con KEV: parche, mitigacion y regla WAF por vulnerabilidad
python -m revital.panel --abrir                   # ver y descargar el resultado
```
Lee del registro de Windows el sistema, IIS, .NET, Internet Explorer, los programas instalados con su version, los parches y los puertos en escucha, y avisa de configuraciones inseguras tipicas (SMBv1, escritorio remoto, UAC, sistema sin soporte, sin parches). Windows en si no se cruza con CVE (NVD no distingue parches); se reporta su fin de soporte y las alertas.

## Descubrir qué hay en una red (PoC)
```
python -m revital.red 192.168.1.0/24 --entidad MI-INSTITUCION --autorizo   # solo conecta y lee banners; --autorizo es obligatorio
python -m revital.cves --entidad MI-INSTITUCION                            # cruza con KEV y muestra qué parchear
```
Por defecto solo redes privadas, máximo 256 equipos y pocas conexiones a la vez. Usar solo en redes propias o con autorizacion por escrito.

## Ramas (cada una toca su carpeta)
| Rama | Carpeta | Qué |
|---|---|---|
| `crawler` | `revital/crawler.py`, `revital/red.py` | Colector web y de red |
| `directorios` | `revital/codigo.py` | Colector de carpeta/app: web.config, pom.xml, DLLs, composer.json... |
| `adaptaciones-windows` | `revital/host.py`, `scripts/` | Colector de equipo local en Windows viejo + `.bat` + TLS/Python viejo |
| `reglas-cisa-cves` | `revital/cves/` | Catálogos offline KEV/NVD, cruce y prioridad, reporte final |
| `caso/portal-muni-drupal` | `casos/portal-muni-gt/` | Caso de demo: portal de transparencia muni (ficticio) sobre Drupal 7 + Apache 2.4.49, con CVEs en KEV |

## Uso (objetivo)
```
python -m revital.crawler https://app.interna.gob --insecure --entidad MINFIN
python -m revital.crawler --demo      # autocomprobación sin red
```

## Flujo de equipo
Ramas cortas, PR a `main`, commits pequeños. Cambios al contrato van primero a `main`.
