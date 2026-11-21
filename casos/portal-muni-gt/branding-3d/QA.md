# Reporte de QA · MuniSoke GT (`branding-3d`)

> **Caso ReVital · MUNI-GT** — Auditoría real y reproducible ejecutada en Chromium headless real (`chromium-1254`, ANGLE SwiftShader WebGL2) mediante Chrome DevTools Protocol (CDP) sobre servidor local `python3 -m http.server`.
>
> **Estado final:** **APROBADO (PASS)** tras detectar, corregir y re-verificar **5 defectos reales**.

---

## 1. Entorno y metodología de verificación

- **Servidor local:** `python3 -m http.server --bind 127.0.0.1` sirviendo exclusivamente `casos/portal-muni-gt/branding-3d/`.
- **Navegador real:** Chromium headless (`/home/phobos/.cache/ms-playwright/chromium-1254/chrome-linux64/chrome`) con flags `--headless=new --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`.
- **Automatización y telemetría:** Script Node.js v24.18.0 conectado vía WebSocket nativo al protocolo CDP (`Network`, `Runtime`, `Log`, `Page`, `Emulation`, `Input`).
- **Escenarios ejecutados:**
  1. **Desktop `1366×900`** (modo claro y modo oscuro, DPR=1 y emulación DPR=3, scroll completo, navegación por teclado y buscador).
  2. **Tablet `768×1024`** (modo claro y modo oscuro).
  3. **Móvil `360×800`** (modo claro, modo oscuro, menú móvil abierto/cierre con `Escape` y auditoría de tap targets).
  4. **Simulación sin WebGL** (`HTMLCanvasElement.prototype.getContext = () => null` inyectado antes de cargar la página).
  5. **`prefers-reduced-motion: reduce`** emulado vía `Emulation.setEmulatedMedia`.
- **Inspección visual directa:** Capturas PNG reales revisadas en `1366px` (claro, oscuro, página completa y sin WebGL), `768px` y `360px` (cerrado y menú abierto).

---

## 2. Defectos encontrados y corregidos

Durante la primera corrida de auditoría se detectaron **5 defectos reales** que fueron corregidos y re-verificados:

| # | Severidad | Defecto detectado | Archivo modificado | Corrección aplicada y re-verificación |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Media | **HTTP 404 en `/favicon.ico`** generando un error en `Log.entryAdded` (`Failed to load resource: 404`). | `index.html` | Se añadió `<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,...">` con el escudo SVG de MuniSoke GT. Resultado: **15/15 peticiones HTTP 200** y **0 errores de red/log**. |
| 2 | Media | **`#inicio` no recibía `is-webgl-ready` ni `is-webgl-failed`**: `main.js` resolvía el contenedor como `.hero-stage` en lugar de `<section id="inicio" class="hero">`. | `js/main.js` | Se priorizó `canvas?.closest('.hero') \|\| document.getElementById('inicio')`. Resultado: `#inicio` recibe `is-webgl-ready` con WebGL activo y `is-webgl-failed` cuando WebGL falla. |
| 3 | Alta (Visual) | **Ícono luna/sol desaparecía en `#theme-toggle` a `360px`**: al encogerse `.util-tools` en móvil, el SVG colapsaba a `width: 0px` (`height: 16px`) dejando espacio en blanco a la izquierda del texto. Además `svg.hidden = ...` no reflejaba el atributo HTML `hidden` en `SVGElement`. | `css/styles.css`, `js/main.js` | Se añadió `flex: 0 0 auto` a `.theme-toggle` y `flex: 0 0 auto; width: 16px; height: 16px` a `.theme-toggle svg` (y `toggleAttribute('hidden', ...)` en `main.js`). Re-verificado visualmente y por geometría: `16×16 px` en claro y oscuro a `360px`. |
| 4 | Media | **Cambio dinámico de `devicePixelRatio` no re-escalaba el canvas WebGL**: `window.addEventListener('resize', updateSize)` solo se registraba en el `else` cuando no existía `ResizeObserver`, por lo que al cambiar DPR de `1` a `3` sin variar CSS width/height el buffer quedaba en `1×`. | `js/scene-3d.js` | Se registra `window.addEventListener('resize', updateSize, { passive: true })` junto con `ResizeObserver` (y se limpia en `destroy()`). Con emulación DPR=3, el canvas re-escala exactamente a `2702×1210` (`effectiveRatio = 2.0 <= 2`). |
| 5 | Media (A11y) | **Anillo de foco recortado/tenue en `.srch`**: `.srch` tenía `overflow: hidden` y recortaba el `outline` de `.srch button:focus-visible`, mientras `.srch:focus-within` usaba una sombra tenue al 25 % de opacidad. | `css/styles.css` | Se aplicó `outline: 3px solid var(--focus-ring); outline-offset: 2px;` en `.srch:focus-within` y foco interior de alto contraste (`outline: 3px solid var(--focus-ring-dark-bg); outline-offset: -3px;`) en `.srch button:focus-visible`. |

