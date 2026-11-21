#!/usr/bin/env bash
# Demo de ReVital frente al publico (caso MUNI-GT). Correr desde cualquier carpeta.
#
#   bash casos/portal-muni-gt/demo.sh preparar    # ANTES de presentar: verifica, limpia, analiza todo y toma la linea base (FTP apagado)
#   bash casos/portal-muni-gt/demo.sh panel       # abre el panel (dejarlo corriendo en otra terminal); por SSH muestra el tunel
#   bash casos/portal-muni-gt/demo.sh cambio      # EN ESCENA: enciende el FTP y el sentinela da la alerta
#   bash casos/portal-muni-gt/demo.sh reiniciar   # despues: apaga el FTP y deja todo listo para otra presentacion
#   bash casos/portal-muni-gt/demo.sh estado      # que esta arriba y que no
#
# Variables: DEMO_IP (por defecto la IP de Tailscale del equipo del demo), DEMO_PORTAL y DEMO_USUARIO (para el tunel SSH).
# Si presentas desde OTRO equipo conectado por SSH: el panel solo escucha en 127.0.0.1 de este equipo; en tu equipo abre
#   ssh -N -L 8765:127.0.0.1:8765 <usuario>@<IP>     y en tu navegador  http://127.0.0.1:8765
# Solo contra el stack propio del caso (muni FICTICIA). No explota nada: solo detecta.
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
DOCKER="$AQUI/docker"
IP="${DEMO_IP:-100.91.166.18}"
PORTAL="${DEMO_PORTAL:-http://$IP:8088}"
SAL="$RAIZ/salida/demo"
ENT="MUNI-GT"
USUARIO="${DEMO_USUARIO:-$(id -un)}"
TUNEL="ssh -N -L 8765:127.0.0.1:8765 $USUARIO@$IP"
PY="$(command -v python3 || command -v python)"

b() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok() { printf '  \033[32m✔\033[0m %s\n' "$*"; }
mal() { printf '  \033[31m✘ %s\033[0m\n' "$*"; }
rv() { (cd "$RAIZ" && "$PY" -W ignore -m "$@"); }
ftp() { (cd "$DOCKER" && docker compose --profile cambio "$@" ftp >/dev/null 2>&1); }
ftp_arriba() { "$PY" -c "import socket;s=socket.create_connection(('$IP',21),2);print(s.recv(80).decode('latin-1'))" 2>/dev/null | grep -q ProFTPD; }

config_red() {  # objetivo de red solo: la vuelta en escena tarda segundos (lo demas ya esta analizado)
  cat > "$SAL/sentinela-cambio.json" <<EOF
{"cada_minutos": 1, "salida": "$SAL", "al_detectar_cambio": "",
 "objetivos": [{"entidad": "$ENT", "tipo": "red", "destino": "$IP", "puertos": [21, 25, 3306, 6379]}]}
EOF
}

enlaces() {
  b "Enlaces (navegador en ventana de incognito)"
  echo "  Portal de la muni ......... $PORTAL/"
  echo "  Ventanilla de tramites .... $PORTAL/#tramites   (ej. finca F-1024)"
  echo "  SIREC operadores .......... $PORTAL/sirec/login.action"
  echo "  Panel de ReVital .......... http://127.0.0.1:8765   (bash $0 panel)"
  [ -n "${SSH_CONNECTION:-}" ] && echo "    desde tu equipo (otra terminal, dejarla abierta):  $TUNEL"
}

estado() {
  b "Estado del stack ($IP)"
  bash "$DOCKER/verificar-backend.sh" "$IP" | sed -n '2,7p'
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$PORTAL/")" = 200 ] && ok "portal responde" || mal "portal NO responde ($PORTAL)"
  ss -ltn 2>/dev/null | grep -q ':8765 ' && ok "panel abierto en http://127.0.0.1:8765" || echo "  · panel cerrado (bash $0 panel)"
}

