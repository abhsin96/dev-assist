/**
 * Type definitions for trace viewer components
 */

export type TraceStepStatus = "pending" | "running" | "success" | "error";

export interface TraceStep {
  id: string;
  agentName?: string;
  toolName?: string;
  description?: string;
  args?: Record<string, unknown>;
  result?: unknown;
  error?: string | Error | Record<string, unknown>;
  status: TraceStepStatus;
  duration?: number; // milliseconds
  startTime?: string; // ISO timestamp
  endTime?: string; // ISO timestamp
  metadata?: Record<string, unknown>;
  children?: TraceStep[];
}

export interface TraceData {
  runId: string;
  steps: TraceStep[];
  totalDuration?: number;
  status: "running" | "completed" | "failed";
}

export interface TraceSummary {
  totalSteps: number;
  totalDuration: number;
  errorCount: number;
  toolCalls: number;
}
