#!/bin/sh
# Inyecta la variable de entorno API_URL en los 3 config.js al arrancar el contenedor.
# Asi la misma imagen sirve para dev (localhost:8100) y produccion (api-gvi.namu-li.com).
set -e

API_URL="${API_URL:-http://localhost:8000}"

write_config() {
  local path="$1"
  mkdir -p "$(dirname "$path")"
  cat > "$path" <<EOF
// Generado por nginx-entrypoint.sh en runtime
window.API_URL = "${API_URL}";
EOF
}

write_config "/usr/share/nginx/html/js/config.js"
write_config "/usr/share/nginx/html/admin/js/config.js"
write_config "/usr/share/nginx/html/db/js/config.js"

echo "[nginx-entrypoint] API_URL=${API_URL} (inyectado en client, admin, db)"
