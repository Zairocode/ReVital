# Rama `reglas-cisa-cves`: contexto

> Documento de la rama `reglas-cisa-cves` (carpeta `revital/cves/`). Explica qué hace, por qué está hecha así y cómo encaja con el resto de ReVital.
> Contexto general del proyecto: [`docs/ReVital-explicado.md`](../../docs/ReVital-explicado.md). Uso rápido: [`LEEME.md`](LEEME.md).
> Si este documento y el código no coinciden, manda el código.

---

## 1. Qué hace, en una frase

**Toma lo que encontraron los colectores ("hay Apache 2.4.49 y Drupal 7.57"), averigua qué vulnerabilidades tiene cada versión, marca las que se están explotando en el mundo real (CISA KEV) y escribe el reporte final por entidad con lo que hay que parchear primero.**

Los colectores responden *"¿qué tengo?"*. Esta rama responde *"¿qué arreglo primero y por qué?"*.

---

## 2. Diagrama

```mermaid
flowchart TD
    subgraph COL["Colectores (otras ramas)"]
        W["web<br/>rama crawler"]
        R["red<br/>rama crawler"]
        K["codigo<br/>rama directorios"]
        H["host<br/>rama adaptaciones-windows"]
    end
    W --> I[("salida/inventario-*.json<br/>contrato de inventory.py")]
    R --> I
    K --> I
    H --> I

    subgraph NET["Con internet, una vez (congelado en el repo)"]
        CISA["CISA KEV<br/>JSON público"] --> DK[("catalogos/kev.json")]
        NVDAPI["NVD API 2.0<br/>CVE que están en KEV"] --> DN[("catalogos/nvd-kev.json")]
        NVDX["NVD API 2.0, opcional<br/>todas las CVE de alias.json"] -.-> DX[("revital/cves/datos/nvd_min.json<br/>solo local")]
    end

    subgraph CVES["revital/cves (esta rama, sin internet)"]
        N["1. normalizar.py + alias.json<br/>'Apache' -> apache:http_server"]
        D["2. evaluar.py: une y limpia<br/>quita duplicados, 'Drupal 7' -> 7.57"]
        V["3. versiones.py<br/>¿la versión cae en el rango de NVD?"]
        KV["4. ¿El CVE está en KEV?"]
        P["5. Prioridad + reglas.json<br/>ransomware, fecha vencida, CVSS, condicionales"]
        E["Fin de soporte<br/>alias.json: eol"]
        C["Configuración insegura<br/>TLS viejo, alertas de colectores"]
    end

    I --> N --> D --> V --> KV --> P
    DN --> V
    DX -.-> V
    DK --> KV
    D --> E
    D --> C
    C --> MD
    P --> MD["salida/reporte-ENTIDAD.md<br/>para el jefe de TI"]
    E --> MD
    P --> JS["salida/hallazgos-ENTIDAD.json<br/>detalle completo"]
```

Versión texto (por si el visor no muestra Mermaid):

```
 colectores ──► salida/inventario-*.json
                        │
                        ▼
   1. normalizar   'Apache' / 'apache http_server' ──► apache:http_server   (alias.json)
   2. unir         mismo producto+versión de varias fuentes = 1 fila; 'Drupal 7' se descarta si se sabe 7.57
   3. versiones    ¿2.4.49 está dentro del rango afectado?        (catalogos/nvd-kev.json [+ datos/nvd_min.json])
   4. KEV          ¿ese CVE se está explotando?                    (catalogos/kev.json)
   5. prioridad    KEV+ransomware > KEV vencido > KEV > CVSS≥9 > CVSS≥7 > resto (reglas.json)
                        │
                        ▼
   salida/reporte-<entidad>.md  +  salida/hallazgos-<entidad>.json
```

---

## 3. Entrada: el contrato común

No leemos nada propio de cada colector. Solo el contrato de `revital/inventory.py`, que se carga con `inventory.cargar_todos("salida")`:

```json
{"kind": "web", "target": "http://localhost:8080", "entidad": "MUNI-GT",
 "components": [{"producto": "Apache", "version": "2.4.49", "fuente": "header server en error 400", "donde": "localhost:8080"}]}
```

