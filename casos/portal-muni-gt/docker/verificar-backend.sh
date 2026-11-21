#!/usr/bin/env bash
# Verifica que el servidor de la muni (backend SIREC) este arriba y anuncie lo que el demo necesita.
# Uso: bash verificar-backend.sh [IP]     (por defecto 127.0.0.1; para el demo, la IP de Tailscale)
# Solo lee banners y llama a la API; no explota nada.
IP=${1:-127.0.0.1}
ok=0; fail=0
chk() { if [ "$1" = "OK" ]; then echo "  [OK]    $2"; ok=$((ok+1)); else echo "  [FALLA] $2"; fail=$((fail+1)); fi; }
banner() { python3 - "$IP" "$1" <<'PY'
import socket, sys
try:
    s = socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=4); s.settimeout(3)
    print(s.recv(256).decode("latin-1", "replace").replace("\x00", " ").strip())
except OSError as e:
    print("SIN-RESPUESTA (%s)" % e)
PY
}
echo "== Servidor de la muni: $IP =="
b=$(banner 25);   case "$b" in *"Exim 4.89"*) chk OK "Exim 4.89 en :25";; *) chk FAIL "Exim 4.89 en :25 -> $b";; esac
b=$(banner 3306); case "$b" in *"5.5.62"*) chk OK "MySQL 5.5.62 en :3306";; *) chk FAIL "MySQL 5.5.62 en :3306 -> ${b:0:60}";; esac
r=$(python3 -c "import socket,sys;s=socket.create_connection(('$IP',6379),4);s.sendall(b'PING\r\n');print(s.recv(64).decode().strip())" 2>&1)
[ "$r" = "+PONG" ] && chk OK "Redis sin clave en :6379 (PING -> PONG)" || chk FAIL "Redis en :6379 -> $r"
j=$(curl -s -m 8 "http://$IP:${PUERTO_PORTAL:-8088}/sirec/api/estado")
case "$j" in *'"SIREC"'*) chk OK "SIREC responde en /sirec/api/estado";; *) chk FAIL "SIREC en /sirec/api/estado -> ${j:0:80}";; esac
b=$(banner 21)
case "$b" in *"ProFTPD 1.3.5"*) echo "  [INFO]  FTP ProFTPD 1.3.5 ENCENDIDO en :21 (para el cambio en vivo debe empezar apagado)";;
             *) echo "  [INFO]  FTP apagado (correcto antes del demo). Encender en vivo: docker compose --profile cambio up -d ftp";; esac
echo "== Resultado: $ok OK, $fail fallas =="
[ $fail -eq 0 ]
