# Dirección Visual y Sistema de Diseño · MuniSoke GT

> **Caso ReVital · MUNI-GT** — Portal municipal ficticio de demostración para la **Municipalidad de Soke**. Implementación 100 % offline, accesible (WCAG 2.2 AA) y modularizada por regiones para migración a tema de Drupal 7.

---

## 1. Concepto visual: Cívico-Editorial del Altiplano

La identidad busca transmitir la serenidad, cercanía y solemnidad administrativa de un portal municipal guatemalteco contemporáneo:

- **Claridad de servicio público**: superficies limpias con elevación sutil, encabezados editoriales centrados y tarjetas de ventanilla digital inmediatamente escaneables.
- **Raíz territorial ficticia**: el paisaje del altiplano volcánico de Soke articula tanto el escudo heráldico como el escenario panorámico del hero (ilustración SVG de LCP inmediato + capa WebGL 3D progresiva), con líneas topográficas tenues y paleta inspirada en cielo profundo, bosque montano y luz solar dorada.
- **Sobriedad institucional**: cero estética de startup, neón o ciberseguridad; cada acento cromático cumple una función de señalización (navegación activa, llamada a la acción primaria, categoría editorial o aviso de demostración).
- **Iconografía vectorial 100 % SVG inline**: se eliminan emojis y símbolos Unicode fuera de Latin-1 para garantizar consistencia tipográfica en todos los sistemas operativos sin dependencias externas.

---

## 2. Paleta institucional, roles y contraste WCAG 2.2 AA

Se conserva la paleta oficial de cinco colores (`#0a2a66`, `#1452c9`, `#128a4e`, `#9bd60d`, `#f6b11f`) complementada con variantes oscurecidas donde el texto blanco lo requiere (p. ej. `#0e7441` en etiquetas verdes, ya que blanco sobre `#128a4e` marca 4.40:1).

| Rol | Tema Claro | Tema Oscuro | Contraste verificado |
| :--- | :--- | :--- | :--- |
| Fondo principal (`--bg`) | `#ffffff` | `#0b1322` | — |
| Superficie / Tarjeta (`--surface`) | `#ffffff` | `#101b30` | — |
| Panel alterno (`--surface-subtle`) | `#f3f6fc` | `#14223b` | — |
| Texto principal (`--text-strong`) | `#0e1726` | `#f1f5fc` | **17.96:1** (claro) / **16.99:1** (oscuro) |
| Cuerpo (`--text-body`) | `#25324a` | `#cdd8ec` | **12.85:1** (claro) / **11.98:1** (oscuro) |
| Texto secundario (`--text-muted`) | `#4b5a75` | `#98abc9` | **6.96:1** (claro) / **7.37:1** (oscuro) |
| Primario / Títulos (`--accent-primary`) | `#0a2a66` | `#8eb6ff` | **13.67:1** (claro) / **8.42:1** (oscuro) |
| Enlaces (`--accent-link`) | `#1147b3` | `#8eb6ff` | **8.15:1** (claro) / **8.42:1** (oscuro) |
| Verde tipográfico (`--accent-green-text`) | `#0d6e3e` | `#4ad08a` | **6.33:1** (claro) / **8.74:1** (oscuro) |
| Etiqueta verde (`.tag`) | `#ffffff` sobre `#0e7441` | `#ffffff` sobre `#0e7441` | **5.84:1** (ambos temas) |
| Cinta demo y CTA oro | `#2b1e00` sobre `#f6b11f` | `#2b1e00` sobre `#ffc53d` | **8.71:1** / **10.33:1** (tinta oscura fija) |
| Acento lima (`.hero-kick`, nav activa) | `#0e1726` sobre `#9bd60d` | `#0e1726` sobre `#aee22a` | **10.28:1** / **11.73:1** (tinta oscura fija) |
| Navegación azul y Hero | `#ffffff` / `#e2ecff` sobre `#0a2a66`–`#1452c9` | Fijo en ambos temas | **6.82:1 – 13.67:1** |
| Bordes de control (`--border-control`) | `#6c7f9e` | `#6680ab` | **4.06:1** / **4.29:1** (>= 3:1 UI) |
| Anillo de foco (`:focus-visible`, 3 px) | `#1452c9` (y `#ffc53d` en fondos oscuros) | `#ffc53d` | **6.82:1 – 10.89:1** (>= 3:1) |

