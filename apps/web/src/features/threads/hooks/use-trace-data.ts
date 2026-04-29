"use client";

import { useQuery } from "@tanstack/react-query";
import type { TraceData } from "@/components/trace";

/**
 * Hook for fetching trace data for a specific run
 */
export function useTraceData(runId: string | null) {
  return useQuery({
    queryKey: ["trace", runId],
    queryFn: async () => {
      if (!runId) {
        throw new Error("Run ID is required");
      }

      const response = await fetch(`/api/runs/${runId}/trace`);

      if (!response.ok) {
        throw new Error(`Failed to fetch trace: ${response.statusText}`);
      }

      const data = await response.json();
      return data as TraceData;
    },
    enabled: !!runId,
    staleTime: 30000, // 30 seconds
    retry: 2,
  });
}
