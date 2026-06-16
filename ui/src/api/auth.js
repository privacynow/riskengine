const AUTH_STORAGE_KEY = "decisionEngineAdminToken";

export function getStoredAdminToken() {
  return sessionStorage.getItem(AUTH_STORAGE_KEY) || "";
}

export function setStoredAdminToken(token) {
  if (token) {
    sessionStorage.setItem(AUTH_STORAGE_KEY, token);
  } else {
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

export function adminAuthHeaders(extra) {
  const token = getStoredAdminToken();
  if (!token) {
    return { ...(extra || {}) };
  }
  return { Authorization: "Bearer " + token, ...(extra || {}) };
}

export { AUTH_STORAGE_KEY };
