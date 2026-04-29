import { describe, it, expect } from "@jest/globals";
import { AppError, parseProblem, isAppError, toAppError } from "../AppError";

describe("AppError", () => {
  describe("constructor", () => {
    it("should create an AppError with all properties", () => {
      const error = new AppError({
        code: "THREAD_NOT_FOUND",
        status: 404,
        detail: "Thread not found",
        traceId: "trace-123",
        metadata: { threadId: "thread-456" },
        retryable: false,
      });

      expect(error.code).toBe("THREAD_NOT_FOUND");
      expect(error.status).toBe(404);
      expect(error.detail).toBe("Thread not found");
      expect(error.traceId).toBe("trace-123");
      expect(error.metadata).toEqual({ threadId: "thread-456" });
      expect(error.retryable).toBe(false);
      expect(error.name).toBe("AppError");
      expect(error.message).toBe("Thread not found");
    });

    it("should auto-detect retryable status codes", () => {
      const error408 = new AppError({ code: "TIMEOUT", status: 408, detail: "Timeout" });
      expect(error408.retryable).toBe(true);

      const error429 = new AppError({ code: "RATE_LIMIT", status: 429, detail: "Too many requests" });
      expect(error429.retryable).toBe(true);

      const error500 = new AppError({ code: "SERVER_ERROR", status: 500, detail: "Server error" });
      expect(error500.retryable).toBe(true);

      const error404 = new AppError({ code: "NOT_FOUND", status: 404, detail: "Not found" });
      expect(error404.retryable).toBe(false);
    });

    it("should allow manual override of retryable", () => {
      const error = new AppError({
        code: "NOT_FOUND",
        status: 404,
        detail: "Not found",
        retryable: true, // Override
      });

      expect(error.retryable).toBe(true);
    });
  });

  describe("toJSON", () => {
    it("should serialize to JSON", () => {
      const error = new AppError({
        code: "TEST_ERROR",
        status: 500,
        detail: "Test error",
        traceId: "trace-123",
        metadata: { key: "value" },
      });

      const json = error.toJSON();

      expect(json.name).toBe("AppError");
      expect(json.code).toBe("TEST_ERROR");
      expect(json.status).toBe(500);
      expect(json.detail).toBe("Test error");
      expect(json.traceId).toBe("trace-123");
      expect(json.metadata).toEqual({ key: "value" });
      expect(json.retryable).toBe(true);
      expect(json.stack).toBeDefined();
    });
  });

  describe("parseProblem", () => {
    it("should parse RFC 7807 problem details", async () => {
      const response = new Response(
        JSON.stringify({
          type: "about:blank",
          title: "Not Found",
          status: 404,
          detail: "The requested resource was not found",
          code: "RESOURCE_NOT_FOUND",
          traceId: "trace-456",
        }),
        {
          status: 404,
          headers: { "content-type": "application/problem+json" },
        }
      );

      const error = await parseProblem(response);

      expect(error.code).toBe("RESOURCE_NOT_FOUND");
      expect(error.status).toBe(404);
      expect(error.detail).toBe("The requested resource was not found");
      expect(error.traceId).toBe("trace-456");
    });

    it("should handle responses without code field", async () => {
      const response = new Response(
        JSON.stringify({
          status: 500,
          title: "Internal Server Error",
          detail: "An error occurred",
        }),
        {
          status: 500,
          headers: { "content-type": "application/json" },
        }
      );

      const error = await parseProblem(response);

      expect(error.code).toBe("Internal Server Error");
      expect(error.status).toBe(500);
      expect(error.detail).toBe("An error occurred");
    });

    it("should handle non-JSON responses", async () => {
      const response = new Response("Internal Server Error", {
        status: 500,
        statusText: "Internal Server Error",
        headers: { "content-type": "text/plain" },
      });

      const error = await parseProblem(response);

      expect(error.code).toBe("HTTP_500");
      expect(error.status).toBe(500);
      expect(error.detail).toBe("Internal Server Error");
    });

    it("should extract trace ID from header if not in body", async () => {
      const response = new Response(
        JSON.stringify({
          status: 500,
          detail: "Server error",
        }),
        {
          status: 500,
          headers: {
            "content-type": "application/json",
            "x-trace-id": "header-trace-123",
          },
        }
      );

      const error = await parseProblem(response);

      expect(error.traceId).toBe("header-trace-123");
    });
  });

  describe("isAppError", () => {
    it("should return true for AppError instances", () => {
      const error = new AppError({ code: "TEST", status: 500, detail: "Test" });
      expect(isAppError(error)).toBe(true);
    });

    it("should return false for other errors", () => {
      expect(isAppError(new Error("Test"))).toBe(false);
      expect(isAppError("string error")).toBe(false);
      expect(isAppError(null)).toBe(false);
      expect(isAppError(undefined)).toBe(false);
    });
  });

  describe("toAppError", () => {
    it("should return AppError as-is", () => {
      const error = new AppError({ code: "TEST", status: 500, detail: "Test" });
      expect(toAppError(error)).toBe(error);
    });

    it("should convert Error to AppError", () => {
      const error = new Error("Test error");
      const appError = toAppError(error);

      expect(appError.code).toBe("UNKNOWN_ERROR");
      expect(appError.status).toBe(500);
      expect(appError.detail).toBe("Test error");
      expect(appError.cause).toBe(error);
    });

    it("should convert string to AppError", () => {
      const appError = toAppError("String error");

      expect(appError.code).toBe("UNKNOWN_ERROR");
      expect(appError.status).toBe(500);
      expect(appError.detail).toBe("String error");
    });

    it("should convert unknown types to AppError", () => {
      const appError = toAppError({ custom: "error" });

      expect(appError.code).toBe("UNKNOWN_ERROR");
      expect(appError.status).toBe(500);
      expect(appError.detail).toBe("[object Object]");
    });
  });
});
