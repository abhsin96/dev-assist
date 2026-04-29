/**
 * SSE Transport adapter for Vercel AI SDK
 *
 * Adapts the backend's SSE protocol (from DEVHUB-010) to the Vercel AI SDK Transport interface.
 * Supports reconnection with `from=<seq>` resume capability.
 */

export interface SSETransportOptions {
  url: string;
  runId: string;
  fromSeq?: number;
  signal?: AbortSignal;
  onError?: (error: Error) => void;
  onReconnect?: (fromSeq: number) => void;
}

/**
 * Stream part types compatible with AI SDK
 */
export type StreamPart =
  | { type: "text-delta"; textDelta: string }
  | { type: "tool-call"; toolCallId: string; toolName: string; args: unknown }
  | { type: "tool-result"; toolCallId: string; result: unknown }
  | {
      type: "interrupt";
      approvalId: string;
      summary: string;
      risk: string;
      expiresAt: string;
      toolName: string;
      toolArgs: unknown;
    }
  | { type: "error"; error: Error }
  | {
      type: "finish";
      finishReason: string;
      usage: { promptTokens: number; completionTokens: number };
    };

export interface SSEEvent {
  id: string;
  event: string;
  data: string;
}

/**
 * Parse SSE event stream from backend
 */
export async function* parseSSEStream(
  response: Response,
): AsyncGenerator<SSEEvent, void, unknown> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent: Partial<SSEEvent> = {};

      for (const line of lines) {
        if (line.startsWith("id:")) {
          currentEvent.id = line.slice(3).trim();
        } else if (line.startsWith("event:")) {
          currentEvent.event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          currentEvent.data = line.slice(5).trim();
        } else if (line === "") {
          // Empty line signals end of event
          if (currentEvent.event && currentEvent.data !== undefined) {
            yield currentEvent as SSEEvent;
          }
          currentEvent = {};
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Convert backend SSE events to AI SDK stream parts
 */
export function convertToStreamPart(event: SSEEvent): StreamPart | null {
  // Skip heartbeat events
  if (event.event === "heartbeat") {
    return null;
  }

  try {
    const data = JSON.parse(event.data);

    switch (event.event) {
      case "token":
        return {
          type: "text-delta",
          textDelta: data.text,
        };

      case "tool_call":
        return {
          type: "tool-call",
          toolCallId: data.id,
          toolName: data.name,
          args: data.args,
        };

      case "tool_result":
        return {
          type: "tool-result",
          toolCallId: data.id,
          result: data.ok ? data.data : { error: data.error },
        };

      case "error":
        return {
          type: "error",
          error: new Error(data.message),
        };

      case "interrupt":
        return {
          type: "interrupt",
          approvalId: data.approval_id || "",
          summary: data.summary || "",
          risk: data.risk || "medium",
          expiresAt:
            data.expires_at ||
            new Date(Date.now() + 5 * 60 * 1000).toISOString(),
          toolName: data.tool_name || "",
          toolArgs: data.tool_args || {},
        };

      case "done":
        return {
          type: "finish",
          finishReason: "stop",
          usage: { promptTokens: 0, completionTokens: 0 },
        };

      // Custom event types not in AI SDK standard
      case "state":
        // These will be handled separately in the UI
        return null;

      default:
        console.warn(`Unknown SSE event type: ${event.event}`);
        return null;
    }
  } catch (error) {
    console.error("Failed to parse SSE event:", error);
    return null;
  }
}

/**
 * Create SSE transport for AI SDK
 */
export async function createSSETransport(
  options: SSETransportOptions,
): Promise<AsyncIterable<StreamPart>> {
  const { url, runId, fromSeq = 0, signal, onError, onReconnect } = options;

  const streamUrl = new URL(url);
  streamUrl.searchParams.set("run_id", runId);
  if (fromSeq > 0) {
    streamUrl.searchParams.set("from", fromSeq.toString());
  }

  let lastSeq = fromSeq;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 3;
  const RECONNECT_DELAY = 1000; // 1 second

  async function* streamWithReconnect(): AsyncGenerator<
    StreamPart,
    void,
    unknown
  > {
    while (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      try {
        const response = await fetch(streamUrl.toString(), {
          method: "GET",
          headers: {
            Accept: "text/event-stream",
            "Cache-Control": "no-cache",
          },
          signal,
        });

        if (!response.ok) {
          throw new Error(
            `SSE request failed: ${response.status} ${response.statusText}`,
          );
        }

        reconnectAttempts = 0; // Reset on successful connection

        for await (const event of parseSSEStream(response)) {
          // Track sequence for reconnection
          if (event.id) {
            lastSeq = parseInt(event.id, 10);
          }

          const part = convertToStreamPart(event);
          if (part) {
            yield part;
          }

          // Check if stream is done
          if (event.event === "done" || event.event === "error") {
            return;
          }
        }

        // Stream ended normally
        return;
      } catch (error) {
        if (signal?.aborted) {
          // User cancelled, don't retry
          return;
        }

        reconnectAttempts++;

        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          const err =
            error instanceof Error ? error : new Error("Stream failed");
          onError?.(err);
          throw err;
        }

        // Wait before reconnecting
        await new Promise((resolve) =>
          setTimeout(resolve, RECONNECT_DELAY * reconnectAttempts),
        );

        // Update URL with last sequence for resume
        streamUrl.searchParams.set("from", (lastSeq + 1).toString());
        onReconnect?.(lastSeq + 1);
      }
    }
  }

  return streamWithReconnect();
}
