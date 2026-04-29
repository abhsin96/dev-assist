/**
 * AppError - Typed mirror of backend DevHubError
 * Represents all application errors with structured metadata
 */
export class AppError extends Error {
  /**
   * Machine-readable error code (e.g., "THREAD_NOT_FOUND", "UNAUTHORIZED")
   */
  readonly code: string;

  /**
   * HTTP status code
   */
  readonly status: number;

  /**
   * Human-readable error detail from backend
   */
  readonly detail: string;

  /**
   * Unique trace ID for debugging
   */
  readonly traceId?: string;

  /**
   * Additional metadata from backend
   */
  readonly metadata?: Record<string, unknown>;

  /**
   * Whether this error is retryable
   */
  readonly retryable: boolean;

  /**
   * Original error that caused this AppError (if any)
   */
  readonly cause?: Error;

  constructor(params: {
    code: string;
    status: number;
    detail: string;
    traceId?: string;
    metadata?: Record<string, unknown>;
    retryable?: boolean;
    cause?: Error;
  }) {
    super(params.detail);
    this.name = "AppError";
    this.code = params.code;
    this.status = params.status;
    this.detail = params.detail;
    this.traceId = params.traceId;
    this.metadata = params.metadata;
    this.retryable = params.retryable ?? isRetryableStatus(params.status);
    this.cause = params.cause;

    // Maintain proper stack trace for where our error was thrown (only available on V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AppError);
    }
  }

  /**
   * Convert AppError to a plain object for logging/serialization
   */
  toJSON() {
    return {
      name: this.name,
      code: this.code,
      status: this.status,
      detail: this.detail,
      traceId: this.traceId,
      metadata: this.metadata,
      retryable: this.retryable,
      stack: this.stack,
    };
  }
}

/**
 * Determine if an HTTP status code represents a retryable error
 */
function isRetryableStatus(status: number): boolean {
  // 408 Request Timeout, 429 Too Many Requests, 5xx Server Errors
  return status === 408 || status === 429 || (status >= 500 && status < 600);
}

/**
 * RFC 7807 Problem Details for HTTP APIs
 */
interface ProblemDetails {
  type?: string;
  title?: string;
  status: number;
  detail?: string;
  instance?: string;
  traceId?: string;
  code?: string;
  [key: string]: unknown;
}

/**
 * Parse RFC 7807 Problem Details response into AppError
 */
export async function parseProblem(response: Response): Promise<AppError> {
  const contentType = response.headers.get("content-type") || "";

  let problem: ProblemDetails;

  try {
    if (
      contentType.includes("application/json") ||
      contentType.includes("application/problem+json")
    ) {
      problem = await response.json();
    } else {
      // Fallback for non-JSON responses
      const text = await response.text();
      problem = {
        status: response.status,
        detail: text || response.statusText,
        code: `HTTP_${response.status}`,
      };
    }
  } catch {
    // If parsing fails, create a generic error
    problem = {
      status: response.status,
      detail: response.statusText || "Unknown error",
      code: `HTTP_${response.status}`,
    };
  }

  return new AppError({
    code: problem.code || problem.title || `HTTP_${problem.status}`,
    status: problem.status,
    detail: problem.detail || problem.title || "An error occurred",
    traceId: problem.traceId || response.headers.get("x-trace-id") || undefined,
    metadata: extractMetadata(problem),
  });
}

/**
 * Extract additional metadata from problem details
 */
function extractMetadata(
  problem: ProblemDetails,
): Record<string, unknown> | undefined {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { type, title, status, detail, instance, traceId, code, ...rest } =
    problem;

  if (Object.keys(rest).length === 0) {
    return undefined;
  }

  return rest;
}

/**
 * Check if an error is an AppError
 */
export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}

/**
 * Convert any error to AppError
 */
export function toAppError(error: unknown): AppError {
  if (isAppError(error)) {
    return error;
  }

  if (error instanceof Error) {
    return new AppError({
      code: "UNKNOWN_ERROR",
      status: 500,
      detail: error.message,
      cause: error,
    });
  }

  return new AppError({
    code: "UNKNOWN_ERROR",
    status: 500,
    detail: String(error),
  });
}
