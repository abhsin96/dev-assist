"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileText, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { ToolRendererProps } from "@/lib/tools/tool-renderer-registry";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface DocDiffData {
  fileName: string;
  oldVersion?: string;
  newVersion?: string;
  diff?: string;
  additions: number;
  deletions: number;
  url?: string;
}

/**
 * Renders a documentation diff as an interactive card
 */
export function DocDiffCard({
  args,
  result,
  error,
  status,
  onRetry,
}: ToolRendererProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Parse result data
  const data = result as DocDiffData | undefined;
  const fileName = data?.fileName ?? (args.file_name as string) ?? (args.fileName as string) ?? (args.file as string);

  // Check if payload is large (> 1000 chars)
  const isLargePayload = (data?.diff?.length ?? 0) > 1000;

  return (
    <Card
      className={cn(
        "overflow-hidden transition-colors",
        status === "loading" && "border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30",
        status === "success" && "border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30",
        status === "error" && "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30",
      )}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <FileText
            className={cn(
              "h-5 w-5 mt-0.5 flex-shrink-0",
              status === "loading" && "text-blue-600 dark:text-blue-400 animate-pulse",
              status === "success" && "text-amber-600 dark:text-amber-400",
              status === "error" && "text-red-600 dark:text-red-400",
            )}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm" id={`doc-${fileName}-title`}>
              {status === "loading" && "Fetching documentation diff..."}
              {status === "success" && (
                <span>
                  {data?.url ? (
                    <a
                      href={data.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline"
                      aria-describedby={`doc-${fileName}-title`}
                    >
                      {fileName}
                    </a>
                  ) : (
                    fileName
                  )}
                </span>
              )}
              {status === "error" && "Failed to fetch documentation diff"}
            </h3>
            <div className="flex items-center gap-2 mt-1 text-xs text-zinc-600 dark:text-zinc-400">
              {data?.oldVersion && data?.newVersion && (
                <span>
                  {data.oldVersion} → {data.newVersion}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Stats */}
        {status === "success" && data && (
          <div className="flex items-center gap-4 mt-3 text-xs">
            <span className="text-green-600 dark:text-green-400">
              +{data.additions} additions
            </span>
            <span className="text-red-600 dark:text-red-400">
              -{data.deletions} deletions
            </span>
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
                aria-label="Retry fetching documentation diff"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            )}
          </div>
        )}

        {/* Expandable diff */}
        {status === "success" && data?.diff && (
          <div className="mt-3">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300 hover:underline focus:outline-none focus:ring-2 focus:ring-amber-500 rounded"
              aria-expanded={isExpanded}
              aria-controls={`doc-${fileName}-diff`}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              )}
              {isExpanded ? "Hide" : "Show"} diff
              {isLargePayload && !isExpanded && " (large)"}
            </button>
            {isExpanded && (
              <pre
                id={`doc-${fileName}-diff`}
                className="mt-2 text-xs bg-amber-100 dark:bg-amber-900/50 p-3 rounded overflow-x-auto max-h-96 overflow-y-auto"
                role="region"
                aria-label="Documentation diff"
              >
                {data.diff}
              </pre>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