- **Soporte dual de tema**: responde a `prefers-color-scheme: dark` y permite anulación explícita vía `:root[data-theme="dark"]` y `:root[data-theme="light"]` desde `#theme-toggle`.

---

## 3. Tipografía local y escala

Cargada 100 % offline desde `./css/fonts.css` (subconjunto Latin en WOFF2 variable):

- **`Archivo` (`--font-head`)**: títulos, marca, navegación, eyebrows, etiquetas, cifras (`font-variant-numeric: tabular-nums`) y botones. Aporta presencia cívica geométrica y compacta.
- **`Inter` (`--font-body`)**: párrafos, descripciones de servicios, buscador, listas LAIP y pie de página. Maximiza legibilidad en pantallas densas y móviles.

| Nivel | Elemento | Tamaño | Peso |
| :--- | :--- | :--- | :--- |
| Marca principal (`h1`) | `.brand h1` | `clamp(1.55rem, 2.6vw, 2.05rem)` | 900 |
| Titular Hero (`h2`) | `.hero-title` | `clamp(2.15rem, 5.2vw, 3.85rem)` | 900 |
| Títulos de sección (`h2`) | `.sec-title` | `clamp(1.55rem, 2.8vw, 2.15rem)` | 900 |
| Cifras clave | `.stat-val` | `clamp(2rem, 3.4vw, 2.75rem)` | 900 |
| Tarjetas y columnas (`h3`) | `.np h3`, `.footer-col h3` | `1rem – 1.14rem` | 800 |
| Cuerpo base | `body` | `1rem` (`line-height: 1.6`) | 400 |
| Eyebrows y etiquetas | `.eyebrow`, `.hero-kick` | `0.74rem – 0.78rem` (mayúsculas) | 800 |

La jerarquía semántica es estricta (`h1 → h2 → h3`, sin saltos a `h4`), asistida por encabezados `.sr-only` en la franja de cifras y el pie institucional.

---

## 4. Ritmo espacial y bloques preparados para Drupal 7

Contenedor maestro `.wrap` (`max-width: 1200px`, safe-area horizontal) con espaciado vertical fluido `--space-sec: clamp(56px, 7vw, 84px)` y rejillas responsivas sin desbordamiento horizontal en `360px`, `768px` y `1366px`.

Cada bloque está delimitado por comentarios `<!-- Region: ... -->` y atributos `data-region="..."` listos para mapearse a `page.tpl.php` en Drupal 7:

1. `demo-banner` — Aviso obligatorio de portal ficticio (`role="region"`).
2. `util` — Marca compacta, accesos rápidos, buscador `#site-search` con `role="status"` y selector `#theme-toggle`.
3. `header` — Escudo heráldico ficticio SVG, identidad `Municipalidad de Soke / MuniSoke GT` y horario de atención ciudadana.
4. `nav` — Barra azul fija (`position: sticky`) con botón móvil `#nav-toggle` en `<= 768px`.
5. `hero` — Escenario `min-height: clamp(470px, 62vh, 620px)` con fallback SVG inmediato, `#hero-3d-canvas`, `.hero-scrim` direccional y dos CTAs.
6. `servicios` — Cuadrícula de 6 servicios en línea (6 cols desktop / 3 tablet / 2 móvil) con enlaces semánticos `<a>` y atributo `data-service`.
7. `cifras` — Banda azul-verde con 4 indicadores institucionales (`data-count-to` / `data-count-static`).
8. `noticias` — 3 artículos editoriales con ilustraciones SVG, etiquetas y enlaces accesibles con contexto para lectores de pantalla.
9. `transparencia` — Listado de 6 obligaciones del Art. 10 LAIP (Decreto 57-2008) sobre superficie sutil diferenciada.
10. `footer` — Pie de 3 columnas (institución y dirección ficticia, servicios, enlaces) más franja de derechos.

---

## 5. Estrategia de animación y mejora progresiva

- **Qué se anima**:
  - **Escenario Hero (`#hero-3d-canvas`)**: transición suave de opacidad (`0 → 1` en `0.6s`) al recibir `.hero.is-webgl-ready`, superponiendo el paisaje volcánico 3D sobre la ilustración SVG base sin parpadeos ni bloqueo de LCP.
  - **Aparición coreografiada (`data-anim`)**: elementos de hero (`hero-item`), encabezados (`section-head`), tarjetas de servicio (`service-card`), cifras con conteo (`stat-item`), noticias (`news-card`) e ítems LAIP (`transp-item`) mediante GSAP/ScrollTrigger.
  - **Microinteracciones CSS**: elevación sobria (`-4px`, curva `--ease-civic`) y acento superior en tarjetas y botones.
