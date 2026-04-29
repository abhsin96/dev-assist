"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import {
  Loader2,
  AlertCircle,
  Wrench,
  CheckCircle,
  XCircle,
} from "lucide-react";

export interface MessagePart {
  type: "text" | "tool-call" | "tool-result" | "error" | "interrupt" | "state";
  content: string;
  toolName?: string;
  toolCallId?: string;
  toolArgs?: Record<string, unknown>;
  toolResult?: unknown;
  toolError?: string;
  interruptData?: {
    approvalId: string;
    summary: string;
    risk: string;
    expiresAt: string;
  };
  stateData?: {
    currentAgent: string | null;
    plan: unknown[];
  };
}

export interface StreamingMessageProps {
  parts: MessagePart[];
  isStreaming: boolean;
  role: "user" | "assistant";
  className?: string;
}

/**
 * Renders a single message part with appropriate styling
 */
function MessagePartRenderer({ part }: { part: MessagePart }) {
  switch (part.type) {
    case "text":
      return (
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {part.content}
          </ReactMarkdown>
        </div>
      );

    case "tool-call":
      return (
        <div className="flex items-start gap-2 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 p-3">
          <Wrench className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-blue-900 dark:text-blue-100">
              Calling tool: {part.toolName}
            </div>
            {part.toolArgs && Object.keys(part.toolArgs).length > 0 && (
              <details className="mt-1">
                <summary className="text-xs text-blue-700 dark:text-blue-300 cursor-pointer hover:underline">
                  View arguments
                </summary>
                <pre className="mt-2 text-xs bg-blue-100 dark:bg-blue-900/50 p-2 rounded overflow-x-auto">
                  {typeof part.toolArgs === "object" && part.toolArgs !== null
                    ? JSON.stringify(part.toolArgs, null, 2)
                    : String(part.toolArgs)}
                </pre>
              </details>
            )}
          </div>
        </div>
      );

    case "tool-result":
      const isSuccess = !part.toolError;
      return (
        <div
          className={cn(
            "flex items-start gap-2 rounded-lg border p-3",
            isSuccess
              ? "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30"
              : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30",
          )}
        >
          {isSuccess ? (
            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5" />
          )}
          <div className="flex-1 min-w-0">
            <div
              className={cn(
                "font-medium text-sm",
                isSuccess
                  ? "text-green-900 dark:text-green-100"
                  : "text-red-900 dark:text-red-100",
              )}
            >
              {isSuccess ? "Tool completed" : "Tool failed"}
            </div>
            {part.toolError && (
              <div className="mt-1 text-xs text-red-700 dark:text-red-300">
                {part.toolError}
              </div>
            )}
            {part.toolResult !== undefined && part.toolResult !== null && (
              <details className="mt-1">
                <summary
                  className={cn(
                    "text-xs cursor-pointer hover:underline",
                    isSuccess
                      ? "text-green-700 dark:text-green-300"
                      : "text-red-700 dark:text-red-300",
                  )}
                >
                  View result
                </summary>
                <pre
                  className={cn(
                    "mt-2 text-xs p-2 rounded overflow-x-auto",
                    isSuccess
                      ? "bg-green-100 dark:bg-green-900/50"
                      : "bg-red-100 dark:bg-red-900/50",
                  )}
                >
                  {(() => {
                    if (typeof part.toolResult === "string") {
                      return part.toolResult;
                    }
                    try {
                      return JSON.stringify(part.toolResult, null, 2);
                    } catch {
                      return String(part.toolResult);
                    }
                  })()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );

    case "error":
      return (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30 p-3">
          <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-red-900 dark:text-red-100">
              Error
            </div>
            <div className="mt-1 text-xs text-red-700 dark:text-red-300">
              {part.content}
            </div>
          </div>
        </div>
      );

    case "interrupt":
      return (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3">
          <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-amber-900 dark:text-amber-100">
              Approval Required
            </div>
            {part.interruptData && (
              <div className="mt-1 space-y-1">
                <div className="text-xs text-amber-700 dark:text-amber-300">
                  {part.interruptData.summary}
                </div>
                <div className="text-xs text-amber-600 dark:text-amber-400">
                  Risk: {part.interruptData.risk}
                </div>
              </div>
            )}
          </div>
        </div>
      );

    case "state":
      return (
        <div className="flex items-start gap-2 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/30 p-3">
          <div className="flex-1 min-w-0">
            {part.stateData?.currentAgent && (
              <div className="text-xs text-zinc-600 dark:text-zinc-400">
                Agent: {part.stateData.currentAgent}
              </div>
            )}
          </div>
        </div>
      );

    default:
      return null;
  }
}

/**
 * Streaming message component with support for text, tool calls, results, errors, and interrupts
 */
export function StreamingMessage({
  parts,
  isStreaming,
  role,
  className,
}: StreamingMessageProps) {
  const messageEndRef = useRef<HTMLDivElement>(null);
  const [showCursor, setShowCursor] = useState(false);

  // Blinking cursor effect while streaming
  useEffect(() => {
    if (!isStreaming) {
      return;
    }

    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530); // Subtle blink rate

    return () => {
      clearInterval(interval);
    };
  }, [isStreaming]);

  return (
    <div
      className={cn(
        "group relative rounded-lg p-4",
        role === "user"
          ? "bg-blue-50 dark:bg-blue-950/30 ml-12"
          : "bg-zinc-50 dark:bg-zinc-900/30 mr-12",
        className,
      )}
    >
      <div className="space-y-3">
        {parts.map((part, index) => (
          <MessagePartRenderer key={index} part={part} />
        ))}

        {isStreaming && (
          <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span className="text-xs">Streaming...</span>
            {showCursor && (
              <span className="inline-block w-0.5 h-4 bg-zinc-400 dark:bg-zinc-500 animate-pulse" />
            )}
          </div>
        )}
      </div>
      <div ref={messageEndRef} />
    </div>
  );
}
