# Catálogos congelados (offline)

Descargados el 2026-11-21 con `python scripts/actualizar_catalogos.py` (KEV 2026.11.20). **La demo no necesita internet:** todo se lee de aquí.

| Archivo | Qué es |
|---|---|
| `kev.json` | Catálogo CISA KEV completo (1790 CVE): `cveID`, `vendorProject`, `product`, `dateAdded`, `dueDate`, `requiredAction`, `knownRansomwareCampaignUse`… |
| `nvd-kev.json` | Extracto de NVD solo de las CVE en KEV (los datos que KEV no trae: CVSS y versiones afectadas) |

## Formato de `nvd-kev.json`
```json
{"descargado": "2026-11-21", "kev_catalogVersion": "2026.11.20", "total": 1790, "sin_datos_nvd": [],
 "cves": {"CVE-2018-7600": {"cvss": 9.8, "cpes": [
    ["drupal", "drupal", "*", "", "", "7.57", ""],
    ["drupal", "drupal", "*", "8.0.0", "", "", "8.3.9"] ]}}}
```
Cada `cpe` = `[vendor, producto, versión, startIncluding, startExcluding, endIncluding, endExcluding]`.
`versión` es exacta (`"2.4.49"`) o `"*"` cuando el rango viene en los otros campos (`""` = sin límite).
Ejemplo: `["apache","http_server","2.4.49","","","",""]` = solo Apache 2.4.49; `["drupal","drupal","*","","","7.57",""]` = Drupal ≤ 7.57.

## Cruzar un componente del inventario
1. Alias: `producto` del inventario → `(vendor, producto)` de NVD (`Apache` → `apache`,`http_server`; `Drupal` → `drupal`,`drupal`).
2. Para cada CVE, ¿algún `cpe` con ese par cuya versión coincide o cae en el rango?
3. Si sí → buscar la CVE en `kev.json` para `requiredAction`, `dueDate` y ransomware.

## Actualizar / verificar
```
python scripts/actualizar_catalogos.py          # con internet, ~15 s (clave NVD opcional en NVD_API_KEY)
python scripts/actualizar_catalogos.py --check  # sin internet: versión y fecha de lo congelado
python tests/test_catalogos.py                  # comprueba que cubren el caso de demo, sin tocar la red
```
Límite: solo cubre lo que **ya se explota** (KEV). Una CVE que no esté en KEV no aparece, a propósito.