- Se hace **un reporte por cada `entidad`** distinta que haya en `salida/`. Si varios colectores apuntan a la misma entidad (web + código + host), sus componentes se unen en un solo reporte.
- `fuente` y `donde` se conservan hasta el final como **evidencia**: el jurado puede preguntar "¿cómo sabes que es esa versión?".

---

## 4. Las fuentes de datos y por qué hacen falta las dos

| Fuente | Qué responde | Qué NO trae | Archivo |
|---|---|---|---|
| **CISA KEV** | Qué CVE se explotan activamente, si los usa ransomware, acción requerida y fecha límite | Qué versiones afecta | `catalogos/kev.json` |
| **NVD** (NIST), extracto KEV | Qué versiones afecta cada CVE de KEV (CPE + rangos) y su CVSS | Si se está explotando | `catalogos/nvd-kev.json` |
| **NVD** completo, opcional | Lo mismo para **todas** las CVE de los productos de `alias.json`, no solo KEV (sección 4 del reporte) | — | `revital/cves/datos/nvd_min.json` (local, no se sube) |

Los dos primeros los congeló el equipo en `catalogos/` con `python scripts/actualizar_catalogos.py` (ver `catalogos/LEEME.md`): son **la fuente oficial** y viajan con el repo. El tercero es un extra que cada quien genera con `python -m revital.cves --actualizar` si quiere ver también las CVE que no están en KEV; pesa unos 8 MB y por eso no se sube.

KEV dice "este CVE de Apache se explota" pero no dice "hasta qué versión". NVD dice "afecta hasta 2.4.48" pero no dice si es urgente. **Juntas responden "¿mi versión tiene algo que se esté explotando hoy?".**

**¿Por qué no una base de datos?** Restricción del proyecto: solo stdlib de Python 3.8, offline, en Windows 7. Son archivos JSON (unos 3 MB en `catalogos/`) que se cargan en memoria en menos de un segundo. Si algún día se quiere todo NVD, el siguiente paso es `sqlite3`, que también es stdlib.

**Offline:** los catálogos ya vienen en el repo (`catalogos/`), así que la demo no necesita internet. Si faltara `catalogos/kev.json`, se usan los catálogos reducidos de `ejemplos/` y el reporte lo avisa arriba.

---

## 5. Decisiones de diseño (y por qué)

| Decisión | Por qué |
|---|---|
| **Tabla de alias** (`alias.json`) en vez de adivinar nombres | Los colectores escriben "Apache", "Microsoft-IIS", "apache http_server"; NVD usa `apache:http_server`. El docs del equipo ya lo marcaba como la parte más difícil. Agregar un producto = editar JSON, no código. |
| **Versiones como números**, no texto | Como texto `"10.0" < "9.9"`. Además: `1.3.3c > 1.3.3` (ProFTPD, OpenSSL) y `7.5-beta < 7.5`. |
| **Versión incompleta = "posible"** | El meta generator dice "Drupal 7"; con eso no se puede confirmar nada. Si otra fuente dio 7.57, se usa esa y la evidencia de "Drupal 7" se une a la fila de 7.57. Si solo hay "7", se listan solo los KEV de la rama como "posibles". |
| **Sin versión = revisión manual** | No inventamos. Se dice cuántos KEV tiene el producto para que alguien lo revise a mano. |
| **CVE condicionales aparte** (`reglas.json`) | Algunos CVE solo aplican con cierta configuración que no se ve desde fuera (ej. CVE-2024-38475, reglas de mod_rewrite). Se reportan como "verificar", no como confirmados. |
| **Configuración insegura** separada de los CVE | `TLS 1.0` o un `web.config` en modo depuración no son software con CVE, pero son riesgos que se corrigen cambiando configuración, sin parche. Antes caían en "sin equivalencia en NVD". |
| **Fin de soporte (EOL)** separado de los CVE | Un Drupal 7 no recibirá más parches: la recomendación no es "parchar" sino "planificar migración". Importante para gobierno. |
| **Solo lectura** | Nunca se descargan ni ejecutan exploits; solo se leen catálogos públicos. |

---

## 6. Prioridad

