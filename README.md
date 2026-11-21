# ReVital

Documenta apps web legacy (gobierno), genera reportes y recomienda qué CVEs y reglas CISA (KEV) priorizar para parchear. Pensado para correr en tecnología vieja (Windows viejo; Linux viejo fuera de scope por ahora).

Solo stdlib de Python 3.8+ (corre en Windows 7). Usar solo contra sistemas propios o con autorización.

## Flujo
`crawler` -> `salida/reporte.json` -> `reglas-cisa-cves` -> recomendaciones de parcheo

## Estructura y ramas (una por integrante, cada una toca su carpeta)
| Rama | Carpeta | Qué |
|---|---|---|
| `crawler` | `revital/crawler.py` | Crawler + reporte.json/.md |
| `reglas-cisa-cves` | `revital/cves/` | Cruce con catálogo CISA KEV y NVD (offline) |
| `directorios` | `revital/dirs/` | Descubrimiento de directorios/rutas comunes y monitoreo |
| `adaptaciones-windows` | `revital/compat/`, `scripts/` | Compatibilidad Windows/Linux viejos (TLS, Python viejo, .bat) |

## Uso
```
python -m revital.crawler https://app.interna.gob --insecure --out salida
python -m revital.crawler --demo   # autocomprobación sin red
```

## Flujo de trabajo
Ramas cortas, PR a `main`, commits pequeños. Contrato entre módulos: `salida/reporte.json` (campos `start`, `pages[]`, `tech[]`).
