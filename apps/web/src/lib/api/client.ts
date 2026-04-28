"use client";

import * as Sentry from "@sentry/nextjs";

export const REQUEST_ID_HEADER = "X-Request-Id";

/**
 * Thin fetch wrapper that:
 * - Attaches a client-generated or Sentry-propagated trace_id as X-Request-Id
 * - Reads X-Request-Id back from responses and tags the current Sentry scope
 */
export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  // Use the active Sentry trace id when available, otherwise generate one
  const traceId =
    Sentry.getCurrentScope().getPropagationContext().traceId ??
    crypto.randomUUID();

  const headers = new Headers(init.headers);
  headers.set(REQUEST_ID_HEADER, traceId);
  headers.set("Content-Type", "application/json");

  const response = await fetch(input, { ...init, headers });

  // Tag the current scope so Sentry events carry the backend trace_id
  const responseTraceId = response.headers.get(REQUEST_ID_HEADER);
  if (responseTraceId) {
    Sentry.getCurrentScope().setTag("trace_id", responseTraceId);
  }

  return response;
}
