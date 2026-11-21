# Apache HTTP Server 2.4.49: la version con CVE-2021-41773 (CISA KEV, usada en ransomware).
# Se deja deliberadamente VULNERABLE para la demo de ReVital. No usar en nada real.
FROM httpd:2.4.49

# 1) Habilitar los modulos que necesitamos: proxy (hacia Drupal) y cgi (para el RCE de 41773).
RUN sed -i \
    -e 's/^#\(LoadModule proxy_module \)/\1/' \
    -e 's/^#\(LoadModule proxy_http_module \)/\1/' \
    -e 's/^#\(LoadModule cgid_module \)/\1/' \
    -e 's/^#\(LoadModule cgi_module \)/\1/' \
    conf/httpd.conf

# 2) El disparador de CVE-2021-41773: en el httpd.conf por defecto el directorio raiz esta en
#    "Require all denied". Al pasarlo a "granted" el path traversal con %2e queda explotable.
RUN sed -i 's/Require all denied/Require all granted/' conf/httpd.conf

# 3) Nuestra config: reverse proxy a Drupal + alias cgi-bin para el PoC de RCE.
COPY vuln.conf conf/extra/vuln.conf
RUN printf '\nInclude conf/extra/vuln.conf\n' >> conf/httpd.conf

# 4) Un cgi-bin de ejemplo (necesario solo para el PoC de RCE de 41773; la lectura de
#    archivos funciona con el alias /icons/ que ya trae la imagen).
RUN mkdir -p /usr/local/apache2/cgi-bin
