"use client";

import { AlertCircle } from "lucide-react";

export interface TraceErrorProps {
  error: string | Error | Record<string, unknown>;
}

/**
 * Component for displaying error details in trace
 */
export function TraceErrorComponent({ error }: TraceErrorProps) {
  const errorMessage =
    typeof error === "string"
      ? error
      : error instanceof Error
        ? error.message
        : "Unknown error";

  const errorStack =
    error instanceof Error ? error.stack : undefined;

  const errorData =
    typeof error === "object" && !(error instanceof Error)
      ? error
      : undefined;

  return (
    <div className="border border-red-200 dark:border-red-800 rounded-lg overflow-hidden bg-red-50 dark:bg-red-950/30">
      <div className="flex items-start gap-2 px-3 py-2">
        <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-red-900 dark:text-red-100">
            Error
          </div>
          <div className="text-xs text-red-700 dark:text-red-300 mt-1">
            {errorMessage}
          </div>
        </div>
      </div>

      {/* Error stack trace */}
      {errorStack && (
        <div className="px-3 pb-3">
          <details className="text-xs">
            <summary className="cursor-pointer text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100">
              Stack trace
            </summary>
            <pre className="mt-2 bg-red-100 dark:bg-red-950/50 rounded p-2 overflow-x-auto">
              <code className="text-red-800 dark:text-red-200">
                {errorStack}
              </code>
            </pre>
          </details>
        </div>
      )}

      {/* Error data */}
      {errorData && (
        <div className="px-3 pb-3">
          <details className="text-xs">
            <summary className="cursor-pointer text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100">
              Error details
            </summary>
            <pre className="mt-2 bg-red-100 dark:bg-red-950/50 rounded p-2 overflow-x-auto">
              <code className="text-red-800 dark:text-red-200">
                {JSON.stringify(errorData, null, 2)}
              </code>
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
