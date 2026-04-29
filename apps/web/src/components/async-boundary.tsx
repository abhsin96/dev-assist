"use client";

import React, { Suspense } from "react";
import { ErrorBoundary, type FallbackProps } from "react-error-boundary";
import { toAppError } from "@/lib/errors";
import { toast } from "@/lib/toast/toast-bus";

/**
 * Props for AsyncBoundary component
 */
interface AsyncBoundaryProps {
  /**
   * Child components to render
   */
  children: React.ReactNode;

  /**
   * Loading fallback component
   */
  loadingFallback?: React.ReactNode;

  /**
   * Error fallback component (optional, uses default if not provided)
   */
  errorFallback?: React.ComponentType<FallbackProps>;

  /**
   * Callback when an error occurs
   */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;

  /**
   * Callback for retry action
   */
  onRetry?: () => void;

  /**
   * Whether to show toast notifications for errors
   */
  showToast?: boolean;
}

/**
 * Default loading fallback
 */
function DefaultLoadingFallback() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="flex flex-col items-center gap-2">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

/**
 * Default error fallback component
 */
function DefaultErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const appError = toAppError(error);

  return (
    <div className="flex items-center justify-center p-8">
      <div className="max-w-md rounded-lg border border-destructive/20 bg-destructive/5 p-6">
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
            <h3 className="font-semibold text-destructive">
              Something went wrong
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {appError.detail || "An unexpected error occurred"}
            </p>
            {appError.traceId && (
              <p className="mt-2 text-xs text-muted-foreground">
                Trace ID: {appError.traceId}
              </p>
            )}
            <div className="mt-4 flex gap-2">
              <button
                onClick={resetErrorBoundary}
                className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Try again
              </button>
              {appError.traceId && (
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(appError.traceId!);
                    toast.success("Trace ID copied");
                  }}
                  className="rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent"
                >
                  Copy Trace ID
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * AsyncBoundary - Combines Suspense and ErrorBoundary for async client islands
 * Wraps async components with loading and error states
 */
export function AsyncBoundary({
  children,
  loadingFallback = <DefaultLoadingFallback />,
  errorFallback: ErrorFallback = DefaultErrorFallback,
  onError,
  onRetry,
  showToast = true,
}: AsyncBoundaryProps) {
  const handleError = (error: unknown, errorInfo: React.ErrorInfo) => {
    // Convert to AppError and show toast if enabled
    if (showToast) {
      const appError = toAppError(error);
      toast.error(appError, {
        onRetry,
      });
    }

    // Call custom error handler if provided
    if (onError && error instanceof Error) {
      onError(error, errorInfo);
    }

    // Log to console for debugging
    console.error("[AsyncBoundary] Error caught:", error, errorInfo);
  };

  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={handleError}
      onReset={onRetry}
    >
      <Suspense fallback={loadingFallback}>{children}</Suspense>
    </ErrorBoundary>
  );
}
