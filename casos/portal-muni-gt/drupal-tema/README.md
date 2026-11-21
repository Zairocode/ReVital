# Tema Drupal 7 "munisoke"

Monta la portada 3D de `../branding-3d/` como **tema de Drupal 7**, para que Drupal siga sirviendo
todas las paginas y el demo conserve sus huellas: meta generator "Drupal 7", `/CHANGELOG.txt` y
`/user/register` (CVE-2018-7600).

```
bash instalar_tema.sh            # contenedor por defecto: revital-drupal
bash ../docker/verificar.sh <url-del-portal>   # debe seguir en 6/6
```

- `generar_tema.py`: arma `munisoke/` desde `branding-3d/` (html.tpl.php en espanol, page.tpl.php
  con la portada completa en `/` y cabecera + contenido de Drupal en paginas internas). Si cambia
  el diseno, se edita `branding-3d/` y se vuelve a correr el instalador.
- `instalar_tema.sh`: genera, copia al contenedor, activa el tema, renombra el sitio a
  "MuniSoke GT · Municipalidad de Soke", limpia caches y hace `apachectl -k graceful` (OPcache del
  contenedor revalida cada 60 s).
- `munisoke/` es generado: no se versiona.

Para la demo, abrir el portal sin sesion de admin (incognito), o se ve la barra de administracion.
