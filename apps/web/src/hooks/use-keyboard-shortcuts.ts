"use client";

import { useEffect } from "react";

interface KeyboardShortcutHandlers {
  onCommandK?: () => void;
  onToggleTheme?: () => void;
  onShowShortcuts?: () => void;
  onNewThread?: () => void;
}

export function useKeyboardShortcuts(handlers: KeyboardShortcutHandlers) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Cmd+K or Ctrl+K - Open command palette
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        handlers.onCommandK?.();
        return;
      }

      // Cmd+J or Ctrl+J - Toggle theme
      if ((event.metaKey || event.ctrlKey) && event.key === "j") {
        event.preventDefault();
        handlers.onToggleTheme?.();
        return;
      }

      // Cmd+/ or Ctrl+/ - Show shortcuts
      if ((event.metaKey || event.ctrlKey) && event.key === "/") {
        event.preventDefault();
        handlers.onShowShortcuts?.();
        return;
      }

      // Cmd+N or Ctrl+N - New thread
      if ((event.metaKey || event.ctrlKey) && event.key === "n") {
        event.preventDefault();
        handlers.onNewThread?.();
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handlers]);
}
