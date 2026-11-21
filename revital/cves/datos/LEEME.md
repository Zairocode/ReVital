# Extra local opcional (no se sube al repo)

La fuente oficial de catalogos es `catalogos/` en la raiz del repo (KEV completo + NVD de las CVE de KEV; ver `catalogos/LEEME.md`). Con eso basta para la demo.

Esta carpeta es para un **extra local**: NVD de **todas** las CVE (no solo KEV) de los productos de `alias.json`, para llenar la seccion "Otras vulnerabilidades" del reporte.

| Archivo | Como se obtiene |
|---|---|
| `nvd_min.json` | `python -m revital.cves --actualizar` (internet; unos minutos; con `NVD_API_KEY` va mas rapido) |
| `nvd_CVE-....json` | Abrir `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-AAAA-NNNN` en el navegador y guardarlo aqui; se convierte solo |

Los `.json` de esta carpeta estan en `.gitignore` (pesan varios MB y cada quien los genera).
