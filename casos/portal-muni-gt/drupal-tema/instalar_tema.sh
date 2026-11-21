#!/usr/bin/env bash
# Copia el tema MuniSoke al contenedor de Drupal y lo deja como tema por defecto.
# No reinstala Drupal ni toca la base de datos mas alla de activar el tema.
# Uso (con el stack arriba):  bash instalar_tema.sh [contenedor]   # por defecto revital-drupal
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
# Windows (Git Bash): no convertir las rutas de DENTRO del contenedor (/var/www/...) en rutas de Windows
export MSYS2_ARG_CONV_EXCL="/var/www"
PY="$(command -v python3 || command -v python)"
C="${1:-$(cd "$HERE/../docker" && docker compose ps -q drupal 2>/dev/null)}"
[ -n "$C" ] || C=revital-drupal
docker inspect "$C" >/dev/null 2>&1 || { echo "No encuentro el contenedor $C (docker compose up -d)"; exit 1; }

"$PY" "$HERE/generar_tema.py"
docker exec "$C" rm -rf /var/www/html/sites/all/themes/munisoke
docker cp "$HERE/munisoke" "$C:/var/www/html/sites/all/themes/munisoke"
docker exec "$C" chown -R www-data:www-data /var/www/html/sites/all/themes/munisoke

docker exec -i "$C" sh -c 'cd /var/www/html && php' <<'PHP'
<?php
define('DRUPAL_ROOT', getcwd());
$_SERVER['REMOTE_ADDR'] = '127.0.0.1';
$_SERVER['HTTP_HOST'] = 'localhost';
$_SERVER['SCRIPT_NAME'] = '/index.php';
require_once DRUPAL_ROOT . '/includes/bootstrap.inc';
drupal_bootstrap(DRUPAL_BOOTSTRAP_FULL);
system_rebuild_theme_data();
theme_enable(array('munisoke'));
variable_set('theme_default', 'munisoke');
variable_set('site_name', 'MuniSoke GT · Municipalidad de Soke');
drupal_flush_all_caches();
echo "Tema por defecto: " . variable_get('theme_default') . "\n";
PHP

# OPcache del contenedor revalida cada 60 s: recarga suave para que el tema nuevo aplique ya.
docker exec "$C" apachectl -k graceful
sleep 2
echo "Listo. Verifica con: bash ../docker/verificar.sh <url>"
