// =============================================
// js/utils.js — Utilidades compartidas
// =============================================

/** Muestra un toast de notificación */
function showToast(message, type = "info", duration = 3500) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.4s";
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

/** Formatea un número como moneda */
function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency", currency: "MXN"
  }).format(amount);
}

/** Formatea una fecha ISO a dd/mm/yyyy */
function formatDate(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleDateString("es-MX");
}

/** Muestra/oculta un spinner en un contenedor */
function showSpinner(containerId) {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = '<div class="spinner"></div>';
}

/** Genera un badge HTML de estado */
function statusBadge(status) {
  const map = {
    pending:   ["badge-warning",   "Pendiente"],
    completed: ["badge-success",   "Completado"],
    cancelled: ["badge-danger",    "Cancelado"],
    shipped:   ["badge-info",      "Enviado"],
  };
  const [cls, label] = map[status] || ["badge-secondary", status];
  return `<span class="badge ${cls}">${label}</span>`;
}

/** Valida formato de email */
function isValidEmail(email) {
  return /^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$/.test(email);
}

/** Escapa HTML para prevenir XSS */
function escapeHtml(str) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(str || ""));
  return d.innerHTML;
}
