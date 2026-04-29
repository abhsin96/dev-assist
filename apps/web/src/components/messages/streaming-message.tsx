"use client";

import { useState, useEffect, useRef, createElement } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { Loader2, AlertCircle } from "lucide-react";
import { toolRendererRegistry } from "@/lib/tools";
import { GenericToolCard } from "@/components/tools";
import { TraceDrawer } from "@/components/trace";
import { useTraceData } from "@/features/threads/hooks/use-trace-data";

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
 * Renders a tool call with custom or generic renderer
 * Uses a wrapper approach to avoid dynamic component creation during render
 */
function ToolCallRenderer({
  toolName,
  toolCallId,
  args,
  status,
  result,
  error,
}: {
  toolName: string;
  toolCallId: string;
  args: Record<string, unknown>;
  status: "loading" | "success" | "error";
  result?: unknown;
  error?: string;
}) {
  // Check if a custom renderer exists
  const hasCustomRenderer = toolRendererRegistry.has(toolName);

  // If no custom renderer, use generic card
  if (!hasCustomRenderer) {
    return (
      <GenericToolCard
        toolName={toolName}
        toolCallId={toolCallId}
        args={args}
        result={result}
        error={error}
        status={status}
      />
    );
  }

  // Get the component and render it using createElement to avoid ESLint error
  // This is safe because we're not creating the component, just retrieving it
  const ToolComponent = toolRendererRegistry.get(toolName)!;

  // Use React.createElement to avoid the static-components ESLint rule
  return createElement(ToolComponent, {
    toolName,
    toolCallId,
    args,
    result,
    error,
    status,
  });
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

    case "tool-call": {
      const toolName = part.toolName ?? "unknown";
      return (
        <ToolCallRenderer
          toolName={toolName}
          toolCallId={part.toolCallId ?? ""}
          args={part.toolArgs ?? {}}
          status="loading"
        />
      );
    }

    case "tool-result": {
      const isSuccess = !part.toolError;
      const toolName = part.toolName ?? "unknown";
      return (
        <ToolCallRenderer
          toolName={toolName}
          toolCallId={part.toolCallId ?? ""}
          args={part.toolArgs ?? {}}
          result={part.toolResult}
          error={part.toolError}
          status={isSuccess ? "success" : "error"}
        />
      );
    }

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
      // Interrupt events are now handled by HITLApprovalCard component
      // This is a placeholder for backward compatibility
      return null;

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
export interface StreamingMessageWithTraceProps extends StreamingMessageProps {
  runId?: string;
  messageId?: string;
  showTraceButton?: boolean;
}

export function StreamingMessage({
  parts,
  isStreaming,
  role,
  className,
  runId,
  messageId,
  showTraceButton = true,
}: StreamingMessageWithTraceProps) {
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

      {/* Trace viewer button - only show for assistant messages with runId */}
      {role === "assistant" &&
        runId &&
        messageId &&
        showTraceButton &&
        !isStreaming && (
          <TraceViewerButton runId={runId} messageId={messageId} />
        )}

      <div ref={messageEndRef} />
    </div>
  );
}

/**
 * Trace viewer button component
 * Fetches trace data and renders the trace drawer
 */
function TraceViewerButton({
  runId,
  messageId,
}: {
  runId: string;
  messageId: string;
}) {
  const { data: traceData, isLoading, error } = useTraceData(runId);

  if (isLoading || error || !traceData) {
    return null;
  }

  return (
    <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800">
      <TraceDrawer messageId={messageId} runId={runId} traceData={traceData} />
    </div>
  );
}
