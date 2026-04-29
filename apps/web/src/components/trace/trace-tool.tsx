"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TraceToolProps {
  toolName: string;
  args?: Record<string, unknown>;
  result?: unknown;
}

/**
 * Component for displaying tool call arguments and results in trace
 */
export function TraceToolComponent({ toolName, args, result }: TraceToolProps) {
  const [showArgs, setShowArgs] = useState(false);
  const [showResult, setShowResult] = useState(false);

  return (
    <div className="space-y-2">
      {/* Tool arguments */}
      {args && Object.keys(args).length > 0 && (
        <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowArgs(!showArgs)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-zinc-50 dark:bg-zinc-900/50 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 text-left"
          >
            {showArgs ? (
              <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-zinc-500" />
            )}
            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
              Arguments
            </span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              ({Object.keys(args).length} params)
            </span>
          </button>
          {showArgs && (
            <div className="p-3 bg-white dark:bg-zinc-950">
              <pre className="text-xs overflow-x-auto">
                <code className="text-zinc-800 dark:text-zinc-200">
                  {JSON.stringify(args, null, 2)}
                </code>
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Tool result */}
      {result !== undefined && (
        <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowResult(!showResult)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-zinc-50 dark:bg-zinc-900/50 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 text-left"
          >
            {showResult ? (
              <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-zinc-500" />
            )}
            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
              Result
            </span>
          </button>
          {showResult && (
            <div className="p-3 bg-white dark:bg-zinc-950">
              <pre className="text-xs overflow-x-auto">
                <code className="text-zinc-800 dark:text-zinc-200">
                  {typeof result === "string"
                    ? result
                    : JSON.stringify(result, null, 2)}
                </code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
