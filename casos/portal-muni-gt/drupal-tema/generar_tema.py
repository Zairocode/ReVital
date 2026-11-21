#!/usr/bin/env python3
"""Genera el tema Drupal 7 'munisoke' a partir de la maqueta estatica ../branding-3d/.

Uso:  python3 generar_tema.py        (escribe ./munisoke/)

Por que un tema y no servir el HTML estatico: Drupal tiene que seguir sirviendo todas las
paginas para que el demo conserve sus huellas (meta generator "Drupal 7", /CHANGELOG.txt,
/user/register para CVE-2018-7600). El tema solo cambia la piel.
"""
import os
import re
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, "..", "branding-3d")
DESTINO = os.path.join(AQUI, "munisoke")

html = open(os.path.join(FUENTE, "index.html"), encoding="utf-8").read()


def entre(ini, fin):
    a = html.index(ini)
    b = html.index(fin, a)
    return html[a:b]


cabecera = entre("<!-- Region: demo_banner -->", "<main ")
portada = entre("<!-- Region: hero -->", "</main>")
pie = entre("<!-- Region: footer -->", "</body>")

# En paginas internas (/user/login, /node/1...) las anclas deben volver a la portada.
ANCLA = '<?php print $mk_ancla; ?>#'
cabecera = cabecera.replace('href="#', 'href="' + ANCLA)
pie = pie.replace('href="#', 'href="' + ANCLA)
# "Mi Portal" lleva al acceso de Drupal (como en un portal municipal real).
cabecera = re.sub(r'href="[^"]*"(>\s*<svg[^>]*>(?:(?!</a>).)*Mi Portal)',
                  r'href="<?php print base_path(); ?>user/login"\1', cabecera, count=1, flags=re.S)

PAGE = """<?php
/**
 * page.tpl.php del tema MuniSoke (generado por generar_tema.py: no editar a mano).
 * Portada: maqueta completa. Paginas internas: misma cabecera/pie + contenido de Drupal.
 */
$mk_ancla = $is_front ? '' : base_path();
?>
%(cabecera)s
<main id="contenido-principal" tabindex="-1">
  <a id="main-content"></a>
<?php if ($messages): ?>
  <div class="wrap mk-mensajes"><?php print $messages; ?></div>
<?php endif; ?>
<?php if ($is_front): ?>
%(portada)s
<?php else: ?>
  <section class="sec mk-interna">
    <div class="wrap">
      <?php print render($title_prefix); ?>
      <?php if ($title): ?><h1 class="sec-title mk-titulo"><?php print $title; ?></h1><?php endif; ?>
      <?php print render($title_suffix); ?>
      <?php if ($tabs): ?><div class="mk-tabs"><?php print render($tabs); ?></div><?php endif; ?>
      <?php if ($action_links): ?><ul class="action-links"><?php print render($action_links); ?></ul><?php endif; ?>
      <div class="mk-contenido"><?php print render($page['content']); ?></div>
    </div>
  </section>
<?php endif; ?>
</main>
%(pie)s
"""

HTML_TPL = """<?php
/**
 * html.tpl.php del tema MuniSoke: documento HTML5 en espanol.
 * $head conserva el meta generator de Drupal 7 (huella que detecta ReVital).
 */
$mk_tema = base_path() . path_to_theme();
?><!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="light">
  <?php print $head; ?>
  <title><?php print drupal_is_front_page() ? check_plain(variable_get('site_name', 'MuniSoke GT')) : $head_title; ?></title>
  <?php print $styles; ?>
  <?php print $scripts; ?>
  <script type="importmap">
  {"imports": {
    "three": "<?php print $mk_tema; ?>/vendor/three/three.module.js",
    "gsap": "<?php print $mk_tema; ?>/vendor/gsap/index.js",
    "gsap/ScrollTrigger": "<?php print $mk_tema; ?>/vendor/gsap/ScrollTrigger.js"
  }}
  </script>
  <script type="module" src="<?php print $mk_tema; ?>/js/main.js"></script>
</head>
<body class="<?php print $classes; ?>" <?php print $attributes; ?>>
  <a class="skip-link" href="#contenido-principal">Saltar al contenido principal</a>
  <?php print $page_top; ?>
  <?php print $page; ?>
  <?php print $page_bottom; ?>
</body>
</html>
"""

INFO = """name = MuniSoke GT
description = Tema del portal ficticio MuniSoke GT (caso ReVital MUNI-GT). Generado desde branding-3d/.
core = 7.x
engine = phptemplate
stylesheets[all][] = css/fonts.css
stylesheets[all][] = css/styles.css
stylesheets[all][] = css/drupal-interno.css
regions[content] = Contenido
"""

# Paginas internas de Drupal (formularios, mensajes, pestanas) con la piel del portal.
INTERNO = """/* Ajustes para paginas internas de Drupal (login, registro, nodos). */
.mk-interna .wrap { max-width: 760px; }
.mk-titulo { margin-bottom: 24px; }
.mk-mensajes { padding-top: 20px; }
.mk-mensajes .messages { border-radius: var(--radius-md); padding: 12px 16px; }
.mk-contenido .form-item { margin: 0 0 18px; }
.mk-contenido label { display: block; font-weight: 600; color: var(--text-strong); margin-bottom: 6px; }
.mk-contenido input.form-text,
.mk-contenido textarea,
.mk-contenido select {
  width: 100%; max-width: 480px; padding: 10px 12px; font: inherit;
  color: var(--text-strong); background: var(--surface);
  border: 1px solid var(--border-control); border-radius: var(--radius-sm);
}
.mk-contenido .description { color: var(--text-muted); font-size: 0.88rem; margin-top: 4px; }
.mk-contenido input.form-submit {
  min-height: 44px; padding: 10px 22px; border: 0; border-radius: 10px; cursor: pointer;
  font-family: var(--font-head); font-weight: 800; color: #fff; background: var(--brand-civic);
}
.mk-contenido input.form-submit:hover { background: var(--brand-navy); }
.mk-tabs ul.tabs { display: flex; gap: 8px; padding: 0; margin: 0 0 20px; list-style: none; border: 0; }
.mk-tabs ul.tabs li a { padding: 8px 14px; border-radius: var(--radius-sm); background: var(--surface-subtle); color: var(--accent-link); font-weight: 600; }
.mk-tabs ul.tabs li.active a { background: var(--brand-navy); color: #fff; }
"""

if os.path.exists(DESTINO):
    shutil.rmtree(DESTINO)
os.makedirs(os.path.join(DESTINO, "templates"))
for carpeta in ("css", "js", "vendor", "fonts"):
    shutil.copytree(os.path.join(FUENTE, carpeta), os.path.join(DESTINO, carpeta))

with open(os.path.join(DESTINO, "munisoke.info"), "w", encoding="utf-8") as f:
    f.write(INFO)
with open(os.path.join(DESTINO, "css", "drupal-interno.css"), "w", encoding="utf-8") as f:
    f.write(INTERNO)
with open(os.path.join(DESTINO, "templates", "html.tpl.php"), "w", encoding="utf-8") as f:
    f.write(HTML_TPL)
with open(os.path.join(DESTINO, "templates", "page.tpl.php"), "w", encoding="utf-8") as f:
    f.write(PAGE % {"cabecera": cabecera.rstrip(), "portada": portada.rstrip(), "pie": pie.rstrip()})
print("tema generado en", DESTINO)
