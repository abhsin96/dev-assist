"use client";

import { useState } from "react";
import { Plus, MessageSquare, Loader2 } from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { Virtuoso } from "react-virtuoso";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useThreads } from "@/features/threads/hooks/use-threads";

interface ThreadSidebarProps {
  onThreadSelect?: () => void;
}

export function ThreadSidebar({ onThreadSelect }: ThreadSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { threads, isLoading, createThread } = useThreads();
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

  const handleThreadClick = (threadId: string) => {
    router.push(`/threads/${threadId}`);
    onThreadSelect?.();
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
              <ThreadItem
                key={thread.id}
                thread={thread}
                isActive={pathname === `/threads/${thread.id}`}
                onClick={() => handleThreadClick(thread.id)}
              />
            )}
            className="h-full"
          />
        ) : (
          // Regular scrollable list for <= 200 threads
          <ScrollArea className="h-full">
            <div className="space-y-1 p-2">
              {threads.map((thread) => (
                <ThreadItem
                  key={thread.id}
                  thread={thread}
                  isActive={pathname === `/threads/${thread.id}`}
                  onClick={() => handleThreadClick(thread.id)}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}

interface ThreadItemProps {
  thread: {
    id: string;
    title?: string;
    updatedAt: string;
  };
  isActive: boolean;
  onClick: () => void;
}

function ThreadItem({ thread, isActive, onClick }: ThreadItemProps) {
  const title = thread.title || "New conversation";
  const date = new Date(thread.updatedAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-md px-3 py-2 text-left transition-colors",
        "hover:bg-zinc-100 dark:hover:bg-zinc-800",
        isActive && "bg-zinc-100 dark:bg-zinc-800",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {title}
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{date}</p>
        </div>
      </div>
    </button>
  );
}
