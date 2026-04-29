"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ThreadSidebar } from "./thread-sidebar";
import { CommandBar } from "./command-bar";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";

interface AppShellProps {
  children: React.ReactNode;
  user?: {
    name?: string | null;
    email?: string | null;
  };
}

export function AppShell({ children, user }: AppShellProps) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isCommandBarOpen, setIsCommandBarOpen] = useState(false);

  // Register keyboard shortcuts
  useKeyboardShortcuts({
    onCommandK: () => setIsCommandBarOpen(true),
  });

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 md:block">
        <ThreadSidebar />
      </aside>

      {/* Mobile Sidebar */}
      <Sheet open={isMobileSidebarOpen} onOpenChange={setIsMobileSidebarOpen}>
        <SheetTrigger asChild className="md:hidden">
          <Button
            variant="ghost"
            size="icon"
            className="fixed left-4 top-4 z-50"
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <ThreadSidebar onThreadSelect={() => setIsMobileSidebarOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="flex h-14 items-center justify-between border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">DevHub AI</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCommandBarOpen(true)}
              className="hidden gap-2 md:flex"
            >
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                Search
              </span>
              <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-zinc-200 bg-zinc-100 px-1.5 font-mono text-[10px] font-medium text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400">
                ⌘K
              </kbd>
            </Button>
            {user && (
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                {user.name ?? user.email}
              </span>
            )}
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto">{children}</div>
      </main>

      {/* Command Bar */}
      <CommandBar open={isCommandBarOpen} onOpenChange={setIsCommandBarOpen} />
    </div>
  );
}
