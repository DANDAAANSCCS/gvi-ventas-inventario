FROM nginx:alpine

# IMPORTANTE: este Dockerfile espera build context = raiz del repo (no ./client).
# Monta las 3 webs bajo el mismo dominio usando subrutas.

# ---- Cliente publico en /
COPY client/css    /usr/share/nginx/html/css
COPY client/js     /usr/share/nginx/html/js
COPY client/*.html /usr/share/nginx/html/

# ---- Panel admin en /admin
COPY admin-web/css    /usr/share/nginx/html/admin/css
COPY admin-web/js     /usr/share/nginx/html/admin/js
COPY admin-web/*.html /usr/share/nginx/html/admin/

# ---- DB manager en /db
COPY db-web/css    /usr/share/nginx/html/db/css
COPY db-web/js     /usr/share/nginx/html/db/js
COPY db-web/*.html /usr/share/nginx/html/db/

# Config nginx
COPY client/nginx.conf /etc/nginx/conf.d/default.conf

# Entrypoint que escribe los 3 config.js (client, admin, db) con API_URL en runtime
COPY client/nginx-entrypoint.sh /docker-entrypoint.d/40-inject-api-url.sh
RUN chmod +x /docker-entrypoint.d/40-inject-api-url.sh

EXPOSE 80
