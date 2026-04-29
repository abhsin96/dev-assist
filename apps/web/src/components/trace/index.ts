/**
 * Trace viewer components
 * 
 * Provides a comprehensive trace viewer for debugging agent execution:
 * - TraceDrawer: Opens from assistant messages to show full trace
 * - Trace: Main trace tree component with virtualization
 * - Trace.Step: Individual step component (compound component pattern)
 * - Trace.Tool: Tool call details component
 * - Trace.Error: Error details component
 */

export { TraceDrawer } from "./trace-drawer";
export { Trace } from "./trace";
export { TraceStepComponent } from "./trace-step";
export { TraceToolComponent } from "./trace-tool";
export { TraceErrorComponent } from "./trace-error";
export type {
  TraceData,
  TraceStep,
  TraceStepStatus,
  TraceSummary,
} from "./types";
