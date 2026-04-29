"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Thread {
  id: string;
  title?: string;
  updatedAt: string;
  createdAt: string;
}

interface ThreadDetailProps {
  threadId: string;
  initialThread: Thread | null;
}

export function ThreadDetail({ threadId, initialThread }: ThreadDetailProps) {
  const router = useRouter();

  // Use React Query for client-side data fetching and caching
  const {
    data: thread,
    isLoading,
    error,
  } = useQuery<Thread>({
    queryKey: ["thread", threadId],
    queryFn: async () => {
      return await api.get<Thread>(`/api/threads/${threadId}`);
    },
    initialData: initialThread || undefined,
    retry: 1,
  });

  // Handle error state
  useEffect(() => {
    if (error) {
      console.error("Failed to load thread:", error);
    }
  }, [error]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-zinc-500 dark:text-zinc-400">Loading thread...</div>
      </div>
    );
  }

  if (error || !thread) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
            <MessageSquare className="h-6 w-6 text-red-600 dark:text-red-400" />
          </div>
          <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            Thread not found
          </h2>
          <p className="mt-2 text-zinc-500 dark:text-zinc-400">
            The conversation you are looking for does not exist or has been deleted.
          </p>
          <Button onClick={() => router.push("/threads")} className="mt-6">
            Back to Conversations
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Thread header */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          {thread.title || "New conversation"}
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Last updated {new Date(thread.updatedAt).toLocaleString()}
        </p>
      </div>

      {/* Message history area - placeholder for now */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="flex h-full items-center justify-center">
          <div className="text-center max-w-md">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
              <MessageSquare className="h-6 w-6 text-zinc-600 dark:text-zinc-400" />
            </div>
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              No messages yet
            </h2>
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              Start a conversation by sending a message below.
            </p>
          </div>
        </div>
      </div>

      {/* Message input area - placeholder for now */}
      <div className="border-t border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Type a message... (streaming functionality coming soon)"
            className="flex-1 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
            disabled
          />
          <Button disabled>Send</Button>
        </div>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
          Message streaming will be implemented in the next story
        </p>
      </div>
    </div>
  );
}
