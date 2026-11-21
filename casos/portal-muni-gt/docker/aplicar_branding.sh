#!/usr/bin/env bash
# Hace que http://localhost:8080/ se vea como la portada MuniSoke GT (branding/index.html) en vez del Drupal por defecto.
# La portada es solo el tema de la pagina de inicio: /?q=user/register, /admin, etc. siguen siendo Drupal (el objetivo
# sigue siendo el mismo para el crawler y para los CVE). No toca el proxy Apache.
# Uso (con el stack arriba y Drupal instalado):  bash aplicar_branding.sh
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
CASO="$(cd "$HERE/.." && pwd)"
C="$(cd "$HERE" && docker compose ps -q drupal)"
[ -n "$C" ] || { echo "No encuentro el contenedor drupal: corre antes 'docker compose up -d --build'"; exit 1; }

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
cp -r "$CASO/drupal-theme/munisoke" "$T/munisoke"
# branding/index.html es un FRAGMENTO (sin <html>/<head>/<body>): lo envolvemos en una pagina completa, con el $head de
# Drupal (conserva meta generator y favicon) y al final los accesos a Drupal (login y registro de ciudadanos).
ENLACES='<p style="text-align:center;padding:14px;font:600 14px sans-serif"><a href="/?q=user/login">Acceso personal municipal</a> &middot; <a href="/?q=user/register">Crear cuenta ciudadana</a></p>'
{
  printf '%s\n' '<!DOCTYPE html>' '<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' '<?php print $head; ?>'
  tr -d '\r' < "$CASO/branding/index.html"
  printf '%s\n' "$ENLACES" '</body></html>'
} > "$T/munisoke/page--front.tpl.php"
grep -q 'print $head' "$T/munisoke/page--front.tpl.php" && grep -q 'MuniSoke' "$T/munisoke/page--front.tpl.php" \
  || { echo "No pude armar la plantilla de la portada"; exit 1; }

docker exec "$C" mkdir -p /var/www/html/sites/all/themes
docker cp "$T/munisoke" "$C:/var/www/html/sites/all/themes/"
docker cp "$HERE/aplicar_branding.php" "$C:/var/www/html/aplicar_branding.php"
docker exec "$C" sh -c '
  cd /var/www/html &&
  chown -R www-data:www-data sites/all/themes/munisoke &&
  su -s /bin/sh www-data -c "php aplicar_branding.php"
  rc=$?
  rm -f aplicar_branding.php
  exit $rc'
code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/)"
curl -s http://localhost:8080/ | grep -q 'MuniSoke' || { echo "FALLO: / no muestra la portada (codigo $code)"; exit 1; }
echo "Listo: http://localhost:8080/ muestra la portada MuniSoke GT. Verifica con: bash verificar.sh"
