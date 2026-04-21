// admin-web/js/layout.js — Sidebar comun inyectado en cada pagina

const SIDEBAR_LINKS = [
  { href: "dashboard.html",  icon: "📊", label: "Dashboard",  role: "staff" },
  { href: "products.html",   icon: "📦", label: "Productos",  role: "staff" },
  { href: "orders.html",     icon: "🛒", label: "Pedidos",    role: "staff" },
  { href: "inventory.html",  icon: "📋", label: "Inventario", role: "staff" },
  { href: "clients.html",    icon: "👥", label: "Clientes",   role: "staff" },
  { href: "daily-ops.html",  icon: "💰", label: "Caja",       role: "staff" },
  { href: "reports.html",    icon: "📈", label: "Reportes",   role: "staff" },
  { href: "users.html",      icon: "🔑", label: "Usuarios",   role: "admin" },
];

function renderSidebar(user) {
  const container = document.getElementById("sidebar");
  if (!container) return;
  const current = location.pathname.split("/").pop() || "dashboard.html";
  const role = user ? user.role : "staff";
  const allowed = SIDEBAR_LINKS.filter(l => role === "admin" || l.role !== "admin");
  container.innerHTML = `
    <div class="sidebar-brand">
      🏪 GVI Admin
      <small>${escapeHtml(user ? user.email : "")}</small>
    </div>
    <nav>
      ${allowed.map(l => `
        <a href="${l.href}" class="${current === l.href ? "active" : ""}">
          <span>${l.icon}</span> ${escapeHtml(l.label)}
        </a>
      `).join("")}
    </nav>
    <div class="sidebar-footer">
      Rol: ${roleBadge(role)}
      <button onclick="logout()">Cerrar sesión</button>
    </div>
  `;
}
