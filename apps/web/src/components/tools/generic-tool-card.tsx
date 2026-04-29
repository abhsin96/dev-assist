"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Wrench, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { ToolRendererProps } from "@/lib/tools/tool-renderer-registry";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

/**
 * Generic fallback renderer for tools without a specific card
 */
export function GenericToolCard({
  toolName,
  args,
  result,
  error,
  status,
  onRetry,
}: ToolRendererProps) {
  const [isArgsExpanded, setIsArgsExpanded] = useState(false);
  const [isResultExpanded, setIsResultExpanded] = useState(false);

  // Check if payloads are large
  const argsString = JSON.stringify(args, null, 2);
  const resultString = result ? JSON.stringify(result, null, 2) : "";
  const isArgsLarge = argsString.length > 500;
  const isResultLarge = resultString.length > 500;

  return (
    <Card
      className={cn(
        "overflow-hidden transition-colors",
        status === "loading" && "border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30",
        status === "success" && "border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/30",
        status === "error" && "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30",
      )}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <Wrench
            className={cn(
              "h-5 w-5 mt-0.5 flex-shrink-0",
              status === "loading" && "text-blue-600 dark:text-blue-400 animate-pulse",
              status === "success" && "text-zinc-600 dark:text-zinc-400",
              status === "error" && "text-red-600 dark:text-red-400",
            )}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm" id={`tool-${toolName}-title`}>
              {status === "loading" && `Calling ${toolName}...`}
              {status === "success" && `${toolName} completed`}
              {status === "error" && `${toolName} failed`}
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
              Tool: {toolName}
            </p>
          </div>
        </div>

        {/* Arguments */}
        {args && Object.keys(args).length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setIsArgsExpanded(!isArgsExpanded)}
              className="flex items-center gap-1 text-xs text-zinc-700 dark:text-zinc-300 hover:underline focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded"
              aria-expanded={isArgsExpanded}
              aria-controls={`tool-${toolName}-args`}
            >
              {isArgsExpanded ? (
                <ChevronDown className="h-3 w-3" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              )}
              {isArgsExpanded ? "Hide" : "Show"} arguments
              {isArgsLarge && !isArgsExpanded && " (large)"}
            </button>
            {isArgsExpanded && (
              <pre
                id={`tool-${toolName}-args`}
                className="mt-2 text-xs bg-zinc-100 dark:bg-zinc-800 p-3 rounded overflow-x-auto max-h-64 overflow-y-auto"
                role="region"
                aria-label="Tool arguments"
              >
                {argsString}
              </pre>
            )}
          </div>
        )}

        {/* Error message */}
        {status === "error" && error && (
          <div className="mt-3">
            <p className="text-xs text-red-700 dark:text-red-300">{error}</p>
            {onRetry && (
              <Button
                size="sm"
                variant="outline"
                onClick={onRetry}
                className="mt-2"
                aria-label={`Retry ${toolName}`}
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            )}
          </div>
        )}

        {/* Result */}
        {status === "success" && result !== undefined && result !== null && (
          <div className="mt-3">
            <button
              onClick={() => setIsResultExpanded(!isResultExpanded)}
              className="flex items-center gap-1 text-xs text-zinc-700 dark:text-zinc-300 hover:underline focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded"
              aria-expanded={isResultExpanded}
              aria-controls={`tool-${toolName}-result`}
            >
              {isResultExpanded ? (
                <ChevronDown className="h-3 w-3" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              )}
              {isResultExpanded ? "Hide" : "Show"} result
              {isResultLarge && !isResultExpanded && " (large)"}
            </button>
            {isResultExpanded && (
              <pre
                id={`tool-${toolName}-result`}
                className="mt-2 text-xs bg-zinc-100 dark:bg-zinc-800 p-3 rounded overflow-x-auto max-h-96 overflow-y-auto"
                role="region"
                aria-label="Tool result"
              >
                {resultString}
              </pre>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
