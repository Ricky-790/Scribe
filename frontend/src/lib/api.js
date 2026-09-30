// Thin fetch wrapper that always points at API_BASE_URL, attaches the JWT
// (unless explicitly skipped — signup/signin), and normalizes 4xx errors into
// { detail: string } so callers can display them.

import { API_BASE_URL } from "../config.js";

const TOKEN_STORAGE_KEY = "access_token";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Fired when the server rejects our token so the app can drop the stale
// session instead of leaving the user signed in against a dead account.
let onUnauthorized = null;

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

function handleUnauthorized() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* storage may be unavailable (private mode) */
  }
  onUnauthorized?.();
}

async function parseBody(res) {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
  try {
    return await res.text();
  } catch {
    return null;
  }
}

export async function apiRequest(
  path,
  { method = "GET", token, body, signal } = {},
) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  const data = await parseBody(res);

  if (!res.ok) {
    if (res.status === 401) handleUnauthorized();
    const detail =
      (data && typeof data === "object" && data.detail) ||
      (typeof data === "string" && data) ||
      `Request failed with status ${res.status}`;
    throw new ApiError(detail, res.status);
  }

  return data;
}

/**
 * Open a server-sent-events stream. Returns the raw Response so the caller
 * can hand it to readEventStream.
 */
export async function openEventStream(path, { token, signal } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers,
    signal,
  });

  if (!res.ok) {
    const data = await parseBody(res);
    if (res.status === 401) handleUnauthorized();
    const detail =
      (data && typeof data === "object" && data.detail) ||
      (typeof data === "string" && data) ||
      `Request failed with status ${res.status}`;
    throw new ApiError(detail, res.status);
  }

  return res;
}
