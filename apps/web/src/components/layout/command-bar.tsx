"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Plus, Settings, LogOut, Bot, Moon, Sun, Keyboard } from "lucide-react";
import { useTheme } from "next-themes";
import { signOut } from "next-auth/react";
import { useThreads } from "@/features/threads/hooks/use-threads";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { KeyboardShortcutsDialog } from "./keyboard-shortcuts-dialog";

interface CommandBarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandBar({ open, onOpenChange }: CommandBarProps) {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { createThread } = useThreads();
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Register keyboard shortcuts
  useKeyboardShortcuts({
    onToggleTheme: () => {
      setTheme(theme === "dark" ? "light" : "dark");
    },
    onShowShortcuts: () => setShowShortcuts(true),
  });

  const handleNewThread = async () => {
    try {
      const newThread = await createThread();
      router.push(`/threads/${newThread.id}`);
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to create thread:", error);
    }
  };

  const handleSignOut = async () => {
    await signOut({ callbackUrl: "/login" });
    onOpenChange(false);
  };

  return (
    <>
      <CommandDialog open={open} onOpenChange={onOpenChange}>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading="Actions">
            <CommandItem onSelect={handleNewThread}>
              <Plus className="mr-2 h-4 w-4" />
              <span>New Thread</span>
            </CommandItem>
            <CommandItem
              onSelect={() => {
                setTheme(theme === "dark" ? "light" : "dark");
                onOpenChange(false);
              }}
            >
              {theme === "dark" ? (
                <Sun className="mr-2 h-4 w-4" />
              ) : (
                <Moon className="mr-2 h-4 w-4" />
              )}
              <span>Toggle Theme</span>
              <kbd className="ml-auto text-xs text-zinc-500">⌘J</kbd>
            </CommandItem>
            <CommandItem
              onSelect={() => {
                setShowShortcuts(true);
                onOpenChange(false);
              }}
            >
              <Keyboard className="mr-2 h-4 w-4" />
              <span>Keyboard Shortcuts</span>
              <kbd className="ml-auto text-xs text-zinc-500">⌘/</kbd>
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Navigation">
            <CommandItem
              onSelect={() => {
                router.push("/threads");
                onOpenChange(false);
              }}
            >
              <Bot className="mr-2 h-4 w-4" />
              <span>All Threads</span>
            </CommandItem>
            <CommandItem
              onSelect={() => {
                router.push("/settings");
                onOpenChange(false);
              }}
            >
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Account">
            <CommandItem onSelect={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sign Out</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      <KeyboardShortcutsDialog
        open={showShortcuts}
        onOpenChange={setShowShortcuts}
      />
    </>
  );
}
