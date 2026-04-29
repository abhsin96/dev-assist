"use client";

import { useState } from "react";
import { Plus, MessageSquare, Loader2 } from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { Virtuoso } from "react-virtuoso";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThreadListItem } from "@/features/threads/components/thread-list-item";
import { useThreads } from "@/features/threads/hooks/use-threads";

interface ThreadSidebarProps {
  onThreadSelect?: () => void;
}

export function ThreadSidebar({ onThreadSelect }: ThreadSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { threads, isLoading, createThread } = useThreads();

  // Extract thread ID from pathname
  const activeThreadId = pathname?.match(/\/threads\/([^/]+)/)?.[1];
  const [isCreating, setIsCreating] = useState(false);

  const handleNewThread = async () => {
    setIsCreating(true);
    try {
      const newThread = await createThread();
      router.push(`/threads/${newThread.id}`);
      onThreadSelect?.();
    } catch (error) {
      console.error("Failed to create thread:", error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="text-sm font-semibold">Threads</h2>
        <Button
          size="sm"
          onClick={handleNewThread}
          disabled={isCreating}
          className="h-8 w-8 p-0"
        >
          {isCreating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
          </div>
        ) : threads.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center p-4 text-center">
            <MessageSquare className="mb-2 h-8 w-8 text-zinc-300 dark:text-zinc-700" />
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              No threads yet
            </p>
            <Button
              size="sm"
              onClick={handleNewThread}
              className="mt-4"
              disabled={isCreating}
            >
              Create your first thread
            </Button>
          </div>
        ) : threads.length > 200 ? (
          // Virtualized list for > 200 threads
          <Virtuoso
            data={threads}
            itemContent={(index, thread) => (
              <ThreadListItem
                key={thread.id}
                thread={thread}
                isActive={thread.id === activeThreadId}
              />
            )}
            className="h-full"
          />
        ) : (
          // Regular scrollable list for <= 200 threads
          <ScrollArea className="h-full">
            <div className="space-y-1 p-2">
              {threads.map((thread) => (
                <ThreadListItem
                  key={thread.id}
                  thread={thread}
                  isActive={thread.id === activeThreadId}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
