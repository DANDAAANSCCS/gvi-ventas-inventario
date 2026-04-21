#!/bin/sh
# Inyecta API_URL en js/config.js al arrancar. Misma imagen sirve dev y prod.
set -e

API_URL="${API_URL:-http://localhost:8100}"
CONFIG_FILE="/usr/share/nginx/html/js/config.js"

cat > "$CONFIG_FILE" <<EOF
// Generado por nginx-entrypoint.sh en runtime
window.API_URL = "${API_URL}";
EOF

echo "[admin-web entrypoint] API_URL=${API_URL}"
