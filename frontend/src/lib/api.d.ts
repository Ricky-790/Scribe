// Type definitions for the JS api wrapper so callers get full IntelliSense.
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number);
}

export interface ApiRequestOptions {
  method?: string;
  token?: string;
  body?: unknown;
  signal?: AbortSignal;
}

export function apiRequest(
  path: string,
  options?: ApiRequestOptions,
): Promise<any>;

/** Opens an SSE stream; the caller feeds the response to readEventStream. */
export function openEventStream(
  path: string,
  options?: { token?: string; signal?: AbortSignal },
): Promise<Response>;

export function setUnauthorizedHandler(
  handler: (() => void) | null,
): void;
