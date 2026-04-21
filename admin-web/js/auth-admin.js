// admin-web/js/auth-admin.js — Gating del panel admin
// Solo usuarios con rol admin o staff pueden entrar.

function hasSession() { return !!window.apiAuth.getToken(); }

function getCurrentRole() {
  const u = window.apiAuth.getStoredUser();
  return u ? u.role : null;
}

function isAdmin() { return getCurrentRole() === "admin"; }
function isStaff() { return getCurrentRole() === "staff"; }
function isAdminOrStaff() { const r = getCurrentRole(); return r === "admin" || r === "staff"; }

/** Exige sesion admin/staff. Redirige a login si falta. */
async function requireAdmin(adminOnly = false) {
  if (!hasSession()) {
    window.location.href = "login.html";
    return null;
  }
  try {
    const user = await window.api.me();
    window.apiAuth.setStoredUser(user);
    const okRole = adminOnly ? user.role === "admin" : (user.role === "admin" || user.role === "staff");
    if (!okRole) {
      alert("No tienes permisos para acceder al panel.");
      window.apiAuth.clearSession();
      window.location.href = "login.html";
      return null;
    }
    return user;
  } catch (err) {
    console.error("[requireAdmin]", err);
    window.apiAuth.clearSession();
    window.location.href = "login.html";
    return null;
  }
}

function logout() {
  window.api.logout();
  window.location.href = "login.html";
}
