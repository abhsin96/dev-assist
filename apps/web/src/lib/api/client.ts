"use client";

import * as Sentry from "@sentry/nextjs";

export const REQUEST_ID_HEADER = "X-Request-Id";

async function getApiToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/token");
    if (!res.ok) return null;
    const data = (await res.json()) as { token?: string };
    return data.token ?? null;
  } catch {
    return null;
  }
}

/**
 * Thin fetch wrapper that:
 * - Attaches a client-generated or Sentry-propagated trace_id as X-Request-Id
 * - Fetches a short-lived API JWT from the BFF and attaches it as Authorization
 * - Reads X-Request-Id back from responses and tags the current Sentry scope
 */
export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const traceId =
    Sentry.getCurrentScope().getPropagationContext().traceId ??
    crypto.randomUUID();

  const headers = new Headers(init.headers);
  headers.set(REQUEST_ID_HEADER, traceId);
  headers.set("Content-Type", "application/json");

  const token = await getApiToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(input, { ...init, headers });

  const responseTraceId = response.headers.get(REQUEST_ID_HEADER);
  if (responseTraceId) {
    Sentry.getCurrentScope().setTag("trace_id", responseTraceId);
  }

  return response;
}
