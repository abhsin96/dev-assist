"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, ExternalLink } from "lucide-react";
import { Trace } from "./trace";
import type { TraceData } from "./types";

export interface TraceDrawerProps {
  messageId: string;
  runId: string;
  traceData: TraceData;
  langsmithUrl?: string;
  children?: React.ReactNode;
}

/**
 * Drawer component for viewing agent execution traces
 * Opens from assistant messages to show full trace tree
 */
export function TraceDrawer({
  messageId,
  runId,
  traceData,
  langsmithUrl,
  children,
}: TraceDrawerProps) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        {children || (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-2 text-xs text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            <Activity className="h-3.5 w-3.5" />
            View trace
          </Button>
        )}
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl lg:max-w-4xl p-0 flex flex-col"
      >
        <SheetHeader className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-base font-semibold">
                Agent Trace
              </SheetTitle>
              <SheetDescription className="text-xs mt-1">
                Run ID: {runId}
              </SheetDescription>
            </div>
            {langsmithUrl && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-2 text-xs"
                asChild
              >
                <a
                  href={langsmithUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  LangSmith
                </a>
              </Button>
            )}
          </div>
        </SheetHeader>
        <ScrollArea className="flex-1">
          <div className="p-6">
            <Trace data={traceData} runId={runId} />
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
