// admin-web/js/utils.js — helpers compartidos

function escapeHtml(str) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(str == null ? "" : String(str)));
  return d.innerHTML;
}

function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(amount);
}

function formatDate(iso, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  if (withTime) return d.toLocaleString("es-MX");
  return d.toLocaleDateString("es-MX");
}

function shortId(id) {
  return id ? String(id).slice(0, 8) : "";
}

function isValidEmail(email) {
  return /^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$/.test(email);
}

function statusBadge(status) {
  const map = {
    pending:   ["badge-warning", "Pendiente"],
    completed: ["badge-success", "Completado"],
    cancelled: ["badge-danger",  "Cancelado"],
  };
  const [cls, label] = map[status] || ["badge-secondary", status];
  return `<span class="badge ${cls}">${label}</span>`;
}

function roleBadge(role) {
  const map = {
    admin:  ["badge-danger",  "Admin"],
    staff:  ["badge-info",    "Staff"],
    client: ["badge-secondary","Cliente"],
  };
  const [cls, label] = map[role] || ["badge-secondary", role];
  return `<span class="badge ${cls}">${label}</span>`;
}

function movementBadge(type) {
  const map = {
    in:         ["badge-success", "Entrada"],
    out:        ["badge-danger",  "Salida"],
    adjustment: ["badge-warning", "Ajuste"],
  };
  const [cls, label] = map[type] || ["badge-secondary", type];
  return `<span class="badge ${cls}">${label}</span>`;
}

function showToast(message, type = "info", duration = 3000) {
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

/** Modal generico. Retorna promesa que resuelve al confirmar o null al cancelar. */
function openModal({ title, bodyHtml, confirmText = "Guardar", cancelText = "Cancelar", onConfirm }) {
  return new Promise((resolve) => {
    const existing = document.getElementById("modal-backdrop");
    if (existing) existing.remove();

    const backdrop = document.createElement("div");
    backdrop.id = "modal-backdrop";
    backdrop.className = "modal-backdrop open";
    backdrop.innerHTML = `
      <div class="modal" role="dialog">
        <div class="modal-header">
          <h2>${escapeHtml(title)}</h2>
          <button class="modal-close" aria-label="Cerrar">&times;</button>
        </div>
        <div class="modal-body">${bodyHtml}</div>
        <div class="modal-footer">
          <button class="btn btn-ghost" data-action="cancel">${escapeHtml(cancelText)}</button>
          <button class="btn btn-primary" data-action="confirm">${escapeHtml(confirmText)}</button>
        </div>
      </div>`;
    document.body.appendChild(backdrop);

    const close = (value) => {
      backdrop.remove();
      resolve(value);
    };
    backdrop.querySelector(".modal-close").onclick = () => close(null);
    backdrop.querySelector('[data-action="cancel"]').onclick = () => close(null);
    backdrop.querySelector('[data-action="confirm"]').onclick = async () => {
      try {
        const val = onConfirm ? await onConfirm(backdrop.querySelector(".modal-body")) : true;
        if (val !== false) close(val);
      } catch (err) {
        showToast(err.message || "Error", "danger");
      }
    };
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(null); });
    document.addEventListener("keydown", function esc(e) {
      if (e.key === "Escape") {
        document.removeEventListener("keydown", esc);
        close(null);
      }
    });
  });
}

function confirmDialog(message, { confirmText = "Eliminar", danger = true } = {}) {
  return openModal({
    title: "Confirmar",
    bodyHtml: `<p>${escapeHtml(message)}</p>`,
    confirmText,
    onConfirm: () => true,
  }).then((v) => !!v);
}

function getFormValues(container) {
  const values = {};
  container.querySelectorAll("[name]").forEach((el) => {
    if (el.type === "checkbox") values[el.name] = el.checked;
    else if (el.type === "number") values[el.name] = el.value === "" ? null : Number(el.value);
    else values[el.name] = el.value === "" ? null : el.value;
  });
  return values;
}
