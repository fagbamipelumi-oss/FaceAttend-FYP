const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

function authHeaders() {
  const token = localStorage.getItem("admin_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(response) {
  if (!response.ok) {
    let detail;
    try {
      const body = await response.json();
      detail = body.detail;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function apiGet(path, params) {
  const url = new URL(API_BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url, { headers: { ...authHeaders() } });
  return handle(res);
}

export async function apiPostJson(path, body) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return handle(res);
}

export async function apiPostForm(path, formData) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
  return handle(res);
}

export async function login(username, password) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);
  const res = await fetch(API_BASE + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  return handle(res);
}
