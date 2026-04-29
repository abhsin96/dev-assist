"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { ToolRendererProps } from "@/lib/tools/tool-renderer-registry";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface IssueData {
  issueNumber: number;
  title: string;
  author: string;
  repository: string;
  state: "open" | "closed";
  labels: string[];
  body?: string;
  url?: string;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * Renders a GitHub issue as an interactive card
 */
export function IssueCard({
  args,
  result,
  error,
  status,
  onRetry,
}: ToolRendererProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Parse result data
  const data = result as IssueData | undefined;
  const issueNumber = data?.issueNumber ?? (args.issue_number as number) ?? (args.issueNumber as number);
  const repository = data?.repository ?? (args.repository as string) ?? (args.repo as string);

  // Check if payload is large (> 1000 chars)
  const isLargePayload = (data?.body?.length ?? 0) > 1000;

  return (
    <Card
      className={cn(
        "overflow-hidden transition-colors",
        status === "loading" && "border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30",
        status === "success" && "border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-950/30",
        status === "error" && "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30",
      )}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <AlertCircle
            className={cn(
              "h-5 w-5 mt-0.5 flex-shrink-0",
              status === "loading" && "text-blue-600 dark:text-blue-400 animate-pulse",
              status === "success" && data?.state === "open" && "text-purple-600 dark:text-purple-400",
              status === "success" && data?.state === "closed" && "text-green-600 dark:text-green-400",
              status === "error" && "text-red-600 dark:text-red-400",
            )}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm" id={`issue-${issueNumber}-title`}>
              {status === "loading" && "Fetching issue..."}
              {status === "success" && data?.title && (
                <a
                  href={data.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                  aria-describedby={`issue-${issueNumber}-title`}
                >
                  {data.title}
                </a>
              )}
              {status === "error" && "Failed to fetch issue"}
            </h3>
            <div className="flex items-center gap-2 mt-1 text-xs text-zinc-600 dark:text-zinc-400">
              {repository && (
                <span>
                  {repository}#{issueNumber}
                </span>
              )}
              {data?.author && <span>by {data.author}</span>}
              {data?.state && (
                <span
                  className={cn(
                    "px-2 py-0.5 rounded-full font-medium",
                    data.state === "open" && "bg-purple-200 dark:bg-purple-800 text-purple-900 dark:text-purple-100",
                    data.state === "closed" && "bg-green-200 dark:bg-green-800 text-green-900 dark:text-green-100",
                  )}
                >
                  {data.state}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Labels */}
        {status === "success" && data?.labels && data.labels.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {data.labels.map((label, index) => (
              <span
                key={index}
                className="px-2 py-0.5 text-xs rounded-full bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
              >
                {label}
              </span>
            ))}
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
                aria-label="Retry fetching issue"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            )}
          </div>
        )}

        {/* Expandable body */}
        {status === "success" && data?.body && (
          <div className="mt-3">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-purple-700 dark:text-purple-300 hover:underline focus:outline-none focus:ring-2 focus:ring-purple-500 rounded"
              aria-expanded={isExpanded}
              aria-controls={`issue-${issueNumber}-body`}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              )}
              {isExpanded ? "Hide" : "Show"} description
              {isLargePayload && !isExpanded && " (large)"}
            </button>
            {isExpanded && (
              <div
                id={`issue-${issueNumber}-body`}
                className="mt-2 text-xs bg-purple-100 dark:bg-purple-900/50 p-3 rounded max-h-96 overflow-y-auto prose prose-sm dark:prose-invert"
                role="region"
                aria-label="Issue description"
              >
                {data.body}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