| Nivel | Etiqueta | Regla |
|---|---|---|
| 1 | CRITICO | En KEV **y** `knownRansomwareCampaignUse = "Known"` |
| 2 | URGENTE (vencido) | En KEV y ya pasó la `dueDate` de CISA |
| 3 | URGENTE | En KEV |
| 4 | ALTO | No está en KEV, CVSS ≥ 9.0 |
| 5 | MEDIO | No está en KEV, CVSS ≥ 7.0 |
| 6 | BAJO | Resto |

Dentro de cada nivel se ordena por CVSS. Los umbrales están en `reglas.json`. Es la prioridad que propone `docs/ReVital-explicado.md` (sección 7.5).

---

## 7. Salida: el reporte final

`salida/reporte-<entidad>.md`, pensado para un jefe de TI:

1. **Resumen** con indicadores y estado de **cumplimiento** ("NO CUMPLE: N vulnerabilidades KEV sin parchear").
2. **Qué parchear primero:** solo KEV, con motivo, acción requerida por CISA, fecha límite y evidencia.
3. **Dependen de configuración** (verificar).
4. **Fuera de soporte** (planificar migración).
5. **Configuración insegura:** protocolos obsoletos que acepta el servidor (`TLS 1.0/1.1`, que reporta el crawler) y alertas de los colectores (ej. `web.config` con `debug=true` o `customErrors Off`, del colector de código), cada una con su recomendación (`reglas.json`).
6. **Otras vulnerabilidades** no KEV (las 20 más graves; el resto en el `.json`).
7. **Revisión manual:** sin versión, versión incompleta, productos sin alias y avisos de cobertura de los colectores.
8. **Inventario** completo con fuente y dónde, y el método usado.

`salida/hallazgos-<entidad>.json` trae todo el detalle, para un dashboard u otra herramienta.

---

## 8. Resultado con el caso de demo (portal-muni-gt)

Entrada: salida real del crawler contra el Docker de `casos/portal-muni-gt` (Drupal 7.57 detrás de un proxy Apache 2.4.49, backend Apache 2.4.10, PHP 7.0.28). Catálogos reales del equipo: **KEV versión 2026.11.20 (1,790 vulnerabilidades)**, en `catalogos/`. Entidad: `MUNI-GT`.

**4 componentes · 10 KEV abiertos (5 usados en ransomware) · 2 a verificar · 2 fuera de soporte**. Con el extra opcional de NVD completo (`--actualizar`) aparecen además 292 CVE conocidas que no están en KEV.

| Prioridad | CVE | Componente |
|---|---|---|
| CRITICO | CVE-2018-7600 (Drupalgeddon 2) | Drupal 7.57 |
| CRITICO | CVE-2018-7602 (Drupalgeddon 3) | Drupal 7.57 |
| CRITICO | CVE-2021-41773 | Apache 2.4.49 (proxy) |
| CRITICO | CVE-2021-42013 | Apache 2.4.49 (proxy) |
| CRITICO | CVE-2021-40438 | Apache 2.4.10 (backend) |
| URGENTE (vencido) | CVE-2020-13671 | Drupal 7.57 |
| URGENTE (vencido) | CVE-2026-109619 | PHP 7.0.28 (agregado a KEV el 26-oct-2026) |
| URGENTE (vencido) | CVE-2020-28949 | Drupal 7.57 (librería incluida) |
| URGENTE (vencido) | CVE-2020-36193 | Drupal 7.57 (librería incluida) |
| URGENTE (vencido) | CVE-2020-11023 | Drupal 7.57 (jQuery incluido) |

Fuera de soporte: Drupal 7 (desde 2025-01-05) y PHP 7.0 (desde 2019-01-10).

Para el pitch: **un sistema "que funciona" sigue acumulando vulnerabilidades explotadas**; la de PHP entró a KEV hace menos de un mes.

**Con el colector de código** (`revital/codigo.py`) sobre la carpeta de la app, los dos inventarios se unen en el mismo reporte de `MUNI-GT`. Probado con una app de prueba que declara `log4j-core 2.14.1` en su `pom.xml`: aparece **CVE-2021-44228 (Log4Shell)** como CRITICO, sin tocar código, solo por el alias.

