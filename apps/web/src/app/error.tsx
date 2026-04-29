"use client";

import { useEffect } from "react";
import { toAppError } from "@/lib/errors";
import { toast } from "@/lib/toast/toast-bus";

/**
 * Root-level error boundary for the entire application
 * Catches errors that bubble up from any route
 * Note: This renders inside the root layout, so it should NOT contain <html> or <body> tags.
 * For a true global error boundary that replaces the root layout, use global-error.tsx instead.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const appError = toAppError(error);

  useEffect(() => {
    // Log error to monitoring service (e.g., Sentry)
    console.error("[Global Error]", {
      error: appError,
      digest: error.digest,
    });

    // Show toast notification
    toast.error(appError, {
      onRetry: reset,
    });
  }, [error, appError, reset]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-destructive/20 bg-card p-8 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            <svg
              className="h-10 w-10 text-destructive"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Application Error
            </h1>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {appError.detail ||
              "An unexpected error occurred in the application."}
          </p>
          {appError.code && (
            <p className="text-xs text-muted-foreground">
              Error Code:{" "}
              <code className="rounded bg-muted px-1 py-0.5">
                {appError.code}
              </code>
            </p>
          )}
          {appError.traceId && (
            <p className="text-xs text-muted-foreground">
              Trace ID:{" "}
              <code className="rounded bg-muted px-1 py-0.5">
                {appError.traceId}
              </code>
            </p>
          )}
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            onClick={reset}
            className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
          <button
            onClick={() => (window.location.href = "/")}
            className="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            Go home
          </button>
        </div>

        {appError.traceId && (
          <button
            onClick={() => {
              navigator.clipboard.writeText(appError.traceId!);
              toast.success("Trace ID copied to clipboard");
            }}
            className="w-full text-xs text-muted-foreground hover:text-foreground"
          >
            Copy trace ID for support
          </button>
        )}
      </div>
    </div>
  );
}
