#!/bin/sh
# Inyecta la variable de entorno API_URL en js/config.js al arrancar el contenedor.
# Asi la misma imagen sirve para dev (localhost:8000) y produccion (api-gvi.namu-li.com).
set -e

API_URL="${API_URL:-http://localhost:8000}"

CONFIG_FILE="/usr/share/nginx/html/js/config.js"

cat > "$CONFIG_FILE" <<EOF
// Generado por nginx-entrypoint.sh en runtime
window.API_URL = "${API_URL}";
EOF

echo "[nginx-entrypoint] API_URL=${API_URL}"
