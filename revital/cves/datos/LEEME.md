# Catalogos offline (datos reales)

Aqui van los catalogos que usa `python -m revital.cves`. Si esta carpeta esta vacia, se usan los de `../ejemplos/` y el reporte lo avisa.

| Archivo | Que es | Como se obtiene |
|---|---|---|
| `kev.json` | Catalogo completo de CISA KEV | `python -m revital.cves --actualizar`, o abrir <https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json> en el navegador y guardarlo (Ctrl+S) con este nombre |
| `nvd_min.json` | Extracto de NVD solo con los productos de `alias.json` | `python -m revital.cves --actualizar` (tarda: NVD limita las consultas; con la variable `NVD_API_KEY` va mas rapido) |
| `nvd_CVE-....json` (opcional) | Respuesta cruda del API de NVD para un CVE | Abrir `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-AAAA-NNNN` y guardarlo aqui; se convierte solo |

`--actualizar` necesita internet: correrlo en una maquina con red y copiar esta carpeta (USB) al equipo sin red.
