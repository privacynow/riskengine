import { adminAuthHeaders } from "./auth.js";

export function request(url, options = {}) {
  return fetch(url, {
    method: options.method || "GET",
    headers: {
      ...adminAuthHeaders(),
      ...(options.headers || {}),
    },
    body: options.body,
  });
}

export async function json(url, options = {}) {
  const response = await request(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed with status " + response.status);
  }
  return response.json();
}

function paginated(path, params) {
  const search = new URLSearchParams(params || {});
  const qs = search.toString();
  return request(qs ? path + "?" + qs : path).then((r) => r.json());
}

export const api = {
  request,
  json,
  paginated,
  tenants: {
    list: (page, size) => paginated("/ui/tenants", { page, size }),
    search: (q, page, size) => paginated("/ui/search_tenants", { q, page, size }),
    create: (payload) =>
      json("/ui/tenants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
  },
  checkpoints: {
    list: (params) => paginated("/ui/checkpoints", params),
    search: (params) => paginated("/ui/search_checkpoints", params),
  },
  signals: {
    list: (params) => paginated("/ui/signals", params),
    search: (params) => paginated("/ui/search_signals", params),
  },
  decisions: {
    search: (params) => paginated("/ui/search_decisions", params),
    get: (id) => json("/decisions/" + id),
    test: (payload) =>
      json("/ui/test_decisions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
  },
  signalLogs: {
    search: (params) => paginated("/ui/search_signal_logs", params),
  },
};

export default api;
