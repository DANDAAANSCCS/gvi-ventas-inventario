// db-web/js/auth-admin.js — solo admins pueden entrar al DB manager

function hasSession() { return !!window.apiAuth.getToken(); }

async function requireAdminOnly() {
  if (!hasSession()) { window.location.href = "login.html"; return null; }
  try {
    const user = await window.api.me();
    window.apiAuth.setStoredUser(user);
    if (user.role !== "admin") {
      alert("Solo usuarios admin pueden acceder al DB manager.");
      window.apiAuth.clearSession();
      window.location.href = "login.html";
      return null;
    }
    return user;
  } catch (err) {
    console.error("[requireAdminOnly]", err);
    window.apiAuth.clearSession();
    window.location.href = "login.html";
    return null;
  }
}

function logout() { window.api.logout(); window.location.href = "login.html"; }
