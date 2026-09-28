// Thin fetch wrapper that always points at API_BASE_URL, attaches the JWT
// (unless explicitly skipped — signup/signin), and normalizes 4xx errors into
// { detail: string } so callers can display them.

import { API_BASE_URL } from "../config.js";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
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
    const detail =
      (data && typeof data === "object" && data.detail) ||
      (typeof data === "string" && data) ||
      `Request failed with status ${res.status}`;
    throw new ApiError(detail, res.status);
  }

  return data;
}
