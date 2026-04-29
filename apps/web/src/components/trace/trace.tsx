"use client";

import { useState, useMemo } from "react";
import { Virtuoso } from "react-virtuoso";
import type { TraceData, TraceStep } from "./types";
import { TraceStepComponent } from "./trace-step";
import { cn } from "@/lib/utils";

export interface TraceProps {
  data: TraceData;
  runId: string;
  className?: string;
}

/**
 * Main trace component that renders the full trace tree
 * Uses virtualization for performance with large traces
 */
export function Trace({ data, runId, className }: TraceProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // Flatten the trace tree for virtualization
  const flattenedSteps = useMemo(() => {
    const flatten = (
      steps: TraceStep[],
      depth: number = 0,
    ): Array<TraceStep & { depth: number }> => {
      const result: Array<TraceStep & { depth: number }> = [];

      for (const step of steps) {
        result.push({ ...step, depth });

        // Include children if this step is expanded
        if (expandedSteps.has(step.id) && step.children?.length) {
          result.push(...flatten(step.children, depth + 1));
        }
      }

      return result;
    };

    return flatten(data.steps);
  }, [data.steps, expandedSteps]);

  const toggleExpanded = (stepId: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  };

  // Performance stats
  const stats = useMemo(() => {
    const totalSteps = data.steps.length;
    const totalDuration = data.steps.reduce(
      (sum, step) => sum + (step.duration || 0),
      0,
    );
    const errorCount = data.steps.filter((step) => step.status === "error")
      .length;

    return { totalSteps, totalDuration, errorCount };
  }, [data.steps]);

  if (flattenedSteps.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500 dark:text-zinc-400">
        <p className="text-sm">No trace data available</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Trace stats */}
      <div className="flex items-center gap-6 text-xs text-zinc-600 dark:text-zinc-400">
        <div>
          <span className="font-medium">{stats.totalSteps}</span> steps
        </div>
        <div>
          <span className="font-medium">
            {(stats.totalDuration / 1000).toFixed(2)}s
          </span>{" "}
          total
        </div>
        {stats.errorCount > 0 && (
          <div className="text-red-600 dark:text-red-400">
            <span className="font-medium">{stats.errorCount}</span> errors
          </div>
        )}
      </div>

      {/* Virtualized trace tree */}
      <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden">
        <Virtuoso
          data={flattenedSteps}
          style={{ height: "600px" }}
          itemContent={(index, step) => (
            <TraceStepComponent
              key={step.id}
              step={step}
              depth={step.depth}
              isExpanded={expandedSteps.has(step.id)}
              onToggleExpand={() => toggleExpanded(step.id)}
            />
          )}
        />
      </div>
    </div>
  );
}

// Compound component exports
Trace.Step = TraceStepComponent;
