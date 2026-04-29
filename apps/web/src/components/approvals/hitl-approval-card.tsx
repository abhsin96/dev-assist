"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle, Clock, ChevronDown, ChevronUp, Edit } from "lucide-react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { HITLApprovalEditor } from "./hitl-approval-editor";

export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface HITLApprovalData {
  approvalId: string;
  summary: string;
  risk: RiskLevel;
  toolName: string;
  toolArgs: Record<string, unknown>;
  expiresAt: string;
  status?: ApprovalStatus;
}

export interface HITLApprovalCardProps {
  data: HITLApprovalData;
  onApprove: (approvalId: string, patchedArgs?: Record<string, unknown>) => Promise<void>;
  onReject: (approvalId: string) => Promise<void>;
  onRetry?: () => void;
  className?: string;
}

const riskConfig: Record<RiskLevel, { variant: "warning" | "destructive" | "info" | "default"; icon: typeof AlertTriangle; label: string }> = {
  low: { variant: "info", icon: AlertTriangle, label: "Low Risk" },
  medium: { variant: "warning", icon: AlertTriangle, label: "Medium Risk" },
  high: { variant: "destructive", icon: AlertTriangle, label: "High Risk" },
  critical: { variant: "destructive", icon: AlertTriangle, label: "Critical Risk" },
};

const statusConfig: Record<ApprovalStatus, { icon: typeof CheckCircle2; label: string; color: string }> = {
  pending: { icon: Clock, label: "Awaiting Approval", color: "text-amber-600 dark:text-amber-400" },
  approved: { icon: CheckCircle2, label: "Approved", color: "text-green-600 dark:text-green-400" },
  rejected: { icon: XCircle, label: "Rejected", color: "text-red-600 dark:text-red-400" },
  expired: { icon: Clock, label: "Expired", color: "text-zinc-500 dark:text-zinc-400" },
};

export function HITLApprovalCard({
  data,
  onApprove,
  onReject,
  onRetry,
  className,
}: HITLApprovalCardProps) {
  const [isArgsOpen, setIsArgsOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<ApprovalStatus>(data.status ?? "pending");

  const riskInfo = riskConfig[data.risk];
  const statusInfo = statusConfig[currentStatus];
  const RiskIcon = riskInfo.icon;
  const StatusIcon = statusInfo.icon;

  const handleApprove = async (patchedArgs?: Record<string, unknown>) => {
    setIsSubmitting(true);
    try {
      await onApprove(data.approvalId, patchedArgs);
      setCurrentStatus("approved");
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to approve:", error);
      // Error handling will be done by the parent component via toast
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(data.approvalId);
      setCurrentStatus("rejected");
    } catch (error) {
      console.error("Failed to reject:", error);
      // Error handling will be done by the parent component via toast
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditAndApprove = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const isPending = currentStatus === "pending";
  const isExpired = currentStatus === "expired";
  const isFinal = currentStatus === "approved" || currentStatus === "rejected";

  return (
    <Card
      className={cn(
        "border-l-4 transition-all",
        currentStatus === "pending" && "border-l-amber-500 bg-amber-50/50 dark:bg-amber-950/20",
        currentStatus === "approved" && "border-l-green-500 bg-green-50/50 dark:bg-green-950/20",
        currentStatus === "rejected" && "border-l-red-500 bg-red-50/50 dark:bg-red-950/20",
        currentStatus === "expired" && "border-l-zinc-500 bg-zinc-50/50 dark:bg-zinc-950/20",
        className
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base flex items-center gap-2">
              <StatusIcon className={cn("h-4 w-4", statusInfo.color)} />
              {statusInfo.label}
            </CardTitle>
            <CardDescription className="mt-1.5">{data.summary}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={riskInfo.variant}>
              <RiskIcon className="h-3 w-3 mr-1" />
              {riskInfo.label}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        <Collapsible open={isArgsOpen} onOpenChange={setIsArgsOpen}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full justify-between">
              <span className="text-xs font-medium">Tool Arguments</span>
              {isArgsOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <div className="rounded-md bg-zinc-100 dark:bg-zinc-900 p-3">
              <div className="text-xs text-zinc-600 dark:text-zinc-400 mb-1">
                Tool: <span className="font-mono font-semibold">{data.toolName}</span>
              </div>
              <pre className="text-xs overflow-x-auto">
                <code>{JSON.stringify(data.toolArgs, null, 2)}</code>
              </pre>
            </div>
          </CollapsibleContent>
        </Collapsible>

        {isEditing && (
          <div className="mt-3">
            <HITLApprovalEditor
              toolName={data.toolName}
              initialArgs={data.toolArgs}
              onSubmit={handleApprove}
              onCancel={handleCancelEdit}
              isSubmitting={isSubmitting}
            />
          </div>
        )}
      </CardContent>

      <CardFooter className="flex flex-col gap-2">
        {isPending && !isEditing && (
          <div className="flex gap-2 w-full">
            <Button
              onClick={() => handleApprove()}
              disabled={isSubmitting}
              className="flex-1"
              size="sm"
            >
              <CheckCircle2 className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              onClick={handleEditAndApprove}
              disabled={isSubmitting}
              variant="secondary"
              className="flex-1"
              size="sm"
            >
              <Edit className="h-4 w-4 mr-1" />
              Edit & Approve
            </Button>
            <Button
              onClick={handleReject}
              disabled={isSubmitting}
              variant="destructive"
              className="flex-1"
              size="sm"
            >
              <XCircle className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </div>
        )}

        {isExpired && onRetry && (
          <Button onClick={onRetry} variant="outline" className="w-full" size="sm">
            Retry Action
          </Button>
        )}

        {isFinal && (
          <div className="text-xs text-center text-zinc-600 dark:text-zinc-400 w-full">
            This approval has been {currentStatus}.
          </div>
        )}

        {isPending && (
          <div className="text-xs text-center text-zinc-600 dark:text-zinc-400 w-full">
            Expires: {new Date(data.expiresAt).toLocaleString()}
          </div>
        )}
      </CardFooter>
    </Card>
  );
}