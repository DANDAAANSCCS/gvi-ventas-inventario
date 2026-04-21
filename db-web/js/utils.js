// db-web/js/utils.js — helpers compartidos

function escapeHtml(str) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(str == null ? "" : String(str)));
  return d.innerHTML;
}

function showToast(message, type = "info", duration = 3200) {
  let box = document.getElementById("toast-container");
  if (!box) {
    box = document.createElement("div");
    box.id = "toast-container";
    box.className = "toast-container";
    document.body.appendChild(box);
  }
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = message;
  box.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transition = "opacity .4s";
    setTimeout(() => t.remove(), 400);
  }, duration);
}

function debounce(fn, ms = 300) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), ms);
  };
}

function confirmDialog(msg) {
  return window.confirm(msg);
}

/** Formatea valor de celda para display. */
function formatCellValue(value) {
  if (value === null || value === undefined) return '<em style="color:var(--text-muted);">NULL</em>';
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return escapeHtml(JSON.stringify(value));
  const s = String(value);
  if (s.length > 120) return escapeHtml(s.slice(0, 120)) + "...";
  return escapeHtml(s);
}

/** Parsea input de texto a valor apropiado. "" / "NULL" -> null. */
function parseCellInput(rawValue, columnType) {
  if (rawValue === "" || rawValue === null) return null;
  if (rawValue === "NULL" || rawValue === "null") return null;
  const t = (columnType || "").toLowerCase();
  if (t.includes("int") || t.includes("numeric") || t.includes("decimal") || t.includes("real") || t.includes("double")) {
    const n = Number(rawValue);
    if (!isNaN(n)) return n;
  }
  if (t.includes("bool")) {
    if (rawValue === "true" || rawValue === true) return true;
    if (rawValue === "false" || rawValue === false) return false;
  }
  return rawValue;
}
