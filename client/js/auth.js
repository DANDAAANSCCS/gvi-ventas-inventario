// =============================================
// js/auth.js - Manejo de sesion cliente contra la API REST
// =============================================
// Funciones compartidas por todas las paginas.
// La sesion vive en localStorage (JWT + user) y se maneja via api-client.js.

// ── Sesion ─────────────────────────────────────────────────────────────
function hasSession() {
  return !!window.apiAuth.getToken();
}

/**
 * Garantiza que haya un token valido, cargando /auth/me si no hay usuario cacheado.
 * Redirige a login si el token es invalido o falta.
 */
async function requireAuth(redirectTo = "login.html") {
  if (!hasSession()) {
    window.location.href = redirectTo;
    return null;
  }
  try {
    let user = window.apiAuth.getStoredUser();
    if (!user) user = await window.api.me();
    return { user };
  } catch (err) {
    window.apiAuth.clearSession();
    window.location.href = redirectTo;
    return null;
  }
}

/**
 * Redirige si ya hay sesion (para paginas login/registro).
 */
async function redirectIfAuth(redirectTo = "index.html") {
  if (!hasSession()) return;
  try {
    await window.api.me();
    window.location.href = redirectTo;
  } catch {
    window.apiAuth.clearSession();
  }
}

function logout() {
  window.api.logout();
  window.location.href = "login.html";
}

/**
 * Pinta los links del navbar segun el estado de sesion.
 */
function updateNavbar() {
  const authLinks = document.querySelectorAll("[data-auth-only]");
  const guestLinks = document.querySelectorAll("[data-guest-only]");
  const userDisplay = document.getElementById("user-display");
  const user = window.apiAuth.getStoredUser();

  if (hasSession()) {
    authLinks.forEach(el => (el.style.display = ""));
    guestLinks.forEach(el => (el.style.display = "none"));
    if (userDisplay && user) {
      userDisplay.textContent = (user.email || "").split("@")[0];
    }
  } else {
    authLinks.forEach(el => (el.style.display = "none"));
    guestLinks.forEach(el => (el.style.display = ""));
    if (userDisplay) userDisplay.textContent = "";
  }
}

/**
 * Devuelve el perfil del cliente autenticado (GET /clients/me).
 */
async function getClientProfile() {
  if (!hasSession()) return null;
  try {
    return await window.api.getMyClient();
  } catch (err) {
    if (err.status === 404) return null;
    console.error("Error al obtener perfil:", err);
    return null;
  }
}

document.addEventListener("DOMContentLoaded", updateNavbar);
