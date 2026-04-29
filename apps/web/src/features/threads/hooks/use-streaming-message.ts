"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { createSSETransport } from "@/lib/streaming/sseTransport";
import type { MessagePart } from "@/components/messages/streaming-message";
import { toast } from "sonner";

export interface UseStreamingMessageOptions {
  threadId?: string;
  onComplete?: (parts: MessagePart[]) => void;
  onError?: (error: Error) => void;
}

export interface UseStreamingMessageReturn {
  parts: MessagePart[];
  isStreaming: boolean;
  error: Error | null;
  startStream: (runId: string) => Promise<void>;
  cancelStream: () => void;
  retry: () => void;
}

/**
 * Hook for managing streaming messages with SSE transport
 */
export function useStreamingMessage({
  onComplete,
  onError,
}: UseStreamingMessageOptions): UseStreamingMessageReturn {
  const [parts, setParts] = useState<MessagePart[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastRunIdRef = useRef<string | null>(null);
  const currentTextPartRef = useRef<string>("");

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      toast.info("Stream cancelled");
    }
  }, []);

  const startStream = useCallback(
    async (runId: string) => {
      // Cancel any existing stream
      cancelStream();

      // Reset state
      setParts([]);
      setError(null);
      setIsStreaming(true);
      currentTextPartRef.current = "";
      lastRunIdRef.current = runId;

      // Create new abort controller
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      try {
        const stream = await createSSETransport({
          url: "/api/runs/stream",
          runId,
          signal: abortController.signal,
          onError: (err) => {
            console.error("SSE transport error:", err);
            setError(err);
            onError?.(err);
            toast.error("Stream connection failed", {
              description: err.message,
            });
          },
          onReconnect: (fromSeq) => {
            toast.info("Reconnecting...", {
              description: `Resuming from sequence ${fromSeq}`,
            });
          },
        });

        for await (const part of stream) {
          // Check if cancelled
          if (abortController.signal.aborted) {
            break;
          }

          switch (part.type) {
            case "text-delta":
              currentTextPartRef.current += part.textDelta;
              setParts((prev) => {
                const newParts = [...prev];
                const lastPart = newParts[newParts.length - 1];

                if (lastPart && lastPart.type === "text") {
                  // Update existing text part
                  lastPart.content = currentTextPartRef.current;
                } else {
                  // Create new text part
                  newParts.push({
                    type: "text",
                    content: currentTextPartRef.current,
                  });
                }

                return newParts;
              });
              break;

            case "tool-call":
              currentTextPartRef.current = ""; // Reset text accumulator
              setParts((prev) => [
                ...prev,
                {
                  type: "tool-call",
                  content: "",
                  toolName: part.toolName,
                  toolCallId: part.toolCallId,
                  toolArgs: part.args as Record<string, unknown>,
                },
              ]);
              break;

            case "tool-result":
              setParts((prev) => [
                ...prev,
                {
                  type: "tool-result",
                  content: "",
                  toolCallId: part.toolCallId,
                  toolResult: part.result,
                  toolError:
                    typeof part.result === "object" &&
                    part.result &&
                    "error" in part.result
                      ? String(part.result.error)
                      : undefined,
                },
              ]);
              break;

            case "interrupt":
              // Handle HITL interrupt events
              setParts((prev) => [
                ...prev,
                {
                  type: "interrupt",
                  content: "",
                  interruptData: {
                    approvalId: part.approvalId,
                    summary: part.summary,
                    risk: part.risk,
                    expiresAt: part.expiresAt,
                  },
                  toolName: part.toolName,
                  toolArgs: part.toolArgs as Record<string, unknown>,
                },
              ]);
              break;

            case "error":
              const errorMessage =
                part.error instanceof Error
                  ? part.error.message
                  : "Unknown error";
              setParts((prev) => [
                ...prev,
                {
                  type: "error",
                  content: errorMessage,
                },
              ]);
              setError(
                part.error instanceof Error
                  ? part.error
                  : new Error(errorMessage),
              );
              break;

            case "finish":
              setIsStreaming(false);
              onComplete?.(parts);
              return;
          }
        }

        // Stream completed
        setIsStreaming(false);
        onComplete?.(parts);
      } catch (err) {
        if (abortController.signal.aborted) {
          // User cancelled, not an error
          return;
        }

        const error = err instanceof Error ? err : new Error("Stream failed");
        setError(error);
        setIsStreaming(false);
        onError?.(error);
        toast.error("Stream failed", {
          description: error.message,
        });
      }
    },
    [cancelStream, onComplete, onError, parts],
  );

  const retry = useCallback(() => {
    if (lastRunIdRef.current) {
      startStream(lastRunIdRef.current);
    }
  }, [startStream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    parts,
    isStreaming,
    error,
    startStream,
    cancelStream,
    retry,
  };
}
