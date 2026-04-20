// =============================================
// js/config.js - URL de la API backend
// =============================================
// En produccion, nginx inyecta este valor via envsubst (ver client/nginx-entrypoint.sh).
// En dev, se puede editar directamente.
window.API_URL = window.API_URL || "http://localhost:8000";
