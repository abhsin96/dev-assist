"use client";

import { useEffect } from "react";
import { toAppError } from "@/lib/errors";
import { toast } from "@/lib/toast/toast-bus";

/**
 * Error boundary for authentication routes
 * Catches errors in the (auth) route group
 */
export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const appError = toAppError(error);

  useEffect(() => {
    // Log error for debugging
    console.error("[Auth Route Error]", {
      error: appError,
      digest: error.digest,
    });

    // Show toast notification
    toast.error(appError, {
      onRetry: reset,
    });
  }, [error, appError, reset]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md space-y-4 rounded-lg border border-destructive/20 bg-card p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">
            <svg
              className="h-6 w-6 text-destructive"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-destructive">
              Authentication Error
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {appError.detail || "An error occurred during authentication."}
            </p>
            {appError.traceId && (
              <p className="mt-2 text-xs text-muted-foreground">
                Trace ID:{" "}
                <code className="rounded bg-muted px-1 py-0.5">
                  {appError.traceId}
                </code>
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <button
            onClick={reset}
            className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
          <button
            onClick={() => (window.location.href = "/login")}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent"
          >
            Back to login
          </button>
        </div>
      </div>
    </div>
  );
}
