// =============================================
// js/history.js - Historial de compras del cliente
// =============================================
// Consume GET /orders/me, GET /orders/{id}, POST /orders/{id}/cancel.

let allOrders = [];
let clientProfile = null;
const orderDetailCache = new Map();

document.addEventListener("DOMContentLoaded", async () => {
  const auth = await requireAuth("login.html?next=history.html");
  if (!auth) return;

  clientProfile = await getClientProfile();
  if (!clientProfile) {
    document.getElementById("orders-container").innerHTML =
      `<div class="alert alert-warning">
        No encontramos tu perfil de cliente.
        <a href="register.html">Completa tu registro</a>.
       </div>`;
    return;
  }

  await loadOrders();
});

async function loadOrders() {
  showSpinner("orders-container");
  try {
    const data = await window.api.listMyOrders();
    allOrders = (data || []).map(o => ({ ...o, total: Number(o.total) }));
    renderSummaryCards(allOrders);
    renderOrders(allOrders);
  } catch (err) {
    document.getElementById("orders-container").innerHTML =
      `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function renderSummaryCards(orders) {
  const total = orders.reduce((s, o) => s + Number(o.total), 0);
  const completed = orders.filter(o => o.status === "completed").length;
  const pending = orders.filter(o => o.status === "pending").length;

  document.getElementById("summary-cards").innerHTML = [
    ["🧾 Total Pedidos", orders.length, "var(--primary)"],
    ["✅ Completados", completed, "var(--success)"],
    ["⏳ Pendientes", pending, "var(--warning)"],
    ["💰 Gasto Total", formatCurrency(total), "var(--danger)"],
  ].map(([label, val, color]) => `
    <div class="card">
      <div class="card-body" style="text-align:center">
        <div style="font-size:.85rem;color:var(--text-light);margin-bottom:4px">${label}</div>
        <div style="font-size:1.6rem;font-weight:700;color:${color}">${val}</div>
      </div>
    </div>`).join("");
}

function renderOrders(orders) {
  const container = document.getElementById("orders-container");

  if (orders.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <h3>Sin pedidos</h3>
        <p>Aun no has realizado ninguna compra</p>
        <a href="index.html" class="btn btn-primary" style="margin-top:12px">
          🛍️ Ver Catalogo
        </a>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Pedido #</th>
            <th>Fecha</th>
            <th>Total</th>
            <th>Metodo de Pago</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${orders.map(o => `
            <tr>
              <td><code>${shortOrderId(o.id)}</code></td>
              <td>${formatDate(o.created_at)}</td>
              <td><strong>${formatCurrency(o.total)}</strong></td>
              <td>${escapeHtml(o.payment_method || "—")}</td>
              <td>${statusBadge(o.status)}</td>
              <td>
                <button class="btn btn-primary btn-sm"
                  onclick="viewOrderDetail('${o.id}')">
                  🔍 Ver Detalle
                </button>
                ${o.status === "pending"
                  ? `<button class="btn btn-danger btn-sm"
                       onclick="cancelOrder('${o.id}')">
                       ❌ Cancelar
                     </button>` : ""}
              </td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function shortOrderId(id) {
  const s = String(id);
  return s.length > 8 ? s.slice(0, 8).toUpperCase() : s;
}

function applyFilters() {
  const status = document.getElementById("status-filter").value;
  const dateFrom = document.getElementById("date-from").value;
  const dateTo = document.getElementById("date-to").value;

  let filtered = [...allOrders];

  if (status) filtered = filtered.filter(o => o.status === status);
  if (dateFrom) filtered = filtered.filter(o => o.created_at.slice(0, 10) >= dateFrom);
  if (dateTo) filtered = filtered.filter(o => o.created_at.slice(0, 10) <= dateTo);

  renderSummaryCards(filtered);
  renderOrders(filtered);
}

function resetFilters() {
  document.getElementById("status-filter").value = "";
  document.getElementById("date-from").value = "";
  document.getElementById("date-to").value = "";
  renderSummaryCards(allOrders);
  renderOrders(allOrders);
}

async function viewOrderDetail(orderId) {
  document.getElementById("detail-title").textContent =
    `Pedido #${shortOrderId(orderId)}`;
  document.getElementById("detail-body").innerHTML = '<div class="spinner"></div>';
  document.getElementById("detail-modal").style.display = "flex";

  try {
    let detail = orderDetailCache.get(String(orderId));
    if (!detail) {
      detail = await window.api.getOrder(orderId);
      orderDetailCache.set(String(orderId), detail);
    }

    const items = detail.items || [];
    const total = items.reduce((s, i) => s + Number(i.unit_price) * i.quantity, 0);

    document.getElementById("detail-body").innerHTML = `
      <div style="margin-bottom:1rem">
        <p><strong>Fecha:</strong> ${formatDate(detail.created_at)}</p>
        <p><strong>Estado:</strong> ${statusBadge(detail.status)}</p>
        <p><strong>Pago:</strong> ${escapeHtml(detail.payment_method || "—")}</p>
        ${detail.notes ? `<p><strong>Notas:</strong> ${escapeHtml(detail.notes)}</p>` : ""}
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Producto</th>
              <th>P. Unitario</th>
              <th>Cantidad</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(item => `
              <tr>
                <td>${escapeHtml(item.product_name || "N/A")}</td>
                <td>${formatCurrency(item.unit_price)}</td>
                <td>${item.quantity}</td>
                <td>${formatCurrency(Number(item.unit_price) * item.quantity)}</td>
              </tr>`).join("")}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" style="text-align:right;font-weight:700">Total:</td>
              <td style="font-weight:700;color:var(--success)">
                ${formatCurrency(total)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>`;
  } catch (err) {
    document.getElementById("detail-body").innerHTML =
      `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function closeDetailModal(event) {
  if (event.target === document.getElementById("detail-modal")) {
    document.getElementById("detail-modal").style.display = "none";
  }
}

async function cancelOrder(orderId) {
  if (!confirm("Seguro que deseas cancelar este pedido?")) return;
  try {
    await window.api.cancelOrder(orderId);
    orderDetailCache.delete(String(orderId));
    showToast("Pedido cancelado correctamente.", "success");
    await loadOrders();
  } catch (err) {
    showToast("Error al cancelar: " + err.message, "danger");
  }
}
