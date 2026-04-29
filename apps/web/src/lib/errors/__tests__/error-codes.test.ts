import { describe, it, expect } from "@jest/globals";
import { getErrorMessage, isRetryableErrorCode, ERROR_MESSAGES } from "../error-codes";

describe("error-codes", () => {
  describe("getErrorMessage", () => {
    it("should return correct message for UNAUTHORIZED", () => {
      const message = getErrorMessage("UNAUTHORIZED");
      expect(message.title).toBe("Authentication Required");
      expect(message.description).toBe("Please sign in to continue.");
    });

    it("should return correct message for THREAD_NOT_FOUND", () => {
      const message = getErrorMessage("THREAD_NOT_FOUND");
      expect(message.title).toBe("Thread Not Found");
      expect(message.description).toContain("conversation");
    });

    it("should return correct message for RATE_LIMIT_EXCEEDED", () => {
      const message = getErrorMessage("RATE_LIMIT_EXCEEDED");
      expect(message.title).toBe("Too Many Requests");
      expect(message.description).toContain("too many requests");
    });

    it("should return correct message for INTERNAL_SERVER_ERROR", () => {
      const message = getErrorMessage("INTERNAL_SERVER_ERROR");
      expect(message.title).toBe("Server Error");
      expect(message.description).toContain("went wrong");
    });

    it("should return correct message for NETWORK_ERROR", () => {
      const message = getErrorMessage("NETWORK_ERROR");
      expect(message.title).toBe("Network Error");
      expect(message.description).toContain("connect");
    });

    it("should return correct message for APPROVAL_REQUIRED", () => {
      const message = getErrorMessage("APPROVAL_REQUIRED");
      expect(message.title).toBe("Approval Required");
      expect(message.description).toContain("approval");
    });

    it("should return default message for unknown code", () => {
      const message = getErrorMessage("UNKNOWN_CODE_12345");
      expect(message.title).toBe("Unexpected Error");
      expect(message.description).toBe("An unexpected error occurred. Please try again.");
    });
  });

  describe("isRetryableErrorCode", () => {
    it("should return true for retryable codes", () => {
      expect(isRetryableErrorCode("RATE_LIMIT_EXCEEDED")).toBe(true);
      expect(isRetryableErrorCode("SERVICE_UNAVAILABLE")).toBe(true);
      expect(isRetryableErrorCode("GATEWAY_TIMEOUT")).toBe(true);
      expect(isRetryableErrorCode("NETWORK_ERROR")).toBe(true);
      expect(isRetryableErrorCode("REQUEST_TIMEOUT")).toBe(true);
      expect(isRetryableErrorCode("HTTP_408")).toBe(true);
      expect(isRetryableErrorCode("HTTP_429")).toBe(true);
      expect(isRetryableErrorCode("HTTP_500")).toBe(true);
      expect(isRetryableErrorCode("HTTP_502")).toBe(true);
      expect(isRetryableErrorCode("HTTP_503")).toBe(true);
      expect(isRetryableErrorCode("HTTP_504")).toBe(true);
    });

    it("should return true for any HTTP_5xx code", () => {
      expect(isRetryableErrorCode("HTTP_501")).toBe(true);
      expect(isRetryableErrorCode("HTTP_599")).toBe(true);
    });

    it("should return false for non-retryable codes", () => {
      expect(isRetryableErrorCode("UNAUTHORIZED")).toBe(false);
      expect(isRetryableErrorCode("FORBIDDEN")).toBe(false);
      expect(isRetryableErrorCode("THREAD_NOT_FOUND")).toBe(false);
      expect(isRetryableErrorCode("VALIDATION_ERROR")).toBe(false);
      expect(isRetryableErrorCode("HTTP_400")).toBe(false);
      expect(isRetryableErrorCode("HTTP_404")).toBe(false);
    });
  });

  describe("ERROR_MESSAGES coverage", () => {
    it("should have at least 6 representative error codes", () => {
      const codes = Object.keys(ERROR_MESSAGES);
      expect(codes.length).toBeGreaterThanOrEqual(6);
    });

    it("should have messages for all critical error types", () => {
      const criticalCodes = [
        "UNAUTHORIZED",
        "THREAD_NOT_FOUND",
        "RATE_LIMIT_EXCEEDED",
        "INTERNAL_SERVER_ERROR",
        "NETWORK_ERROR",
        "UNKNOWN_ERROR",
      ];

      criticalCodes.forEach((code) => {
        expect(ERROR_MESSAGES[code]).toBeDefined();
        expect(ERROR_MESSAGES[code].title).toBeTruthy();
        expect(ERROR_MESSAGES[code].description).toBeTruthy();
      });
    });
  });
});
