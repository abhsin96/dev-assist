"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { toast } from "sonner";

interface Thread {
  id: string;
  title?: string;
  updatedAt: string;
  createdAt: string;
}

interface UpdateThreadRequest {
  title: string;
}

export function useThreadMutations() {
  const queryClient = useQueryClient();

  // Update thread mutation
  const updateThreadMutation = useMutation({
    mutationFn: async ({
      threadId,
      title,
    }: {
      threadId: string;
      title: string;
    }): Promise<Thread> => {
      return await api.patch<Thread, UpdateThreadRequest>(
        `/api/threads/${threadId}`,
        { title }
      );
    },
    onMutate: async ({ threadId, title }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["threads"] });

      // Snapshot previous value
      const previousThreads = queryClient.getQueryData<Thread[]>(["threads"]);

      // Optimistically update
      queryClient.setQueryData<Thread[]>(["threads"], (old = []) =>
        old.map((thread) =>
          thread.id === threadId
            ? { ...thread, title, updatedAt: new Date().toISOString() }
            : thread
        )
      );

      return { previousThreads };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousThreads) {
        queryClient.setQueryData(["threads"], context.previousThreads);
      }
      toast.error("Failed to rename thread");
    },
    onSuccess: () => {
      toast.success("Thread renamed successfully");
    },
  });

  // Delete thread mutation
  const deleteThreadMutation = useMutation({
    mutationFn: async (threadId: string): Promise<void> => {
      await api.delete(`/api/threads/${threadId}`);
    },
    onMutate: async (threadId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["threads"] });

      // Snapshot previous value
      const previousThreads = queryClient.getQueryData<Thread[]>(["threads"]);

      // Optimistically update
      queryClient.setQueryData<Thread[]>(["threads"], (old = []) =>
        old.filter((thread) => thread.id !== threadId)
      );

      return { previousThreads, threadId };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousThreads) {
        queryClient.setQueryData(["threads"], context.previousThreads);
      }
      toast.error("Failed to delete thread");
    },
    onSuccess: (data, variables, context) => {
      // Show undo toast
      toast.success("Thread deleted", {
        action: {
          label: "Undo",
          onClick: () => {
            if (context?.previousThreads) {
              queryClient.setQueryData(["threads"], context.previousThreads);
              toast.success("Thread restored");
            }
          },
        },
      });
    },
  });

  const updateThread = async (threadId: string, title: string) => {
    return updateThreadMutation.mutateAsync({ threadId, title });
  };

  const deleteThread = async (threadId: string) => {
    return deleteThreadMutation.mutateAsync(threadId);
  };

  return {
    updateThread,
    deleteThread,
    isUpdating: updateThreadMutation.isPending,
    isDeleting: deleteThreadMutation.isPending,
  };
}
