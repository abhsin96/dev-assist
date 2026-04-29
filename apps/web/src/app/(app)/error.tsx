"use client";

import { useEffect } from "react";
import { toAppError } from "@/lib/errors";
import { toast } from "@/lib/toast/toast-bus";

/**
 * Error boundary for the main app routes
 * Catches errors in the (app) route group
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const appError = toAppError(error);

  useEffect(() => {
    // Log error for debugging
    console.error("[App Route Error]", {
      error: appError,
      digest: error.digest,
    });

    // Show toast notification
    toast.error(appError, {
      onRetry: reset,
    });
  }, [error, appError, reset]);

  return (
    <div className="flex min-h-[400px] items-center justify-center p-4">
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
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-destructive">
              Something went wrong
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {appError.detail || "An error occurred while loading this page."}
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

        <div className="flex gap-2">
          <button
            onClick={reset}
            className="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
          {appError.traceId && (
            <button
              onClick={() => {
                navigator.clipboard.writeText(appError.traceId!);
                toast.success("Trace ID copied");
              }}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent"
            >
              Copy Trace ID
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
