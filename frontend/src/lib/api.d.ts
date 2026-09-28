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
