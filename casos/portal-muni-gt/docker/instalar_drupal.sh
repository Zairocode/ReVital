#!/usr/bin/env bash
# Instala Drupal 7.57 en el contenedor "drupal" SIN asistente web (para no depender de hacerlo a mano en la demo).
# Uso (con el stack arriba):  bash instalar_drupal.sh        # admin / admin, solo local
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
C="$(cd "$HERE" && docker compose ps -q drupal)"
[ -n "$C" ] || { echo "No encuentro el contenedor drupal: corre antes 'docker compose up -d --build'"; exit 1; }

if ! curl -s -o /dev/null -w '%{redirect_url}' http://localhost:8080/ | grep -qi 'install.php'; then
  echo "Drupal ya parece instalado (/ no redirige a install.php). Nada que hacer."; exit 0
fi

docker cp "$HERE/instalar_drupal.php" "$C:/var/www/html/instalar_drupal.php"
docker exec "$C" sh -c '
  cd /var/www/html &&
  cp -f sites/default/default.settings.php sites/default/settings.php &&
  cat >> sites/default/settings.php <<EOS
\$databases["default"]["default"] = array("driver" => "mysql", "database" => "drupal", "username" => "drupal", "password" => "drupalpw", "host" => "db", "port" => "", "prefix" => "");
EOS
  mkdir -p sites/default/files &&
  chown -R www-data:www-data sites/default/settings.php sites/default/files &&
  chmod 666 sites/default/settings.php &&
  su -s /bin/sh www-data -c "php instalar_drupal.php"
  rc=$?
  rm -f instalar_drupal.php; chmod 444 sites/default/settings.php
  exit $rc'
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/)
[ "$code" = "200" ] || { echo "FALLO: / responde $code (revisa el error de arriba)"; exit 1; }
bash "$HERE/aplicar_branding.sh"   # deja la portada MuniSoke GT en / (el objetivo sigue siendo Drupal)
echo "Listo: http://localhost:8080 (admin / admin). Verifica con: bash verificar.sh"
