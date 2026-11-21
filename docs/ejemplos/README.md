# Ejemplos de salida (respaldo para la demo)

Salida real del colector web contra el caso `casos/portal-muni-gt` (Drupal 7.57 + Apache 2.4.49, institución **ficticia**), generada el 21-nov-2026 en local y offline. Sirven de respaldo si la demo en vivo falla.

| Archivo | Qué es |
|---|---|
| `portal-muni-gt/inventario-web-localhost-8080.json` | Inventario en el contrato común (`revital/inventory.py`): lo que consume `reglas-cisa-cves` |
| `portal-muni-gt/reporte-MUNI-GT-web.md` | Reporte legible del colector web: componentes, rutas de `robots.txt`, páginas y formularios |

Regenerar:
```
cd casos/portal-muni-gt/docker && docker compose up -d --build && bash instalar_drupal.sh
python -m revital.crawler http://localhost:8080 --entidad "MUNI-GT" --out salida
```

> Nota: la salida se capturó cuando la muni ficticia se llamaba "San Ejemplo"; se alineó al nombre
> definitivo **MUNI-GT** (entidad, nombre de archivo y el `site_name` que aparece en los títulos de
> página). La estructura real del crawl (rutas, estados, formularios, versiones) no se tocó. Al
> regenerar con el `instalar_drupal.sh` actual (que ya instala el sitio como MUNI-GT) sale idéntico.
