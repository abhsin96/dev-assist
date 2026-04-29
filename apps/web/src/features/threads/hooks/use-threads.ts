"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

interface Thread {
  id: string;
  title?: string;
  updatedAt: string;
  createdAt: string;
}

interface CreateThreadResponse {
  id: string;
  title?: string;
  createdAt: string;
  updatedAt: string;
}

export function useThreads() {
  const queryClient = useQueryClient();

  // Fetch threads
  const {
    data: threads = [],
    isLoading,
    error,
  } = useQuery<Thread[]>({
    queryKey: ["threads"],
    queryFn: async () => {
      return await api.get<Thread[]>("/api/threads");
    },
  });

  // Create thread mutation
  const createThreadMutation = useMutation({
    mutationFn: async (): Promise<CreateThreadResponse> => {
      return await api.post<CreateThreadResponse>("/api/threads", {});
    },
    onSuccess: (newThread) => {
      // Optimistically update the cache
      queryClient.setQueryData<Thread[]>(["threads"], (old = []) => [
        newThread,
        ...old,
      ]);
    },
  });

  const createThread = async (): Promise<Thread> => {
    return createThreadMutation.mutateAsync();
  };

  return {
    threads,
    isLoading,
    error,
    createThread,
  };
}