---

## 3. Resultados verificados por categoría

### 3.1. 100 % Offline, Red y Tipografías Locales — **PASS**

- **Peticiones HTTP totales:** `15` (todas servidas desde `http://127.0.0.1:<puerto>/`).
- **Llamadas externas / CDNs:** `0`.
- **Peticiones con estado != 200 o fallidas:** `0`.
- **Recursos cargados con HTTP 200:**
  - `/index.html`, `/css/fonts.css`, `/css/styles.css`
  - `/js/main.js`, `/js/scene-3d.js`, `/js/animations.js`
  - `/vendor/three/three.module.js`, `/vendor/three/three.core.js`
  - `/vendor/gsap/index.js`, `/vendor/gsap/gsap-core.js`, `/vendor/gsap/CSSPlugin.js`, `/vendor/gsap/ScrollTrigger.js`, `/vendor/gsap/Observer.js`
  - `/fonts/archivo-latin-wght-normal.woff2`, `/fonts/inter-latin-wght-normal.woff2`
- **Fuentes (`document.fonts`):**
  - `Archivo` (`weight: 100 900`, `status: loaded`)
  - `Inter` (`weight: 100 900`, `status: loaded`)

### 3.2. Cero errores de consola y runtime — **PASS**

| Escenario | `console.error` / `warn` | `Runtime.exceptionThrown` | `Log.entryAdded` (error/warn) |
| :--- | :---: | :---: | :---: |
| Desktop / Tablet / Móvil (claro + oscuro) | **0** | **0** | **0** |
| Simulación sin WebGL (`getContext => null`) | **0** | **0** | **0** |
| `prefers-reduced-motion: reduce` | **0** | **0** | **0** |

### 3.3. Escena 3D (Three.js), DPR <= 2, Pausa y Fallback sin WebGL — **PASS**

- **WebGL activo (SwiftShader):**
  - `#inicio` contiene clases `["hero", "is-webgl-ready"]`.
  - `#hero-3d-canvas`: dimensiones visibles `1351×605 px`, `opacity: 1`.
  - **Límite `devicePixelRatio <= 2`:** emulando `window.devicePixelRatio = 3` vía CDP, el buffer de dibujo se ajusta exactamente a `2702×1210 px` (`effectiveRatioX = 2.0`, `effectiveRatioY = 2.0`).
  - **Reactividad al tema:** al pulsar `#theme-toggle`, la escena transiciona de cielo azul diurno con sol dorado a cielo nocturno azul profundo con iluminación cálida en el Palacio Municipal y ventanas encendidas (verificado visualmente en `desktop-1366-light.png` vs `desktop-1366-dark.png`).
  - **Pausa automática fuera de viewport:** instrumentando `requestAnimationFrame` por origen de stack, `js/scene-3d.js` registra **18 frames en 600 ms** con el hero visible y **0 frames en 700 ms** tras hacer scroll a `#contacto`.
- **Simulación sin WebGL (`getContext => null`):**
  - `#inicio` recibe `["hero", "is-webgl-failed"]`.
  - `#hero-3d-canvas` pasa a `display: none`.
  - `.hero-fallback-svg` permanece visible e intacto (`1351×605 px`) con **0 errores** en consola o runtime.

### 3.4. Animaciones GSAP y `prefers-reduced-motion: reduce` — **PASS**

- **Modo normal (`prefers-reduced-motion: no-preference`):**
  - Tras recorrer `#servicios`, `#cifras`, `#noticias`, `#transparencia` y `#contacto`, los 4 contadores terminan exactamente en: **`12`**, **`340`**, **`24/7`**, **`10 días`**.
  - Los **27/27** elementos `[data-anim]` finalizan en `opacity: 1` y `transform: none` (`0` elementos atascados u ocultos).
- **Modo reducido (`prefers-reduced-motion: reduce`):**
  - `window.matchMedia('(prefers-reduced-motion: reduce)').matches === true`.
  - Sin hacer scroll, los 4 contadores muestran de inmediato **`12`**, **`340`**, **`24/7`**, **`10 días`**.
  - Los **27/27** elementos `[data-anim]` están inmediatamente en `opacity: 1` y `transform: none`.
  - `js/scene-3d.js` registra **0 llamadas `rAF` en 700 ms** (un único frame estático renderizado).

### 3.5. Accesibilidad WCAG 2.2 AA (Modo Claro y Modo Oscuro) — **PASS**

#### Contraste calculado con colores computados (`getComputedStyle` + luminancia relativa WCAG)

**50/50 verificaciones aprobadas en tema claro** (mínimo texto: **5.25:1**, mínimo UI: **3.75:1**) y **50/50 aprobadas en tema oscuro** (mínimo texto: **5.25:1**, mínimo UI: **3.97:1**).

