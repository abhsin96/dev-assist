"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AlertCircle, CheckCircle2, XCircle } from "lucide-react";

export interface HITLApprovalEditorProps {
  toolName: string;
  initialArgs: Record<string, unknown>;
  onSubmit: (patchedArgs: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
}

export function HITLApprovalEditor({
  toolName,
  initialArgs,
  onSubmit,
  onCancel,
  isSubmitting,
}: HITLApprovalEditorProps) {
  // Derive the JSON string from initialArgs
  const initialArgsJson = JSON.stringify(initialArgs, null, 2);
  const [editedArgsJson, setEditedArgsJson] = useState(initialArgsJson);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Sync state when initialArgs reference changes (not on every render)
  useEffect(() => {
    const newArgsJson = JSON.stringify(initialArgs, null, 2);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEditedArgsJson(newArgsJson);
  }, [initialArgs]);

  const handleSubmit = async () => {
    try {
      const parsed = JSON.parse(editedArgsJson);
      setValidationError(null);
      await onSubmit(parsed);
    } catch (err) {
      if (err instanceof SyntaxError) {
        setValidationError("Invalid JSON format. Please check your syntax.");
      } else {
        setValidationError("Failed to submit approval. Please try again.");
      }
    }
  };

  const handleJsonChange = (value: string) => {
    setEditedArgsJson(value);
    // Clear validation error when user starts editing
    if (validationError) {
      setValidationError(null);
    }
  };

  const validateJson = () => {
    try {
      JSON.parse(editedArgsJson);
      setValidationError(null);
      return true;
    } catch (error) {
      setValidationError("Invalid JSON format");
      return false;
    }
  };

  return (
    <Card className="border-amber-200 dark:border-amber-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          Edit Tool Arguments
        </CardTitle>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="space-y-2">
          <div className="text-xs text-zinc-600 dark:text-zinc-400">
            Tool: <span className="font-mono font-semibold">{toolName}</span>
          </div>
          <div className="relative">
            <textarea
              value={editedArgsJson}
              onChange={(e) => handleJsonChange(e.target.value)}
              onBlur={validateJson}
              className="w-full h-48 p-3 font-mono text-xs rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 focus:outline-none focus:ring-2 focus:ring-amber-500 dark:focus:ring-amber-400"
              placeholder="Enter JSON arguments..."
              disabled={isSubmitting}
            />
          </div>
          {validationError && (
            <div className="flex items-start gap-2 text-xs text-red-600 dark:text-red-400">
              <XCircle className="h-3 w-3 mt-0.5" />
              <span>{validationError}</span>
            </div>
          )}
        </div>
      </CardContent>
      <CardFooter className="flex gap-2">
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || !!validationError}
          size="sm"
          className="flex-1"
        >
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Submit & Approve
        </Button>
        <Button
          onClick={onCancel}
          disabled={isSubmitting}
          variant="outline"
          size="sm"
          className="flex-1"
        >
          Cancel
        </Button>
      </CardFooter>
    </Card>
  );
}
