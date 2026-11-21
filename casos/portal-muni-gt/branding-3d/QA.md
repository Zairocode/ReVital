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
