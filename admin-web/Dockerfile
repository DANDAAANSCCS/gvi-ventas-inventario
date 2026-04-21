FROM nginx:alpine

# Archivos estaticos (HTML/CSS/JS)
COPY css       /usr/share/nginx/html/css
COPY js        /usr/share/nginx/html/js
COPY *.html    /usr/share/nginx/html/

# Config nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Entrypoint que escribe js/config.js con API_URL en runtime
COPY nginx-entrypoint.sh /docker-entrypoint.d/40-inject-api-url.sh
RUN chmod +x /docker-entrypoint.d/40-inject-api-url.sh

EXPOSE 80
