"use client";

import { useState } from "react";
import { ChevronRight, Clock, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceStep } from "./types";
import { TraceToolComponent } from "./trace-tool";
import { TraceErrorComponent } from "./trace-error";

export interface TraceStepProps {
  step: TraceStep;
  depth: number;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

/**
 * Individual trace step component
 * Shows agent name, tool, duration, status, and expandable args/result
 */
export function TraceStepComponent({
  step,
  depth,
  isExpanded,
  onToggleExpand,
}: TraceStepProps) {
  const [showDetails, setShowDetails] = useState(false);
  const hasChildren = (step.children?.length ?? 0) > 0;

  // Status icon
  const StatusIcon = (() => {
    switch (step.status) {
      case "success":
        return CheckCircle2;
      case "error":
        return AlertCircle;
      default:
        return Clock;
    }
  })();

  // Status color
  const statusColor = (() => {
    switch (step.status) {
      case "success":
        return "text-green-600 dark:text-green-400";
      case "error":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-zinc-500 dark:text-zinc-400";
    }
  })();

  return (
    <div
      className={cn(
        "border-b border-zinc-100 dark:border-zinc-800 last:border-0",
        step.status === "error" &&
          "bg-red-50/50 dark:bg-red-950/20 border-red-100 dark:border-red-900",
      )}
    >
      <div
        className="flex items-start gap-3 p-3 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 cursor-pointer"
        style={{ paddingLeft: `${depth * 24 + 12}px` }}
        onClick={() => setShowDetails(!showDetails)}
      >
        {/* Expand/collapse button */}
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            className="mt-0.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-transform"
          >
            <ChevronRight
              className={cn(
                "h-4 w-4 transition-transform",
                isExpanded && "rotate-90",
              )}
            />
          </button>
        )}
        {!hasChildren && <div className="w-4" />}

        {/* Status icon */}
        <StatusIcon className={cn("h-4 w-4 mt-0.5 flex-shrink-0", statusColor)} />

        {/* Step info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Agent name */}
            {step.agentName && (
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {step.agentName}
              </span>
            )}

            {/* Tool name */}
            {step.toolName && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-mono">
                {step.toolName}
              </span>
            )}

            {/* Duration */}
            {step.duration !== undefined && (
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                {step.duration < 1000
                  ? `${step.duration}ms`
                  : `${(step.duration / 1000).toFixed(2)}s`}
              </span>
            )}
          </div>

          {/* Description */}
          {step.description && (
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
              {step.description}
            </p>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {showDetails && (
        <div
          className="px-3 pb-3 space-y-3"
          style={{ paddingLeft: `${depth * 24 + 12 + 28}px` }}
        >
          {/* Tool details */}
          {step.toolName && (
            <TraceToolComponent
              toolName={step.toolName}
              args={step.args}
              result={step.result}
            />
          )}

          {/* Error details */}
          {step.status === "error" && step.error && (
            <TraceErrorComponent error={step.error} />
          )}

          {/* Metadata */}
          {step.metadata && Object.keys(step.metadata).length > 0 && (
            <div className="text-xs">
              <div className="font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Metadata
              </div>
              <pre className="bg-zinc-100 dark:bg-zinc-900 rounded p-2 overflow-x-auto">
                <code className="text-zinc-800 dark:text-zinc-200">
                  {JSON.stringify(step.metadata, null, 2)}
                </code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