| Elemento / Componente | Modo Claro (`fg` / `bg`) | Ratio Claro | Modo Oscuro (`fg` / `bg`) | Ratio Oscuro | Umbral |
| :--- | :--- | :---: | :--- | :---: | :---: |
| Cinta demo (`.demo-bar`) | `#2b1e00` / `#f6b11f` | **8.71:1** | `#2b1e00` / `#ffc53d` | **10.33:1** | >= 4.5:1 |
| Accesos rápidos (`.util-nav a`) | `#0a2a66` / `#f3f6fc` | **12.63:1** | `#8eb6ff` / `#14223b` | **7.78:1** | >= 4.5:1 |
| Buscador texto (`#search-input`) | `#0e1726` / `#ffffff` | **17.96:1** | `#f1f5fc` / `#101b30` | **15.72:1** | >= 4.5:1 |
| Buscador placeholder (`--text-muted`) | `#4b5a75` / `#ffffff` | **6.96:1** | `#98abc9` / `#101b30` | **7.37:1** | >= 4.5:1 |
| Botón buscar ícono (`.srch button`) | `#ffffff` / `#1452c9` | **6.82:1** | `#ffffff` / `#1452c9` | **6.82:1** | >= 3.0:1 |
| Toggle tema (`#theme-toggle`) | `#0e1726` / `#ffffff` | **17.96:1** | `#f1f5fc` / `#101b30` | **15.72:1** | >= 4.5:1 |
| Eyebrow cabecera (`.brand span`) | `#0d6e3e` / `#ffffff` | **6.33:1** | `#4ad08a` / `#101b30` | **8.74:1** | >= 4.5:1 |
| Marca `h1` (`.brand h1`) | `#0a2a66` / `#ffffff` | **13.67:1** | `#8eb6ff` / `#101b30` | **8.42:1** | >= 3.0:1 |
| Horario atención (`.office-copy span`) | `#4b5a75` / `#f3f6fc` | **6.43:1** | `#98abc9` / `#14223b` | **6.81:1** | >= 4.5:1 |
| Nav activa (`.nav-links a.is-active`) | `#0e1726` / `#9bd60d` | **10.28:1** | `#0e1726` / `#aee22a` | **11.73:1** | >= 4.5:1 |
| Nav enlace (extremos `#0a2a66` / `#1452c9`) | `#ffffff` / `#1452c9` | **6.82:1–13.67:1** | `#ffffff` / `#1452c9` | **6.82:1–13.67:1** | >= 4.5:1 |
| Hero etiqueta (`.hero-kick`) | `#0e1726` / `#9bd60d` | **10.28:1** | `#0e1726` / `#aee22a` | **11.73:1** | >= 4.5:1 |
| Hero título / lead (sobre scrim `#07183a`) | `#ffffff` / `#e2ecff` | **17.49:1 / 14.72:1** | `#ffffff` / `#e2ecff` | **17.49:1 / 14.72:1** | >= 3.0 / 4.5 |
| Hero CTA primario (`.btn-primary`) | `#2b1e00` / `#f6b11f` | **8.71:1** | `#2b1e00` / `#ffc53d` | **10.33:1** | >= 4.5:1 |
| Hero CTA secundario (`.btn-secondary`) | `#ffffff` / `#07183a` | **17.49:1** | `#ffffff` / `#07183a` | **17.49:1** | >= 4.5:1 |
| Servicios tarjeta título / descripción | `#0a2a66` / `#4b5a75` | **13.67:1 / 6.96:1** | `#8eb6ff` / `#98abc9` | **8.42:1 / 7.37:1** | >= 4.5:1 |
| Cifras valor (peor extremo `#0e6f40`) | `#ffffff` / `#0e6f40` | **6.24:1–13.67:1** | `#ffffff` / `#0e6f40` | **6.24:1–13.67:1** | >= 3.0:1 |
| Cifras etiqueta (peor extremo `#0e6f40`) | `#e2ecff` / `#0e6f40` | **5.25:1–11.51:1** | `#e2ecff` / `#0e6f40` | **5.25:1–11.51:1** | >= 4.5:1 |
| Noticias etiqueta (`.np .tag`) | `#ffffff` / `#0e7441` | **5.84:1** | `#ffffff` / `#0e7441` | **5.84:1** | >= 4.5:1 |
| Noticias título / cuerpo / enlace | `#0e1726` / `#4b5a75` / `#1147b3` | **17.96 / 6.96 / 8.15** | `#f1f5fc` / `#98abc9` / `#8eb6ff` | **15.72 / 7.37 / 8.42** | >= 4.5:1 |
| Transparencia eyebrow / enlace | `#0d6e3e` / `#0a2a66` | **5.85:1 / 13.67:1** | `#4ad08a` / `#8eb6ff` | **8.08:1 / 8.42:1** | >= 4.5:1 |
| Footer título / cuerpo / copyright | `#ffffff` / `#c4d2e8` / `#9eb0cf` | **18.84 / 12.32 / 8.58** | `#ffffff` / `#c4d2e8` / `#9eb0cf` | **19.81 / 12.95 / 9.02** | >= 4.5:1 |
| Borde controles (`--border-control`) | `#6c7f9e` / `#f3f6fc` | **3.75:1–4.06:1** | `#6680ab` / `#14223b` | **3.97:1–4.29:1** | >= 3.0:1 |
| Anillo `:focus-visible` (3 px) | `#1452c9` / `#ffffff` (`#ffc53d` en oscuro) | **6.30:1–11.94:1** | `#ffc53d` / `#14223b` | **8.66:1–12.55:1** | >= 3.0:1 |

