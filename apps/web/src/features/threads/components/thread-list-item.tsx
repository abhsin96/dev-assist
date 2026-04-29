"use client";

import { useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { MoreVertical, Trash2, Edit2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useThreadMutations } from "../hooks/use-thread-mutations";

interface Thread {
  id: string;
  title?: string;
  updatedAt: string;
  createdAt: string;
}

interface ThreadListItemProps {
  thread: Thread;
  isActive?: boolean;
}

export function ThreadListItem({ thread, isActive }: ThreadListItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(
    thread.title || "New conversation",
  );
  const { updateThread, deleteThread } = useThreadMutations();

  const handleDoubleClick = () => {
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (editedTitle.trim() && editedTitle !== thread.title) {
      await updateThread(thread.id, editedTitle.trim());
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      setEditedTitle(thread.title || "New conversation");
      setIsEditing(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await deleteThread(thread.id);
  };

  // Safely parse the date with fallback
  const updatedDate = thread.updatedAt
    ? new Date(thread.updatedAt)
    : new Date();
  const isValidDate = !isNaN(updatedDate.getTime());

  const timeAgo = isValidDate
    ? formatDistanceToNow(updatedDate, { addSuffix: true })
    : "recently";

  return (
    <div
      className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
        isActive
          ? "bg-zinc-100 dark:bg-zinc-800"
          : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
      }`}
    >
      <Link href={`/threads/${thread.id}`} className="flex-1 min-w-0">
        <div className="flex flex-col gap-1">
          {isEditing ? (
            <Input
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              onBlur={handleSave}
              onKeyDown={handleKeyDown}
              className="h-7 text-sm"
              autoFocus
              onClick={(e) => e.preventDefault()}
            />
          ) : (
            <div
              className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate"
              onDoubleClick={handleDoubleClick}
            >
              {thread.title || "New conversation"}
            </div>
          )}
          <div className="text-xs text-zinc-500 dark:text-zinc-400">
            {timeAgo}
          </div>
        </div>
      </Link>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
          >
            <MoreVertical className="h-4 w-4" />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsEditing(true);
            }}
          >
            <Edit2 className="mr-2 h-4 w-4" />
            Rename
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={handleDelete}
            className="text-red-600 dark:text-red-400"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
