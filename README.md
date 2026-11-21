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

## Ramas (cada una toca su carpeta)
| Rama | Carpeta | Qué |
|---|---|---|
| `crawler` | `revital/crawler.py`, `revital/red.py` | Colector web y de red |
| `directorios` | `revital/codigo.py` | Colector de carpeta/app: web.config, pom.xml, DLLs, composer.json... |
| `adaptaciones-windows` | `revital/host.py`, `scripts/` | Colector de equipo local en Windows viejo + `.bat` + TLS/Python viejo |
| `reglas-cisa-cves` | `revital/cves/` | Catálogos offline KEV/NVD, cruce y prioridad, reporte final |

## Uso (objetivo)
```
python -m revital.crawler https://app.interna.gob --insecure --entidad MINFIN
python -m revital.crawler --demo      # autocomprobación sin red
```

## Flujo de equipo
Ramas cortas, PR a `main`, commits pequeños. Cambios al contrato van primero a `main`.
