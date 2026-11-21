# revital/cves: evaluacion KEV/NVD y reporte final (rama `reglas-cisa-cves`)

Contexto completo de la rama, con diagrama: [`CONTEXTO.md`](CONTEXTO.md).

Lee los `inventario-*.json` de los colectores (web, red, codigo, host), busca que CVE afectan cada version, marca los que estan en CISA KEV, los prioriza y escribe el reporte final por entidad.

```
python -m revital.cves --demo                 # caso portal-muni-gt, sin red: debe terminar en "ok"
python -m revital.cves --out salida           # lee salida/inventario-*.json -> salida/reporte-<entidad>.md
python -m revital.cves --out salida --entidad MUNI-GT
python -m revital.cves --actualizar           # opcional: NVD completo de alias.json a datos/ (internet)
python tests/test_cves.py                     # pruebas
```

Salida: `reporte-<entidad>.md` (para el jefe de TI) y `hallazgos-<entidad>.json` (todo el detalle).

| Archivo | Que hace |
|---|---|
| `versiones.py` | Compara versiones como numeros ('10.0' > '9.9', '1.3.3c' > '1.3.3') y revisa rangos de NVD |
| `normalizar.py` + `alias.json` | Nombre del colector ('Apache', 'Microsoft-IIS') -> CPE de NVD; ramas fuera de soporte |
| `catalogo.py` | Lee los catalogos del equipo en `catalogos/` (KEV + NVD de KEV) y el extra opcional de `datos/` |
| `evaluar.py` + `reglas.json` | Une componentes, cruza con NVD/KEV y asigna prioridad; CVE que dependen de configuracion |
| `reporte.py` | Escribe el `.md` y el `.json` |

Prioridad: 1 KEV + ransomware, 2 KEV con fecha limite vencida, 3 KEV, 4 CVSS >= 9, 5 CVSS >= 7, 6 resto. Los CVE de `reglas.json > condicionales` van aparte como "verificar". Una version incompleta ('Drupal 7') solo genera "posibles" y solo de KEV.

Para soportar un producto nuevo: agregarlo en `alias.json` (nombres que usan los colectores + CPE de NVD) y correr `--actualizar`.
