/**
 * Error code to user-facing message mapping
 * This is the single source of truth for error messages (i18n table)
 */
export const ERROR_MESSAGES: Record<string, { title: string; description: string }> = {
  // Authentication & Authorization
  UNAUTHORIZED: {
    title: "Authentication Required",
    description: "Please sign in to continue.",
  },
  FORBIDDEN: {
    title: "Access Denied",
    description: "You don't have permission to access this resource.",
  },
  TOKEN_EXPIRED: {
    title: "Session Expired",
    description: "Your session has expired. Please sign in again.",
  },
  INVALID_TOKEN: {
    title: "Invalid Session",
    description: "Your session is invalid. Please sign in again.",
  },

  // Resource Not Found
  THREAD_NOT_FOUND: {
    title: "Thread Not Found",
    description: "The conversation you're looking for doesn't exist or has been deleted.",
  },
  RUN_NOT_FOUND: {
    title: "Run Not Found",
    description: "The agent run you're looking for doesn't exist.",
  },
  USER_NOT_FOUND: {
    title: "User Not Found",
    description: "The user you're looking for doesn't exist.",
  },
  RESOURCE_NOT_FOUND: {
    title: "Not Found",
    description: "The requested resource could not be found.",
  },

  // Validation Errors
  VALIDATION_ERROR: {
    title: "Invalid Input",
    description: "Please check your input and try again.",
  },
  INVALID_REQUEST: {
    title: "Invalid Request",
    description: "The request could not be processed. Please check your input.",
  },

  // Rate Limiting
  RATE_LIMIT_EXCEEDED: {
    title: "Too Many Requests",
    description: "You've made too many requests. Please wait a moment and try again.",
  },

  // Server Errors
  INTERNAL_SERVER_ERROR: {
    title: "Server Error",
    description: "Something went wrong on our end. Please try again later.",
  },
  SERVICE_UNAVAILABLE: {
    title: "Service Unavailable",
    description: "The service is temporarily unavailable. Please try again later.",
  },
  GATEWAY_TIMEOUT: {
    title: "Request Timeout",
    description: "The request took too long to complete. Please try again.",
  },

  // Network Errors
  NETWORK_ERROR: {
    title: "Network Error",
    description: "Unable to connect to the server. Please check your internet connection.",
  },
  REQUEST_TIMEOUT: {
    title: "Request Timeout",
    description: "The request took too long. Please try again.",
  },

  // Agent-specific Errors
  AGENT_EXECUTION_FAILED: {
    title: "Agent Execution Failed",
    description: "The AI agent encountered an error while processing your request.",
  },
  TOOL_EXECUTION_FAILED: {
    title: "Tool Execution Failed",
    description: "A tool failed to execute properly. Please try again.",
  },
  APPROVAL_REQUIRED: {
    title: "Approval Required",
    description: "This action requires approval before proceeding.",
  },
  APPROVAL_EXPIRED: {
    title: "Approval Expired",
    description: "The approval request has expired. Please try again.",
  },
  APPROVAL_REJECTED: {
    title: "Approval Rejected",
    description: "The requested action was rejected.",
  },

  // Generic HTTP Errors
  HTTP_400: {
    title: "Bad Request",
    description: "The request could not be understood by the server.",
  },
  HTTP_404: {
    title: "Not Found",
    description: "The requested resource could not be found.",
  },
  HTTP_500: {
    title: "Server Error",
    description: "An internal server error occurred.",
  },
  HTTP_502: {
    title: "Bad Gateway",
    description: "The server received an invalid response.",
  },
  HTTP_503: {
    title: "Service Unavailable",
    description: "The service is temporarily unavailable.",
  },
  HTTP_504: {
    title: "Gateway Timeout",
    description: "The server did not receive a timely response.",
  },

  // Default/Unknown
  UNKNOWN_ERROR: {
    title: "Unexpected Error",
    description: "An unexpected error occurred. Please try again.",
  },
};

/**
 * Get user-facing message for an error code
 */
export function getErrorMessage(code: string): { title: string; description: string } {
  return ERROR_MESSAGES[code] || ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * Check if an error code is retryable based on its semantic meaning
 */
export function isRetryableErrorCode(code: string): boolean {
  const retryableCodes = [
    "RATE_LIMIT_EXCEEDED",
    "SERVICE_UNAVAILABLE",
    "GATEWAY_TIMEOUT",
    "NETWORK_ERROR",
    "REQUEST_TIMEOUT",
    "HTTP_408",
    "HTTP_429",
    "HTTP_500",
    "HTTP_502",
    "HTTP_503",
    "HTTP_504",
  ];

  return retryableCodes.includes(code) || code.startsWith("HTTP_5");
}