#### Semántica, Teclado, ARIA y Fidelidad de Dominio

- **Skip-link:** Primer `Tab` enfoca `.skip-link` (`Saltar al contenido principal`) con `:focus-visible` (`3px solid #1452c9`); al pulsar `Enter`, el foco pasa a `MAIN#contenido-principal`.
- **Selector de tema (`#theme-toggle`):** alterna correctamente `aria-pressed` (`false` ↔ `true`), `aria-label` (`Cambiar a modo oscuro` ↔ `Cambiar a modo claro`) y `data-theme`.
- **Menú móvil (`#nav-toggle`):** en `360px` alterna `aria-expanded` (`false` ↔ `true`), despliega `#nav-links` sin desbordamiento, y al pulsar `Escape` cierra el menú y devuelve el foco a `#nav-toggle`.
- **Buscador (`#site-search`):** `#search-feedback` tiene `role="status"` y `aria-live="polite"`; anuncia búsqueda vacía, coincidencia (`"agua"` enfoca `agua-empasoke` y resalta `.is-search-match`) y sin resultados.
- **Landmarks:** `banner` (1), `navigation` (2, con `aria-label` distintos), `main` (1), `contentinfo` (1), `search` (1), `region` demo (1).
- **Jerarquía de headings:** `h1` único (`MuniSoke GT`), seguida por `h2` y `h3` sin saltos de nivel (13 encabezados totales).
- **SVGs e imágenes:** 35 SVGs totales, `0` sin etiquetado/ocultamiento correcto (34 decorativos con `aria-hidden="true"`, 1 escudo informativo con `role="img"` + `aria-label`). `0` imágenes sin `alt`.
- **Fidelidad institucional ficticia:** se conservan el plazo **LAIP = `10 días` (Art. 42)** y la **cinta amarilla de demostración** (`PORTAL DE DEMOSTRACIÓN · Municipalidad ficticia "MuniSoke GT" ... no es una institución real`).

### 3.6. Responsive real (`360px`, `768px`, `1366px`) — **PASS**

| Viewport | Tema / Estado | `scrollWidth` | `innerWidth` | Overflow horizontal |
| :--- | :--- | :---: | :---: | :---: |
| `1366×900` | Claro / Oscuro | `1351` / `1366` | `1366` | **0 px (No)** |
| `768×1024` | Claro / Oscuro | `753` / `753` | `768` | **0 px (No)** |
| `360×800` | Claro / Oscuro | `360` / `360` | `360` | **0 px (No)** |
| `360×800` | Menú móvil abierto | `360` | `360` | **0 px (No)** |

- **Tap targets en `360px`:** `0/35` controles visibles por debajo del mínimo WCAG 2.2 AA (SC 2.5.8, `24×24 px`).
- **Inspección visual:** Sin recortes, sin solapamientos y con contraste nítido sobre el escenario 3D gracias a `.hero-scrim` en los 3 viewports y ambos temas.

### 3.7. Rendimiento y peso en disco — **PASS**

#### Métricas Web Vitals reales (Chromium headless + SwiftShader CPU WebGL)

- **LCP (Largest Contentful Paint):** **`980 ms`** (`H2#hero-titulo`, `165,452 px²`) — **Bueno** (`< 2500 ms`).
- **CLS (Cumulative Layout Shift):** **`0.0033`** (carga fría) / **`0.001`** (carga tibia) — **Bueno** (`< 0.1`).
- **DOMContentLoaded / Load:** `386 ms / 411 ms` (tibia) · `1550 ms / 1562 ms` (fría con compilación inicial de shaders en SwiftShader).
- **Nota técnica sobre `rAF` en reposo:** `js/scene-3d.js` detiene completamente su bucle `requestAnimationFrame` (**0 frames**) al salir del viewport y en `prefers-reduced-motion: reduce`. Únicamente el ticker interno de la librería vendored GSAP (`vendor/gsap/gsap-core.js`) mantiene su heartbeat estándar sin coste de renderizado WebGL.

#### Peso total de `casos/portal-muni-gt/branding-3d/` (sin incluir este `QA.md`)

