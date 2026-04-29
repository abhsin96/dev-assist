import { parseProblem } from "@/lib/errors";

/**
 * Base API client configuration
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Request options for API calls
 */
export interface RequestOptions extends RequestInit {
  /**
   * Additional headers to include in the request
   */
  headers?: HeadersInit;
  
  /**
   * Request timeout in milliseconds (default: 30000)
   */
  timeout?: number;
  
  /**
   * Whether to include credentials (cookies) in the request
   */
  credentials?: RequestCredentials;
}

/**
 * Enhanced fetch wrapper that throws AppError for non-2xx responses
 * Never returns raw error JSON to callers
 */
export async function apiClient<T = unknown>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { timeout = 30000, headers = {}, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      credentials: fetchOptions.credentials ?? "include",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // For successful responses, parse and return the data
    if (response.ok) {
      // Handle 204 No Content
      if (response.status === 204) {
        return undefined as T;
      }

      const contentType = response.headers.get("content-type");
      if (contentType?.includes("application/json")) {
        return await response.json();
      }

      // For non-JSON responses, return as text
      return (await response.text()) as T;
    }

    // For non-2xx responses, parse as AppError and throw
    const error = await parseProblem(response);
    throw error;
  } catch (error) {
    clearTimeout(timeoutId);

    // If it's already an AppError, re-throw it
    if (error instanceof Error && error.name === "AppError") {
      throw error;
    }

    // Handle abort/timeout errors
    if (error instanceof Error && error.name === "AbortError") {
      const { AppError } = await import("@/lib/errors");
      throw new AppError({
        code: "REQUEST_TIMEOUT",
        status: 408,
        detail: "The request took too long to complete. Please try again.",
        cause: error,
      });
    }

    // Handle network errors
    if (error instanceof TypeError) {
      const { AppError } = await import("@/lib/errors");
      throw new AppError({
        code: "NETWORK_ERROR",
        status: 0,
        detail: "Unable to connect to the server. Please check your internet connection.",
        cause: error,
      });
    }

    // Re-throw unknown errors
    throw error;
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const api = {
  get: <T = unknown>(endpoint: string, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: "GET" }),

  post: <T = unknown>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T = unknown>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T = unknown>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T = unknown>(endpoint: string, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: "DELETE" }),
};