### Diferencias encontradas con `casos/portal-muni-gt` (para quien mantiene el caso)
- **CVE-2021-42013** sí aplica a 2.4.49, no "solo si 2.4.50": NVD lista 2.4.49 y 2.4.50.
- **CVE-2019-6340** no aplica: NVD solo lista Drupal 8.5.x y 8.6.x.
- **CVE-2024-38475** también toca al proxy 2.4.49 (afecta a 2.4.0 hasta antes de 2.4.60), no solo al backend.
- KEV real agrega **CVE-2018-7602** y **CVE-2021-40438** como críticos, que el caso no listaba.

---

## 9. Cómo se usa

```
python -m revital.cves --demo                 # caso de ejemplo, sin red; termina en "ok"
python -m revital.cves --out salida           # lee salida/inventario-*.json -> salida/reporte-<entidad>.md
python -m revital.cves --out salida --entidad MUNI-GT
python -m revital.cves --actualizar           # opcional: NVD completo de los productos de alias.json a datos/ (internet, minutos)
python scripts/actualizar_catalogos.py        # KEV + extracto NVD oficiales en catalogos/ (script del equipo)
python -m revital.cves --actualizar --productos php,drupal   # solo algunos productos
python tests/test_cves.py                     # pruebas (sin pytest)
```

`--demo` siempre usa los catálogos de `ejemplos/`, a propósito, para que la prueba dé siempre el mismo resultado. Con `NVD_API_KEY` en el entorno, `--actualizar` va más rápido.

---

## 10. Archivos

| Archivo | Qué hace |
|---|---|
| `__main__.py` | Línea de comandos: `--demo`, `--out`, `--entidad`, `--actualizar` |
| `normalizar.py` + `alias.json` | Nombre del colector → CPE de NVD; ramas fuera de soporte |
| `versiones.py` | Comparación de versiones y rangos de NVD |
| `catalogo.py` | Lee `catalogos/` (KEV + `nvd-kev.json`) y el extra de `datos/`; convierte formatos de NVD; `--actualizar` |
| `evaluar.py` + `reglas.json` | Une componentes, cruza, prioriza; CVE condicionales y umbrales |
| `reporte.py` | Escribe el `.md` y el `.json` |
| `ejemplos/` | Inventario real del crawler (caso Drupal) + KEV y NVD reducidos |
| `datos/` | Extra local opcional `nvd_min.json` (lo llena `--actualizar`; no se sube al repo) |
| `../../tests/test_cves.py` | Pruebas: versiones, alias, conversión de NVD, caso Drupal completo |

---

## 11. Cómo extenderlo

- **Nuevo producto:** agregarlo a `alias.json` con los nombres que usan los colectores y su CPE de NVD (se busca en <https://nvd.nist.gov/products/cpe/search>), después `--actualizar --productos <nombre>`.
- **Nuevo CVE condicional:** agregarlo a `reglas.json > condicionales` con el texto de qué verificar.
- **Coordinación con los colectores:** si un colector emite un nombre nuevo, aparece en el reporte bajo "Sin equivalencia en NVD"; ahí se ve qué falta en `alias.json`.

---

## 12. Pendiente

- [ ] **Exploit-DB** como señal extra: "no está en KEV pero hay exploit público" como nivel entre KEV y CVSS. Se usaría su índice CSV offline; nunca se descargan exploits.
- [ ] Ampliar `alias.json` con lo que emitan los colectores `codigo` (pom.xml, composer.json, DLLs) y `host` (software instalado en Windows).
- [ ] EPSS (probabilidad de explotación, de FIRST) como desempate dentro de un mismo nivel.
- [x] Catálogos offline en el repo: resuelto por el equipo en `catalogos/` (PR #7). Esta rama los usa como fuente principal.
- [ ] Probar con Python 3.8 en Windows 7 real antes de la demo.

---

## 13. Limitaciones (dicho con honestidad)

- **Depende de que el colector detecte bien la versión.** Si la versión es falsa o está oculta, el resultado también lo estará; por eso cada hallazgo trae su evidencia.
- **Backports:** algunas distribuciones parchean sin cambiar el número de versión. Un hallazgo "confirmado" significa "la versión reportada está en el rango afectado", no "se explotó con éxito".
- **CVE que dependen de configuración** no se pueden confirmar desde fuera; van en su propia sección.
- **Los nombres de NVD cambian** (ej. nginx pasó de `nginx:nginx` a `f5:nginx`); `alias.json` admite varios CPE por producto por eso.