- **Por qué**: refuerza la jerarquía de lectura y guía la mirada hacia los trámites ciudadanos sin distraer ni retrasar la interacción.
- **Progresividad y accesibilidad**:
  - Ningún elemento `[data-anim]` se oculta en CSS con `opacity: 0`; si JavaScript falla o se desactiva, el portal completo permanece visible y operativo.
  - `@media (prefers-reduced-motion: reduce)` desactiva transiciones, animaciones CSS y `scroll-behavior: smooth`.

## Ajuste de paleta: "Mediodía en el valle"

Tras la primera revisión se percibía demasiado oscuro (seguía el modo oscuro del sistema y el hero
era nocturno). Cambios:

- **Claro por defecto**, sin seguir `prefers-color-scheme`; el oscuro solo se activa con el botón
  ("Activar modo oscuro / claro") y se recuerda en `localStorage` (`munisoke-theme-v2`).
- **Hero diurno**: cielo celeste, niebla clara y tinta azul marino sobre un velo claro. El tema
  oscuro pasa a "atardecer" (cielo violeta/durazno, superficies `#131c2e`/`#1a263c`, menos negro).
- **Cifras** en franja clara con tinte azul→verde; **pie** en azul de marca `#0a2a66`.
- Se quitaron las etiquetas sobre los títulos de sección (el título ya lo dice).
- Contraste AA verificado en ambos temas sobre todo el texto visible.

---

## 6. Región `tramites` · Ventanilla de Trámites en Línea (SIREC)

Se incorporó la región modular `<!-- Region: tramites -->` (`#tramites`, `data-region="tramites"`) inmediatamente después de `#servicios` y antes de `#cifras`, junto con la hoja dedicada [`css/sirec.css`](./css/sirec.css), manteniendo el enfoque 100 % offline, la jerarquía estricta de encabezados (`h1 → h2 → h3 → h4`) y los mismos tokens de diseño de `css/styles.css`.

### 6.1 Arquitectura de 4 pestañas WAI-ARIA

El contenedor `.sirec-shell` agrupa los cuatro flujos ciudadanos del contrato SIREC bajo un patrón `role="tablist"` / `role="tab"` / `role="tabpanel"` (sin pagos con tarjeta en línea):

1. **Consulta tu IUSI (`#tab-iusi` → `#panel-iusi`)**: formulario por número de finca (`F-####` / `F-#####`), resumen del inmueble en lista de definición (`.sirec-dl`), tabla responsiva de trimestres (`.sirec-table-wrap` + `.sirec-table` con montos `tabular-nums`) y caja de saldo pendiente (`.sirec-saldo-box`).
2. **Orden de pago (`#tab-orden` → `#panel-orden`)**: selector de concepto (`iusi`, `ornato`, `agua`, `multa`) y referencia dinámica para emitir una boleta pagadera únicamente en agencias bancarias autorizadas (`.sirec-voucher`).
3. **Solicitud LAIP (`#tab-laip` → `#panel-laip`)**: formulario conforme al Decreto 57-2008 (Art. 42, plazo de 10 días) con nombre obligatorio, correo opcional y descripción con contador en vivo (`10–2,000` caracteres).
4. **Seguimiento LAIP (`#tab-seguimiento` → `#panel-seguimiento`)**: consulta por folio (p. ej. `LAIP-2026-0140`) mostrando estado y días restantes.

En escritorio las pestañas forman 4 columnas (`repeat(4, minmax(0, 1fr))`) y en tablet/móvil (`<= 820px`) pasan a una rejilla `2×2` con objetivos táctiles de `>= 48px` de altura y cero desbordamiento horizontal en `360px`, `768px` y `1366px`. Los botones del hero, las tarjetas de `#servicios`, el ítem 6 de `#transparencia` y los enlaces de servicios en `#contacto` enlazan directamente a `#tramites` mediante `data-sirec-open`, `data-sirec-concepto` y `data-sirec-notice`.

### 6.2 Indicador discreto de estado SIREC y avisos contextuales

