#!/bin/sh
# Inyecta API_URL en js/config.js al arrancar.
set -e

API_URL="${API_URL:-http://localhost:8100}"
CONFIG_FILE="/usr/share/nginx/html/js/config.js"

cat > "$CONFIG_FILE" <<EOF
// Generado por nginx-entrypoint.sh en runtime
window.API_URL = "${API_URL}";
EOF

echo "[db-web entrypoint] API_URL=${API_URL}"