| Carpeta / Archivo | Tamaño (bytes) | Tamaño (KiB) |
| :--- | ---: | ---: |
| `vendor/three/` | 2,134,780 | 2,084.7 KiB |
| `vendor/gsap/` | 378,335 | 369.5 KiB |
| `fonts/` (Archivo + Inter WOFF2 + licencias) | 92,164 | 90.0 KiB |
| `js/` (`scene-3d.js`, `main.js`, `animations.js`) | 78,012 | 76.2 KiB |
| `index.html` | 36,105 | 35.3 KiB |
| `css/` (`styles.css`, `fonts.css`) | 31,098 | 30.4 KiB |
| `base-corregida.html` (referencia base) | 17,633 | 17.2 KiB |
| `DISENO.md` | 7,683 | 7.5 KiB |
| **Total** | **2,775,810** | **2,710.8 KiB (2.65 MiB)** |

---

## 4. Cómo reproducir la auditoría localmente

```bash
# 1. Servir el portal 100 % offline
cd /home/phobos/Hackaton/ReVital-frontend3d/casos/portal-muni-gt/branding-3d
python3 -m http.server 8080 --bind 127.0.0.1

# 2. Abrir http://127.0.0.1:8080/index.html en Chromium/Firefox DevTools:
#    - Pestaña Network: comprobar 15/15 peticiones HTTP 200 en 127.0.0.1 (0 externas).
#    - Pestaña Console: comprobar 0 errores y 0 warnings.
#    - Emular DPR=3, prefers-reduced-motion: reduce y viewports 360px / 768px / 1366px.
```

---

## 5. Auditoría de Integración Frontend SIREC (`#tramites`)

> **Fecha de verificación:** 2026-11-21 · **Contrato:** `docs/features/sirec-api.md`
> **Navegador real:** Chromium headless (`chromium-1254`, SwiftShader WebGL2) vía CDP en Node.js v24.18.0 sobre `python3 -m http.server --bind 127.0.0.1`
> **Resultado final:** **APROBADO — 96/96 aserciones PASS (100 %)** tras detectar, corregir y re-verificar **3 defectos reales** en `css/sirec.css` (verificados también mediante inspección visual de capturas en modo claro, oscuro, móvil `360px` y `@media print`).

### 5.1. Defectos detectados y corregidos en la auditoría SIREC

| # | Severidad | Defecto detectado | Archivo modificado | Corrección aplicada y re-verificación |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Media (Print) | **`#btn-orden-imprimir` mantenía `display: inline-flex` computado en `@media print`**: aunque su contenedor padre `.sirec-actions.no-print` se ocultaba (`display: none`), el botón no figuraba explícitamente en la regla de ocultamiento de impresión. Además, los hijos `<strong>` y `<span>` de `.sirec-voucher-print-head` quedaban en línea pegados entre sí. | `css/sirec.css` | Se añadió `#btn-orden-imprimir` explícitamente a la lista `display: none !important` en `@media print` y se formateó `.sirec-voucher-print-head strong/span` en bloque con contraste `#0a2a66` / `#25324a` sobre blanco. Verificado en emulación `media: 'print'` y captura PNG. |
| 2 | Alta (Visual) | **Etiquetas `.sirec-voucher-label` pegadas sin espacio a código y monto** (`Número de ordenOP-2026-004512` y `Monto a pagarQ 832.50`): la clase `.sirec-voucher-label` carecía de regla CSS en `css/sirec.css`. | `css/sirec.css` | Se estilizó `.sirec-voucher-label` como bloque tipográfico superior (`display: block`, `0.76rem`, mayúsculas, `margin-bottom: 4px`, `color: var(--text-muted)`) y `display: block` en `.sirec-voucher-code` / `.sirec-voucher-amount`. Contraste verificado: **6.96:1** (claro) y **7.56:1** (oscuro). |
| 3 | Media (Visual) | **Layout de `.sirec-saldo-box`, `<caption>` de tabla IUSI e íconos en `.sirec-state--error/success`**: el bloque de saldo ocupaba solo 1 de las 3 columnas del `<dl>`, la `<caption>` carecía de relleno/alineación y los íconos SVG de alerta/éxito se apilaban en columna sobre el texto. | `css/sirec.css` | Se aplicó `grid-column: 1 / -1` a `.sirec-dl .sirec-saldo-box`, tipografía/padding consistente a `.sirec-table caption` y `flex-direction: row; align-items: flex-start` a `.sirec-state--error` y `.sirec-state--success`. Re-verificado visualmente en claro, oscuro y `360px`. |

### 5.2. Escenarios funcionales verificados en modo mock (`/?mock=1`) — **PASS**

