"use client";

import { ArrowDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface JumpToLatestProps {
  show: boolean;
  onClick: () => void;
  className?: string;
}

/**
 * Floating "Jump to latest" pill shown when user scrolls up during streaming
 */
export function JumpToLatest({ show, onClick, className }: JumpToLatestProps) {
  if (!show) return null;

  return (
    <div
      className={cn(
        "fixed bottom-24 left-1/2 -translate-x-1/2 z-10",
        "animate-in fade-in slide-in-from-bottom-2 duration-200",
        className
      )}
    >
      <Button
        onClick={onClick}
        size="sm"
        className="shadow-lg gap-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200"
      >
        <ArrowDown className="h-4 w-4" />
        Jump to latest
      </Button>
    </div>
  );
}