preparar() {
  local t0=$SECONDS
  b "1/5 El stack esta arriba"
  if ! bash "$DOCKER/verificar-backend.sh" "$IP" >/dev/null; then
    mal "falta algun servicio. Levantalo:  cd $DOCKER && docker compose up -d"; bash "$DOCKER/verificar-backend.sh" "$IP"; exit 1
  fi
  ok "Exim, MySQL, Redis y SIREC arriba"
  ftp_arriba && { ftp stop; ok "FTP apagado (debe empezar apagado)"; } || ok "FTP apagado"

  b "2/5 Datos de SIREC limpios (se borran solo las ordenes y solicitudes que dejaron las pruebas)"
  docker exec revital-sirec-db mysql -uroot -pmuni2014 sirec -e \
    "DELETE FROM ordenes_pago; DELETE FROM solicitudes_laip WHERE folio > 'LAIP-2026-0152';" 2>/dev/null && ok "ordenes y solicitudes de prueba eliminadas" || mal "no se pudo limpiar la BD"

  b "3/5 Resultados anteriores del demo"
  if [ -d "$SAL" ]; then mv "$SAL" "$SAL-$(date +%H%M%S)" && ok "guardados aparte en salida/demo-$(date +%H%M%S)"; else ok "no habia"; fi
  mkdir -p "$SAL"

  b "4/5 Analisis completo de MUNI-GT"
  rv revital.red "$IP" --puertos 21,25,3306,6379,8088 --entidad "$ENT" --out "$SAL" --autorizo | tail -1 | sed 's/^/  red:    /'
  rv revital.crawler "$PORTAL" --entidad "$ENT" --out "$SAL" --delay 0.1 | tail -1 | sed 's/^/  web:    /'
  rv revital.codigo "$RAIZ/casos/portal-muni-gt/backend/sirec" --entidad "$ENT" --out "$SAL" | tail -1 | sed 's/^/  codigo: /'
  rv revital.cves --out "$SAL" --entidad "$ENT" >/dev/null && ok "$(grep -m1 -o 'Cumplimiento: [A-Z ]*' "$SAL/reporte-muni-gt.md") · $("$PY" -c "import json,sys;h=json.load(open(sys.argv[1]));print(len({x['cve'] for x in h['hallazgos'] if x['en_kev']}))" "$SAL/hallazgos-muni-gt.json") vulnerabilidades KEV"

  b "5/5 Linea base del sentinela (FTP apagado)"
  config_red
  rv revital.sentinela --config "$SAL/sentinela-cambio.json" --una-vez >/dev/null 2>&1 && ok "linea base tomada" || mal "fallo la linea base"
  b "Listo en $((SECONDS - t0)) s. Ahora: bash $0 panel   (y en escena: bash $0 cambio)"
  enlaces
}

cambio() {
  [ -f "$SAL/sentinela-cambio.json" ] || { mal "primero: bash $0 preparar"; exit 1; }
  local t0=$SECONDS
  b "El proveedor habilita un FTP para subir las actas..."
  ftp up -d
  for _ in $(seq 1 20); do ftp_arriba && break; sleep 0.5; done
  ftp_arriba && ok "FTP encendido en $IP:21" || { mal "el FTP no arranco"; exit 1; }
  b "ReVital vigila (una vuelta del sentinela)"
  rv revital.sentinela --config "$SAL/sentinela-cambio.json" --una-vez >/dev/null 2>&1
  "$PY" - "$SAL/alertas.jsonl" <<'PY'
import json, sys
try:
    al = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
except OSError:
    al = []
nuevas = [a for a in al if "ProFTPD" in a.get("detalle", "")]
for a in nuevas[-3:]:
    print("  \033[31m⚠ %s\033[0m  %s" % (a["severidad"].upper(), a["detalle"]))
if not nuevas:
    print("  (sin alerta del FTP: revisa 'bash demo.sh estado')")
PY
  b "Listo en $((SECONDS - t0)) s. Recarga el panel: http://127.0.0.1:8765"
}

reiniciar() {
  b "Dejando todo listo para otra presentacion"
  ftp stop && ok "FTP apagado"
  preparar
}

case "${1:-}" in
  preparar) preparar ;;
  panel)
    cd "$RAIZ" && mkdir -p "$SAL" && config_red
    if ss -ltn 2>/dev/null | grep -q ':8765 '; then ok "el panel ya esta abierto en http://127.0.0.1:8765"; exit 0; fi
    abrir="--abrir"
    if [ -n "${SSH_CONNECTION:-}" ] || [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then  # por SSH: el navegador esta en tu otro equipo
      abrir=""
      b "Panel en este equipo, solo en 127.0.0.1:8765. Para verlo desde tu equipo:"
      echo "  1) en tu equipo, otra terminal (dejarla abierta):  $TUNEL"
      echo "  2) en tu navegador:                                http://127.0.0.1:8765"
      echo "  (Ctrl+C aqui cierra el panel)"
    fi
    exec "$PY" -m revital.panel --salida "$SAL" --config "$SAL/sentinela-cambio.json" $abrir ;;
  cambio) cambio ;;
  reiniciar) reiniciar ;;
  estado) estado; enlaces ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