- **Indicador de estado SIREC (`GET /sirec/api/estado`):**
  - `#sirec-status` pasa a `data-status="online"` con texto `SIREC v3.2.1 en línea · MuniSoke GT (ficticia)` y badge `#sirec-mock-badge` (`Modo de prueba`) visible.
  - **0 peticiones reales a `/sirec/api/`** (`js/sirec-mock.js` cargado dinámicamente solo con `?mock=1`) y **0 errores** de consola, warnings, excepciones o red.
- **Consulta tu IUSI (`GET /sirec/api/iusi?finca=...`):**
  - Validación en navegador (vacío, `F-123`, `1024`): muestra `#iusi-finca-error` vinculado por `aria-describedby`, establece `aria-invalid="true"` y mueve el foco a `#iusi-finca`.
  - Semilla `F-1024`: dirección `4a avenida 7-21, zona 3, Soke`, propietario enmascarado `M**** L****`, valor fiscal `Q 185,000.00`, IUSI anual `Q 1,665.00`, 4 trimestres (2 `Pagado` + 2 `Pendiente` con color + ícono SVG + texto), saldo `Q 832.50` y botón `"Generar orden de pago del saldo"`.
  - Flujo directo desde IUSI a Orden: clic en `"Generar orden de pago del saldo"` activa `#tab-orden`, selecciona `iusi` + `F-1024` y genera automáticamente `OP-2026-004512` por `Q 832.50`, vence `2026-11-28`, `Agencias bancarias autorizadas (ficticio)`.
  - Semilla `F-2048`: 4 trimestres `Pagado`, saldo `Q 0.00`, mensaje de inmueble al día y **sin** botón de orden de pago.
  - Semilla `F-3072`: 3 trimestres `Vencido` (color + ícono SVG + texto) + 1 `Pendiente`, saldo `Q 2,160.00`.
  - Semilla `F-0000`: muestra el `mensaje` de error `404 finca_no_encontrada`.
  - Error directo `400 finca_invalida` verificado mediante `window.__munisoke.sirec.consultarIusi('F-123')`.
- **Orden de pago (`POST /sirec/api/orden-pago`):**
  - **0 campos de tarjeta** (`credit`, `card`, `cvv`, `tarjeta`) en el documento.
  - Cambio dinámico de etiqueta, `placeholder` y texto de ayuda de `#orden-referencia` para los 4 conceptos (`iusi`, `ornato`, `agua`, `multa`).
  - Validación con referencia inválida (`ornato` = `123`): error en `#orden-referencia-error` (`aria-describedby`), `aria-invalid="true"` y foco en `#orden-referencia`.
  - Emisión exitosa verificada para: `ornato` (`1001 47673 0101` → `Q 15.00`), `agua` (`A-10006` → `Q 605.56`) y `multa` (`PMT-2026-00101` → `Q 150.00`).
  - Errores del contrato verificados: `iusi` + `F-2048` (`400 sin_saldo`), `iusi` + `F-0000` y `agua` + `A-00000` (`404 referencia_no_encontrada`), y `400 concepto_invalido` vía `window.__munisoke.sirec.generarOrdenPago`.
  - **Impresión (`@media print` vía `Emulation.setEmulatedMedia({ media: 'print' })`):** `#orden-comprobante`, `.sirec-voucher-print-head` y `.demo-bar` visibles (`display !== 'none'`); `.site-nav`, `#inicio`, `#servicios`, `#cifras`, `#noticias`, `#transparencia`, `.site-footer`, `.sirec-tabs`, `.sirec-form` y `#btn-orden-imprimir` ocultos (`display === 'none'`).
- **Solicitud de información pública LAIP (`POST /sirec/api/laip`):**
  - Validación: envío vacío marca nombre y descripción (`aria-describedby`, `aria-invalid="true"`) y enfoca `#laip-nombre`; descripción `"hola"` (< 10 caracteres) actualiza `#laip-descripcion-count` (`4 / 2000 caracteres`), muestra `#laip-descripcion-error` y enfoca `#laip-descripcion`; correo `"no-es-correo"` muestra `#laip-correo-error` y enfoca `#laip-correo`.
  - Envío válido sin correo (`201` → `LAIP-2026-0153`, fecha `2026-11-21`, vence `2026-12-07`, estado `Recibida`) y con correo opcional (`201` → `LAIP-2026-0154`).
  - Clic en `"Consultar seguimiento de este folio"` activa `#tab-seguimiento` y consulta `LAIP-2026-0153` mostrando estado `Recibida` y `10 días hábiles restantes`.
- **Seguimiento LAIP (`GET /sirec/api/laip/:folio`):**
  - `LAIP-2026-0101` → `Resuelta` (SVG + texto) y `0 días`.
  - `LAIP-2026-0140` → `En trámite` (SVG + texto) y `6 días`.
  - `LAIP-2026-0120` → `Prorrogada` (SVG + texto) y `4 días`.
  - `LAIP-2026-9999` → `404 folio_no_encontrado` mostrando `mensaje`.
