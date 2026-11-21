# Archivos locales del panel (sin internet)

| Archivo | Qué es | Licencia |
|---|---|---|
| `gsap.min.js` | GSAP 3.15.1 (animaciones). Bajado con `npm install gsap` | Standard "no charge" license de GSAP: https://gsap.com/standard-license |
| `instrument-sans-latin-*.woff2` | Tipografía Instrument Sans 400/500/600/700 (`@fontsource/instrument-sans`) | SIL Open Font License 1.1 (`LICENSE-instrument-sans.txt`) |
| `panel.js` | Pantalla de carga, animaciones de las gráficas y recarga automática | del proyecto |

El JavaScript es opcional: si el navegador no lo ejecuta (equipos muy viejos), el panel funciona igual, sin animaciones.
El servidor solo entrega archivos de esta carpeta con extensión `.js`, `.woff2` o `.txt` (ruta `/static/<archivo>`).
