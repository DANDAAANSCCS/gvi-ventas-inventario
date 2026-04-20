// =============================================
// js/api-client.js - Wrapper fetch a la API REST del backend FastAPI
// =============================================
// Lee window.API_URL (definido en js/config.js) y maneja JWT en localStorage.
// Todas las llamadas pasan por aqui para:
//   - Anexar el header Authorization si hay token.
//   - Parsear JSON y lanzar Error con mensaje legible.
//   - Cerrar sesion automaticamente en 401 (excepto en login/register).

const TOKEN_KEY = "gv_token";
const USER_KEY = "gv_user";

function getApiBase() {
  const base = (window.API_URL || "").replace(/\/$/, "");
  if (!base) {
    console.warn("window.API_URL no definido. Usando localhost:8000.");
    return "http://localhost:8000";
  }
  return base;
}

// ── Token / sesion local ────────────────────────────────────────────────
function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

function setStoredUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}

function clearSession() {
  setToken(null);
  setStoredUser(null);
}

// ── Core fetch ───────────────────────────────────────────────────────────
async function apiFetch(path, { method = "GET", body, auth = true, silentAuth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${getApiBase()}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new Error("No se pudo conectar con el servidor. Revisa tu conexion.");
  }

  if (response.status === 401 && auth && !silentAuth) {
    clearSession();
    if (!window.location.pathname.endsWith("login.html") &&
        !window.location.pathname.endsWith("register.html")) {
      const next = encodeURIComponent(window.location.pathname.split("/").pop() || "index.html");
      window.location.href = `login.html?next=${next}`;
    }
    throw new Error("Sesion expirada. Inicia sesion nuevamente.");
  }

  if (response.status === 204) return null;

  let data = null;
  const ct = response.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    try { data = await response.json(); } catch { data = null; }
  } else {
    try { data = await response.text(); } catch { data = null; }
  }

  if (!response.ok) {
    const detail = (data && data.detail) || (typeof data === "string" ? data : "") || response.statusText;
    const msg = Array.isArray(detail)
      ? detail.map(d => d.msg || JSON.stringify(d)).join("; ")
      : detail;
    const error = new Error(msg || `Error HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }

  return data;
}

const apiGet = (path, opts) => apiFetch(path, { method: "GET", ...(opts || {}) });
const apiPost = (path, body, opts) => apiFetch(path, { method: "POST", body, ...(opts || {}) });
const apiPut = (path, body, opts) => apiFetch(path, { method: "PUT", body, ...(opts || {}) });
const apiDelete = (path, opts) => apiFetch(path, { method: "DELETE", ...(opts || {}) });

// ── API de alto nivel ───────────────────────────────────────────────────
const api = {
  // Auth
  async login(email, password) {
    const res = await apiPost("/auth/login", { email, password }, { auth: false });
    if (res && res.access_token) {
      setToken(res.access_token);
      setStoredUser(res.user);
    }
    return res;
  },
  async register(payload) {
    // payload: {email, password, name, phone?, address?}
    const res = await apiPost("/auth/register", payload, { auth: false });
    if (res && res.access_token) {
      setToken(res.access_token);
      setStoredUser(res.user);
    }
    return res;
  },
  async me() {
    const user = await apiGet("/auth/me");
    setStoredUser(user);
    return user;
  },
  logout() {
    clearSession();
  },
  forgotPassword: (email) =>
    apiPost("/auth/forgot-password", { email }, { auth: false }),
  resetPassword: (token, newPassword) =>
    apiPost("/auth/reset-password", { token, new_password: newPassword }, { auth: false }),

  // Cliente propio
  getMyClient: () => apiGet("/clients/me"),
  updateMyClient: (payload) => apiPut("/clients/me", payload),

  // Productos
  listProducts: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.category) qs.set("category", params.category);
    if (params.only_active !== undefined) qs.set("only_active", params.only_active);
    if (params.only_in_stock !== undefined) qs.set("only_in_stock", params.only_in_stock);
    if (params.limit) qs.set("limit", params.limit);
    if (params.offset) qs.set("offset", params.offset);
    const suffix = qs.toString() ? `?${qs}` : "";
    return apiGet(`/products${suffix}`, { auth: false });
  },
  getCategories: () => apiGet("/products/categories", { auth: false }),
  getProduct: (id) => apiGet(`/products/${id}`, { auth: false }),

  // Pedidos
  createOrder: (payload) => apiPost("/orders", payload),
  listMyOrders: () => apiGet("/orders/me"),
  getOrder: (id) => apiGet(`/orders/${id}`),
  cancelOrder: (id) => apiPost(`/orders/${id}/cancel`),

  // Reportes (admin/staff)
  salesReport: (days = 30) => apiGet(`/reports/sales?days=${days}`),
  topProducts: (days = 30, limit = 10) => apiGet(`/reports/top-products?days=${days}&limit=${limit}`),
};

// Exponer para uso global
window.api = api;
window.apiAuth = { getToken, setToken, getStoredUser, setStoredUser, clearSession };