- **Conexión desde Hero, Tarjetas de Servicios y Transparencia:**
  - Hero `"Pagar un servicio"` → `#tab-orden`; `"Solicitar información"` → `#tab-laip`.
  - Tarjetas: `iusi` → `#tab-iusi`; `multas-pmt` → `#tab-orden` (`multa`); `agua-empasoke` → `#tab-orden` (`agua`); `boleto-ornato` → `#tab-orden` (`ornato`); `expedientes-web` → `#tab-seguimiento`; `licencias` → muestra `#sirec-notice` con aviso de gestión presencial.
  - Transparencia `"Solicitud de información pública"` → `#tab-laip`.
- **Estados de carga y `aria-live`:** durante la petición en curso, el botón submit queda `disabled`, `#iusi-resultado` (`aria-live="polite"`) pasa a `aria-busy="true"` con `.sirec-state--loading` y `.sirec-spinner`, y al completar vuelve a `aria-busy="false"` y rehabilita el botón.

### 5.3. Modo sin mock (`/` sin `?mock=1`, backend SIREC apagado) — **PASS**

- **No carga `js/sirec-mock.js`** (0 peticiones al módulo mock).
- Realiza `GET /sirec/api/estado` sobre el mismo origen (ruta relativa).
- `#sirec-status` transiciona a `data-status="offline"` con texto `"El sistema de recaudación no está disponible, intenta más tarde."`, `#sirec-status-retry` visible y `#sirec-mock-badge` oculto.
- Al consultar `F-1024` sin backend, muestra exactamente `"El sistema de recaudación no está disponible, intenta más tarde."`, sin datos inventados, sin pantalla vacía y con **0 excepciones JS no capturadas** (`Runtime.exceptionThrown === 0`).

### 5.4. WCAG 2.2 AA (claro/oscuro), Teclado, Responsive, Reduced Motion, Offline y Regresiones — **PASS**

#### Contraste computado WCAG en `#tramites` (`42/42` PASS claro · `42/42` PASS oscuro)

| Elemento `#tramites` | Claro (`fg` / `bg`) | Ratio Claro | Oscuro (`fg` / `bg`) | Ratio Oscuro | Umbral |
| :--- | :--- | :---: | :--- | :---: | :---: |
| Título (`#tit-tramites`) / Subtítulo | `#0a2a66` / `#4b5a75` sobre `#f3f6fc` | **12.63 / 6.43** | `#9cc0ff` / `#a9b8d3` sobre `#172238` | **8.62 / 7.93** | >= 3.0 / 4.5 |
| Estado SIREC `online` / `offline` | `#0a5a32` / `#b42318` sobre `#ffffff` | **8.33 / 6.57** | `#8ef0b9` / `#ff9b96` sobre `#1a263c` | **11.05 / 7.49** | >= 4.5:1 |
| Badge `#sirec-mock-badge` / Botón reintentar | `#734400`/`#fff4d6` · `#0a2a66`/`#f3f6fc` | **7.50 / 12.63** | `#ffd670`/`#3a2b0d` · `#9cc0ff`/`#172238` | **9.86 / 8.62** | >= 4.5:1 |
| Pestaña activa / inactiva | `#0a2a66`/`#ffffff` · `#25324a`/`#f3f6fc` | **13.67 / 11.87** | `#f3f6fc`/`#1a263c` · `#d3dcee`/`#172238` | **13.99 / 11.53** | >= 4.5:1 |
| Label / Hint / Input texto | `#0e1726` / `#4b5a75` / `#0e1726` | **17.96 / 6.96 / 17.96** | `#f3f6fc` / `#a9b8d3` / `#f3f6fc` | **13.99 / 7.56 / 15.73** | >= 4.5:1 |
| Input borde normal / borde error | `#6c7f9e` / `#c93126` sobre `#ffffff` | **4.06 / 5.32** | `#7189b3` / `#f06a62` sobre `#1a263c` | **4.28 / 5.01** | >= 3.0:1 |
| Error de campo (`#iusi-finca-error`) | `#b42318` / `#ffffff` | **6.57:1** | `#ff9b96` / `#1a263c` | **7.49:1** | >= 4.5:1 |
| Botón primario / deshabilitado / secundario | `#ffffff`/`#1452c9` · `#ffffff`/`#566885` · `#0a2a66`/`#ffffff` | **6.82 / 5.65 / 13.67** | `#ffffff`/`#1452c9` · `#dbe6fa`/`#344666` · `#9cc0ff`/`#22314d` | **6.82 / 7.55 / 7.06** | >= 4.5:1 |
| Tabla IUSI (`caption` / `th` / `td`) | `#0e1726` / `#0e1726` / `#25324a` | **17.96 / 16.59 / 12.85** | `#f3f6fc` / `#f3f6fc` / `#d3dcee` | **13.99 / 14.67 / 10.99** | >= 4.5:1 |
| Badges `pagado` / `resuelta` | `#0a5a32` / `#e4f6ec` | **7.41:1** | `#8ef0b9` / `#113524` | **9.83:1** | >= 4.5:1 |
| Badges `pendiente` / `en_tramite` | `#734400` / `#fff4d6` | **7.50:1** | `#ffd670` / `#3a2b0d` | **9.86:1** | >= 4.5:1 |
| Badge `vencido` | `#9a1c15` / `#fdeceb` | **7.20:1** | `#ffaba5` / `#3f1718` | **8.63:1** | >= 4.5:1 |
| Badge `recibida` | `#0a2a66` / `#e8f0fe` | **11.93:1** | `#b6d0ff` / `#172b52` | **8.95:1** | >= 4.5:1 |
| Badge `prorrogada` | `#4a2574` / `#f2ebfc` | **9.99:1** | `#d9baff` / `#2d1b47` | **9.14:1** | >= 4.5:1 |
| Comprobante orden (`label` / `código` / `monto` / `nota`) | `#4b5a75` / `#0a2a66` / `#0e1726` / `#25324a` | **6.96 / 13.67 / 17.96 / 11.87** | `#a9b8d3` / `#9cc0ff` / `#f3f6fc` / `#d3dcee` | **7.56 / 8.22 / 13.99 / 11.53** | >= 4.5 / 3.0 |

