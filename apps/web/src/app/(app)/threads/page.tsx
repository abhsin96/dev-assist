"use client";

import { MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThreadListItem } from "@/features/threads/components/thread-list-item";
import { useThreads } from "@/features/threads/hooks/use-threads";

export default function ThreadsPage() {
  const { threads, isLoading, createThread } = useThreads();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-zinc-500 dark:text-zinc-400">
          Loading threads...
        </div>
      </div>
    );
  }

  if (threads.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
            <MessageSquare className="h-6 w-6 text-zinc-600 dark:text-zinc-400" />
          </div>
          <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            No conversations yet
          </h2>
          <p className="mt-2 text-zinc-500 dark:text-zinc-400">
            Start a new conversation to get help with your development tasks.
          </p>
          <Button onClick={createThread} className="mt-6">
            Start New Conversation
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            Conversations
          </h1>
          <Button onClick={createThread} size="sm">
            New Thread
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="space-y-1">
          {threads.map((thread) => (
            <ThreadListItem key={thread.id} thread={thread} />
          ))}
        </div>
      </div>
    </div>
  );
}