- **`#sirec-status`** (`role="status"`, `aria-live="polite"`): refleja `data-status="loading" | "online" | "offline"` combinando color AA y forma diferenciada (aro giratorio en carga que pasa a borde punteado estático en `prefers-reduced-motion`, punto sólido en línea y rombo rotado en fuera de línea). Incluye la insignia `#sirec-mock-badge` ("Modo de prueba") y el botón `#sirec-status-retry` (`min-height: 44px`).
- **`#sirec-notice`**: franja informativa opcional para accesos que requieren aclaración presencial (como Licencias de construcción y uso de suelo).

### 6.3 Paleta semántica de estados y errores (WCAG 2.2 AA en ambos temas)

Todas las insignias (`.sirec-badge`) combinan ícono SVG inline + etiqueta textual y superan `4.5:1` sobre sus fondos respectivos, así como `>= 3:1` en bordes de controles (`--border-control`) y foco visible de `3px`:

| Estado / Rol | Tema Claro (texto / fondo / borde) | Contraste Claro | Tema Oscuro (texto / fondo / borde) | Contraste Oscuro |
| :--- | :--- | :--- | :--- | :--- |
| Error de campo (`.field-error`) | `#b42318` sobre `#ffffff` | **6.57:1** | `#ff9b96` sobre `#1a263c` | **7.49:1** |
| Estado de error y badge `vencido` | `#9a1c15` / `#fdeceb` / `#c93126` | **7.20:1** | `#ffaba5` / `#3f1718` / `#f06a62` | **8.63:1** |
| Estado de éxito y badges `pagado` / `resuelta` | `#0a5a32` / `#e4f6ec` / `#128a4e` | **7.41:1** | `#8ef0b9` / `#113524` / `#4ad08a` | **9.83:1** |
| Badges `pendiente` / `en_tramite` y modo prueba | `#734400` / `#fff4d6` / `#c48200` | **7.50:1** | `#ffd670` / `#3a2b0d` / `#f6b11f` | **9.86:1** |
| Aviso informativo y badge `recibida` | `#0a2a66` / `#e8f0fe` / `#1452c9` | **11.93:1** | `#b6d0ff` / `#172b52` / `#7aa7ff` | **8.95:1** |
| Badge `prorrogada` | `#4a2574` / `#f2ebfc` / `#7642b5` | **9.99:1** | `#d9baff` / `#2d1b47` / `#b182f5` | **9.14:1** |
| Botón primario (`.sirec-btn-primary`) | `#ffffff` sobre `#1452c9` (hover `#0a2a66`) | **6.82:1** / **13.67:1** | `#ffffff` sobre `#1452c9` (hover `#0a2a66`) | **6.82:1** / **13.67:1** |

### 6.4 Estados de interfaz (`vacío`, `cargando`, `error`, `éxito`)

Cada panel incluye una región viva `.sirec-result` (`aria-live="polite"`, `aria-busy="false"`) estilizada para cuatro estados consistentes:
- **Vacío (`.sirec-state--empty`)**: recuadro sutil con borde punteado e instrucción clara inicial.
- **Cargando (`.sirec-state--loading`)**: indicador `.sirec-spinner` alineado al texto de espera; se vuelve estático cuando `@media (prefers-reduced-motion: reduce)` está activo.
- **Error (`.sirec-state--error`)**: contenedor de alto contraste para mensajes amigables devueltos por SIREC o errores de red.
- **Éxito (`.sirec-state--success` / `.sirec-card` / `.sirec-voucher`)**: tarjetas estructuradas con montos en `tabular-nums` y acciones contextuales claras.

### 6.5 Diseño de impresión (`@media print`) de la Orden de Pago

Al imprimir el comprobante `#orden-comprobante` (`.sirec-voucher`), la hoja `@media print` oculta cabecera, navegación, hero, servicios, cifras, noticias, transparencia, pie, pestañas, formularios y controles marcados con `.no-print`, conservando únicamente:
- La cinta `.demo-bar` en fondo blanco con borde azul marino (ahorro de tinta y aviso visible de demostración).
- El comprobante `.sirec-voucher` con fondo blanco, borde sólido `#0a2a66`, sin sombras, `break-inside: avoid` y la cabecera de impresión `.sirec-voucher-print-head` visible ("MuniSoke GT · Municipalidad de Soke · Orden de Pago (Demostración)").
