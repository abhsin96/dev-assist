"use client";

import { toast as sonnerToast } from "sonner";
import { AppError, getErrorMessage } from "@/lib/errors";

/**
 * Toast action button configuration
 */
interface ToastAction {
  label: string;
  onClick: () => void | Promise<void>;
}

/**
 * Options for displaying error toasts
 */
interface ErrorToastOptions {
  /**
   * Custom retry function for retryable errors
   */
  onRetry?: () => void | Promise<void>;

  /**
   * Additional actions to show in the toast
   */
  actions?: ToastAction[];

  /**
   * Duration in milliseconds (default: 5000 for errors)
   */
  duration?: number;
}

/**
 * Central toast bus for displaying AppErrors with consistent formatting
 */
export const toast = {
  /**
   * Display an error toast from an AppError
   */
  error(error: AppError, options: ErrorToastOptions = {}) {
    const { title, description } = getErrorMessage(error.code);
    const { onRetry, actions = [], duration = 5000 } = options;

    // Build action buttons
    const toastActions: ToastAction[] = [...actions];

    // Add retry button for retryable errors
    if (error.retryable && onRetry) {
      toastActions.unshift({
        label: "Retry",
        onClick: async () => {
          try {
            await onRetry();
          } catch (retryError) {
            console.error("Retry failed:", retryError);
          }
        },
      });
    }

    // Add copy trace ID button if trace ID exists
    if (error.traceId) {
      toastActions.push({
        label: "Copy Trace ID",
        onClick: () => {
          navigator.clipboard.writeText(error.traceId!);
          sonnerToast.success("Trace ID copied to clipboard");
        },
      });
    }

    // Display the toast with primary action
    const primaryAction = toastActions[0];

    sonnerToast.error(title, {
      description,
      duration,
      action: primaryAction
        ? {
            label: primaryAction.label,
            onClick: primaryAction.onClick,
          }
        : undefined,
      // Note: Sonner doesn't natively support multiple actions, so we show the most important one
      // For multiple actions, consider using a custom toast component
    });

    // Log error details for debugging
    console.error("[Toast Error]", {
      code: error.code,
      status: error.status,
      detail: error.detail,
      traceId: error.traceId,
      metadata: error.metadata,
      stack: error.stack,
    });
  },

  /**
   * Display a success toast
   */
  success(message: string, description?: string) {
    sonnerToast.success(message, { description });
  },

  /**
   * Display an info toast
   */
  info(message: string, description?: string) {
    sonnerToast.info(message, { description });
  },

  /**
   * Display a warning toast
   */
  warning(message: string, description?: string) {
    sonnerToast.warning(message, { description });
  },

  /**
   * Display a loading toast
   */
  loading(message: string, description?: string) {
    return sonnerToast.loading(message, { description });
  },

  /**
   * Dismiss a toast by ID
   */
  dismiss(toastId?: string | number) {
    sonnerToast.dismiss(toastId);
  },

  /**
   * Display a promise toast that updates based on promise state
   */
  promise<T>(
    promise: Promise<T>,
    options: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    },
  ) {
    return sonnerToast.promise(promise, options);
  },
};

/**
 * Hook-friendly version that can be used in React components
 */
export function useToast() {
  return toast;
}
