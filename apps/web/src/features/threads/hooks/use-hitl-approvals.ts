"use client";

import { useState, useCallback, useEffect } from "react";
import { HITLApprovalData, ApprovalStatus } from "@/components/approvals";
import { apiClient } from "@/lib/api/client";
import { toastBus } from "@/lib/toast/toast-bus";

export interface UseHITLApprovalsOptions {
  runId: string;
  onApprovalResolved?: (approvalId: string, decision: "approved" | "rejected") => void;
}

export interface UseHITLApprovalsReturn {
  approvals: Map<string, HITLApprovalData>;
  addApproval: (approval: HITLApprovalData) => void;
  updateApprovalStatus: (approvalId: string, status: ApprovalStatus) => void;
  handleApprove: (approvalId: string, patchedArgs?: Record<string, unknown>) => Promise<void>;
  handleReject: (approvalId: string) => Promise<void>;
  pendingApprovals: HITLApprovalData[];
}

/**
 * Hook for managing HITL approvals in a thread
 * Handles approval state, submission, and expiration
 */
export function useHITLApprovals({
  runId,
  onApprovalResolved,
}: UseHITLApprovalsOptions): UseHITLApprovalsReturn {
  const [approvals, setApprovals] = useState<Map<string, HITLApprovalData>>(new Map());

  // Add a new approval to the map
  const addApproval = useCallback((approval: HITLApprovalData) => {
    setApprovals((prev) => {
      const next = new Map(prev);
      next.set(approval.approvalId, { ...approval, status: "pending" });
      return next;
    });
  }, []);

  // Update approval status
  const updateApprovalStatus = useCallback((approvalId: string, status: ApprovalStatus) => {
    setApprovals((prev) => {
      const next = new Map(prev);
      const approval = next.get(approvalId);
      if (approval) {
        next.set(approvalId, { ...approval, status });
      }
      return next;
    });
  }, []);

  // Handle approval submission
  const handleApprove = useCallback(
    async (approvalId: string, patchedArgs?: Record<string, unknown>) => {
      try {
        await apiClient.post(`/runs/${runId}/approvals`, {
          approval_id: approvalId,
          decision: "approved",
          patched_args: patchedArgs,
        });

        updateApprovalStatus(approvalId, "approved");
        toastBus.success("Approval submitted successfully");

        if (onApprovalResolved) {
          onApprovalResolved(approvalId, "approved");
        }
      } catch (error) {
        toastBus.error("Failed to submit approval");
        throw error;
      }
    },
    [runId, updateApprovalStatus, onApprovalResolved]
  );

  // Handle rejection submission
  const handleReject = useCallback(
    async (approvalId: string) => {
      try {
        await apiClient.post(`/runs/${runId}/approvals`, {
          approval_id: approvalId,
          decision: "rejected",
        });

        updateApprovalStatus(approvalId, "rejected");
        toastBus.success("Action rejected successfully");

        if (onApprovalResolved) {
          onApprovalResolved(approvalId, "rejected");
        }
      } catch (error) {
        toastBus.error("Failed to reject action");
        throw error;
      }
    },
    [runId, updateApprovalStatus, onApprovalResolved]
  );

  // Check for expired approvals
  useEffect(() => {
    const checkExpiration = () => {
      const now = new Date();
      setApprovals((prev) => {
        const next = new Map(prev);
        let hasChanges = false;

        for (const [id, approval] of next.entries()) {
          if (approval.status === "pending" && new Date(approval.expiresAt) < now) {
            next.set(id, { ...approval, status: "expired" });
            hasChanges = true;
            toastBus.warning(`Approval "${approval.summary}" has expired`);
          }
        }

        return hasChanges ? next : prev;
      });
    };

    // Check every 5 seconds
    const interval = setInterval(checkExpiration, 5000);
    return () => clearInterval(interval);
  }, []);

  // Get pending approvals in FIFO order
  const pendingApprovals = Array.from(approvals.values())
    .filter((approval) => approval.status === "pending")
    .sort((a, b) => new Date(a.expiresAt).getTime() - new Date(b.expiresAt).getTime());

  return {
    approvals,
    addApproval,
    updateApprovalStatus,
    handleApprove,
    handleReject,
    pendingApprovals,
  };
}