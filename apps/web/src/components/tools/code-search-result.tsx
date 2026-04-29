"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Search, RefreshCw, FileCode } from "lucide-react";
import { cn } from "@/lib/utils";
import { ToolRendererProps } from "@/lib/tools/tool-renderer-registry";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface CodeMatch {
  file: string;
  line: number;
  content: string;
  context?: string;
}

interface CodeSearchData {
  query: string;
  matches: CodeMatch[];
  totalMatches: number;
  repository?: string;
}

/**
 * Renders code search results as an interactive card
 */
export function CodeSearchResult({
  args,
  result,
  error,
  status,
  onRetry,
}: ToolRendererProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Parse result data
  const data = result as CodeSearchData | undefined;
  const query = data?.query ?? (args.query as string) ?? (args.q as string);
  const repository = data?.repository ?? (args.repository as string) ?? (args.repo as string);

  // Check if payload is large (> 5 matches)
  const isLargePayload = (data?.matches?.length ?? 0) > 5;

  return (
    <Card
      className={cn(
        "overflow-hidden transition-colors",
        status === "loading" && "border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30",
        status === "success" && "border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/30",
        status === "error" && "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30",
      )}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <Search
            className={cn(
              "h-5 w-5 mt-0.5 flex-shrink-0",
              status === "loading" && "text-blue-600 dark:text-blue-400 animate-pulse",
              status === "success" && "text-indigo-600 dark:text-indigo-400",
              status === "error" && "text-red-600 dark:text-red-400",
            )}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm" id="code-search-title">
              {status === "loading" && "Searching code..."}
              {status === "success" && `Search results for "${query}"`}
              {status === "error" && "Code search failed"}
            </h3>
            <div className="flex items-center gap-2 mt-1 text-xs text-zinc-600 dark:text-zinc-400">
              {repository && <span>in {repository}</span>}
              {status === "success" && data && (
                <span>
                  {data.totalMatches} {data.totalMatches === 1 ? "match" : "matches"} found
                </span>
              )}
            </div>
          </div>
        </div>

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
                aria-label="Retry code search"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            )}
          </div>
        )}

        {/* Expandable results */}
        {status === "success" && data?.matches && data.matches.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-indigo-700 dark:text-indigo-300 hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
              aria-expanded={isExpanded}
              aria-controls="code-search-results"
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              )}
              {isExpanded ? "Hide" : "Show"} results
              {isLargePayload && !isExpanded && " (large)"}
            </button>
            {isExpanded && (
              <div
                id="code-search-results"
                className="mt-2 space-y-2 max-h-96 overflow-y-auto"
                role="region"
                aria-label="Code search results"
              >
                {data.matches.map((match, index) => (
                  <div
                    key={index}
                    className="bg-indigo-100 dark:bg-indigo-900/50 p-3 rounded text-xs"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FileCode className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
                      <span className="font-medium text-indigo-900 dark:text-indigo-100">
                        {match.file}:{match.line}
                      </span>
                    </div>
                    <pre className="text-indigo-800 dark:text-indigo-200 overflow-x-auto">
                      {match.content}
                    </pre>
                    {match.context && (
                      <div className="mt-1 text-indigo-600 dark:text-indigo-400 italic">
                        {match.context}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* No results */}
        {status === "success" && data?.matches && data.matches.length === 0 && (
          <p className="mt-3 text-xs text-zinc-600 dark:text-zinc-400">No matches found</p>
        )}
      </div>
    </Card>
  );
}
