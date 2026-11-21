# MuniSoke GT · Portada 3D (Caso ReVital `MUNI-GT`)

Portada estática, 100 % offline y sin paso de compilación del portal municipal ficticio **MuniSoke GT** (*Municipalidad de Soke*, objetivo vulnerable del demo de ReVital). Combina una escena 3D procedural del altiplano volcánico guatemalteco en **Three.js** con animaciones sobrias en **GSAP + ScrollTrigger**, preparada en regiones semánticas listas para integrarse más adelante como tema de **Drupal 7**.

> **Aviso:** Portal ficticio de demostración. No representa a ninguna municipalidad ni institución real.

---

## Cómo servirlo localmente (100 % offline)

Desde esta carpeta (`casos/portal-muni-gt/branding-3d/`):

```bash
python3 -m http.server 8080
```

Luego abre en el navegador:

```text
http://localhost:8080/
```

Para probar los trámites de SIREC en local sin levantar Tomcat/Apache, agrega `?mock=1`:

```text
http://localhost:8080/?mock=1
```

Sin `?mock=1`, el portal consume el backend real en el mismo origen a través de rutas relativas `/sirec/api/...` (sin cargar `js/sirec-mock.js`).

No requiere `npm install`, bundler ni conexión a internet: todas las dependencias y tipografías viven en `vendor/` y `fonts/`.

---

## Qué hace cada archivo y carpeta

- `index.html` — Documento principal en bloques/regiones claros (`demo-banner`, `util`, `header`, `nav`, `hero`, `servicios`, `cifras`, `noticias`, `transparencia`, `footer`), con `<script type="importmap">` local, ilustración SVG de respaldo para el hero y favicon SVG en línea.
- `base-corregida.html` — Maqueta original de referencia conservada intacta.
- `css/fonts.css` — Declaraciones `@font-face` locales para `Archivo` e `Inter` (fuentes variables WOFF2, `font-display: swap`).
- `css/styles.css` — Sistema de tokens institucionales (claro/oscuro con contraste WCAG 2.2 AA), diseño responsive (`360px` / `768px` / `1366px`), foco visible y soporte de `prefers-reduced-motion: reduce`.
- `css/sirec.css` — Estilos dedicados del módulo de trámites SIREC (barra de estado, pestañas accesibles, formularios, tarjetas de resultado, insignias de estado, tabla de trimestres y vista de impresión `@media print` para la orden de pago).
- `js/main.js` — Orquestador de módulos: selector de tema claro/oscuro (`localStorage` + `prefers-color-scheme`), menú móvil accesible, buscador demostrativo con región `aria-live`, integración progresiva de SIREC e inicialización de Three.js y GSAP.
- `js/sirec.js` — Integración ES module con los endpoints `/sirec/api/*` (estado, consulta IUSI, orden de pago, solicitud LAIP y seguimiento por folio), validación accesible de formularios, construcción segura del DOM sin `innerHTML`, formato de quetzales y tolerancia a páginas internas de Drupal sin `#tramites`.
- `js/sirec-mock.js` — Simulador offline del contrato de SIREC con los datos semilla garantizados (`F-1024`, `F-2048`, `F-3072`, `F-0000`, `LAIP-2026-0101`, `LAIP-2026-0140`, etc.), importado dinámicamente solo cuando la URL incluye `?mock=1`.
- `js/scene-3d.js` — Escena 3D procedural en Three.js (cadena de volcanes low-poly, sol dorado, niebla atmosférica y ciudad municipal de Soke con Palacio y Parque Central). Limita `devicePixelRatio <= 2`, pausa el render fuera de viewport o con pestaña oculta, aplica parallax sutil, reacciona al cambio de tema, respeta `prefers-reduced-motion` (1 solo frame estático) y cae limpiamente al SVG si no hay WebGL2.
- `js/animations.js` — Coreografía en GSAP + ScrollTrigger (entrada del hero, revelado por sección, contadores de cifras y microinteracciones sutiles) animando solo `transform` y `opacity`, completamente desactivada bajo `prefers-reduced-motion: reduce`.
- `vendor/three/` — Distribución ES module de Three.js v0.187.0 (`three.module.js`, `three.core.js`) + `LICENSE` (MIT).
- `vendor/gsap/` — Módulos ESM estrictamente necesarios de GSAP v3.15.1 (`index.js`, `gsap-core.js`, `CSSPlugin.js`, `ScrollTrigger.js`, `Observer.js`) + `LICENSE`.
- `fonts/` — Tipografías variables locales `Archivo` e `Inter` (`*.woff2`) + sus licencias SIL OFL (`LICENSE-archivo.txt`, `LICENSE-inter.txt`).
- `DISENO.md` — Dirección visual: concepto cívico-editorial, paleta y contraste, tipografía, ritmo espacial, regiones Drupal 7 y principios de movimiento.
- `QA.md` — Reporte de auditoría real en Chromium headless: accesibilidad WCAG 2.2 AA (claro/oscuro), responsive `360`/`768`/`1366`, WebGL y fallback, `prefers-reduced-motion`, rendimiento (LCP/CLS), red offline y hallazgos corregidos.
