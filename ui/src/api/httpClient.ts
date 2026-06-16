import { AUTH_STORAGE_KEY } from "@/app/config";
import { ApiError, parseApiErrorBody } from "@/api/errors";

export type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  signal?: AbortSignal;
};

function getStoredToken(): string {
  return sessionStorage.getItem(AUTH_STORAGE_KEY) || "";
}

export function setStoredToken(token: string): void {
  if (token) sessionStorage.setItem(AUTH_STORAGE_KEY, token);
  else sessionStorage.removeItem(AUTH_STORAGE_KEY);
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = { ...(extra || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function httpRequest(
  path: string,
  options: RequestOptions = {}
): Promise<Response> {
  const headers = authHeaders(options.headers);
  return fetch(path, {
    method: options.method || "GET",
    headers,
    body: options.body,
    signal: options.signal,
  });
}

export async function httpJson<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const response = await httpRequest(path, options);
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(
      parseApiErrorBody(body),
      response.status,
      body
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function buildQuery(
  params: Record<string, string | number | boolean | undefined | null>
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}
