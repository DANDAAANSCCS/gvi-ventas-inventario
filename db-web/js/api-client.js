// db-web/js/api-client.js — Cliente especifico para DB manager (endpoints /admin-db/*)

const TOKEN_KEY = "gv_dbmgr_token";
const USER_KEY  = "gv_dbmgr_user";

function getApiBase() {
  const base = (window.API_URL || "").replace(/\/$/, "");
  if (!base) {
    console.warn("window.API_URL no definido. Usando localhost:8100.");
    return "http://localhost:8100";
  }
  return base;
}

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); }
function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}
function setStoredUser(u) { u ? localStorage.setItem(USER_KEY, JSON.stringify(u)) : localStorage.removeItem(USER_KEY); }
function clearSession() { setToken(null); setStoredUser(null); }

async function apiFetch(path, { method = "GET", body, auth = true, silentAuth = false, raw = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(`${getApiBase()}${path}`, {
      method, headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new Error("No se pudo conectar con el servidor.");
  }
  if (response.status === 401 && auth && !silentAuth) {
    clearSession();
    if (!window.location.pathname.endsWith("login.html")) {
      window.location.href = "login.html";
    }
    throw new Error("Sesion expirada.");
  }
  if (response.status === 204) return null;
  if (raw) return response;

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
const apiPatch = (path, body, opts) => apiFetch(path, { method: "PATCH", body, ...(opts || {}) });
const apiDelete = (path, opts) => apiFetch(path, { method: "DELETE", ...(opts || {}) });

function qs(params) {
  const q = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

const api = {
  login: async (email, password) => {
    const res = await apiPost("/auth/login", { email, password }, { auth: false });
    if (res && res.access_token) {
      setToken(res.access_token);
      setStoredUser(res.user);
    }
    return res;
  },
  me: () => apiGet("/auth/me"),
  logout: () => clearSession(),

  // DB manager
  tables:   ()                       => apiGet("/admin-db/tables"),
  columns:  (table)                  => apiGet(`/admin-db/tables/${table}/columns`),
  rows:     (table, params = {})     => apiGet(`/admin-db/tables/${table}/rows${qs(params)}`),
  insertRow:(table, body)            => apiPost(`/admin-db/tables/${table}/rows`, body),
  updateRow:(table, pk, body)        => apiPatch(`/admin-db/tables/${table}/rows/${pk}`, body),
  deleteRow:(table, pk)              => apiDelete(`/admin-db/tables/${table}/rows/${pk}`),
  query:    (sql, allowDestructive = false, params = null) =>
              apiPost("/admin-db/query", { sql, allow_destructive: allowDestructive, params }),
  exportUrl:(table) => `${getApiBase()}/admin-db/tables/${table}/export.csv`,
};

window.api = api;
window.apiAuth = { getToken, setToken, getStoredUser, setStoredUser, clearSession, getApiBase };