- **Teclado en `[role="tablist"]`:** `ArrowRight`, `ArrowLeft`, `Home` y `End` rotan correctamente el foco, `aria-selected="true"` y `tabindex="0"` / `"-1"`.
- **Semántica:** jerarquía `h1 -> h2 -> h3 -> h4` sin saltos (1 `h1` único), todos los SVGs decorativos con `aria-hidden="true"`, `0` imágenes sin `alt`, cinta amarilla de demostración y plazo LAIP `10 días (Art. 42)` intactos.
- **Responsive (`360×800`, `768×1024`, `1366×900` en claro y oscuro con resultados IUSI y Orden visibles):** `0 px` de overflow horizontal (`scrollWidth <= innerWidth`) y todos los tap targets visibles en `#tramites` cumplen ampliamente WCAG 2.2 AA (mínimo medido: **`147×46 px`**, >= `44 px` de altura).
- **`prefers-reduced-motion: reduce`:** emulado vía CDP → `.sirec-spinner` con `animation-name: none`, contadores inmediatamente en `12`, `340`, `24/7`, `10 días`, y **0 errores**.
- **100 % Offline:** `0` peticiones externas en red y `0` URLs externas en `index.html`, `css/` y `js/` (únicas coincidencias `http://`: el namespace estándar SVG `http://www.w3.org/2000/svg`).
- **Cero regresiones:** Hero 3D (`is-webgl-ready`), selector de tema claro/oscuro, menú móvil (`360px` + `Escape`) y buscador (`"agua"`) verificados sin errores.

### 5.5. Cómo reproducir la auditoría SIREC localmente

```bash
# 1. Servir el portal estático 100 % offline
cd /home/phobos/Hackaton/ReVital-frontend-sirec/casos/portal-muni-gt/branding-3d
python3 -m http.server 8080 --bind 127.0.0.1

# 2. Probar en modo mock (sin backend SIREC):
#    Abrir http://127.0.0.1:8080/?mock=1
#    - Estado online: SIREC v3.2.1 + badge "Modo de prueba" (0 peticiones /sirec/api/).
#    - IUSI: probar F-1024 (saldo Q 832.50 -> botón orden OP-2026-004512), F-2048 (al día),
#      F-3072 (Vencido Q 2,160.00), F-0000 (404) y formato inválido (F-123).
#    - Orden de pago: probar iusi/ornato (1001 47673 0101)/agua (A-10006)/multa (PMT-2026-00101)
#      y previsualizar impresión (Ctrl+P / DevTools Rendering -> Emulate CSS media type: print).
#    - LAIP: enviar solicitud (201 -> LAIP-2026-0153) y consultar seguimiento para
#      LAIP-2026-0101 (Resuelta), LAIP-2026-0140 (En trámite), LAIP-2026-0120 (Prorrogada) y LAIP-2026-9999 (404).

# 3. Probar en modo real sin backend (degradación limpia):
#    Abrir http://127.0.0.1:8080/ (sin ?mock=1)
#    - Confirmar en Network que NO se solicita js/sirec-mock.js y sí GET /sirec/api/estado.
#    - Confirmar barra en estado offline con botón Reintentar y mensaje claro al consultar F-1024.
```


## Ajuste posterior (revisión de integración, 2026-11-21)
Formatos de referencia alineados con SIREC real (`docs/features/sirec-api.md`): contador `A-#####`, boleta `PMT-2026-#####`, DPI enviado como `#### ##### ####`; ejemplos tomados de los datos semilla; finca al día → `400 sin_saldo`. Verificado contra el backend real, no solo con `?mock=1`.
