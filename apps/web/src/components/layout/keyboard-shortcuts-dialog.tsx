"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface KeyboardShortcutsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const shortcuts = [
  {
    category: "General",
    items: [
      { keys: ["⌘", "K"], description: "Open command palette" },
      { keys: ["⌘", "J"], description: "Toggle theme" },
      { keys: ["⌘", "/"], description: "Show keyboard shortcuts" },
      { keys: ["Esc"], description: "Close dialog" },
    ],
  },
  {
    category: "Navigation",
    items: [
      { keys: ["⌘", "N"], description: "New thread" },
      { keys: ["↑", "↓"], description: "Navigate threads" },
      { keys: ["Enter"], description: "Open selected thread" },
    ],
  },
  {
    category: "Accessibility",
    items: [
      { keys: ["Tab"], description: "Move focus forward" },
      { keys: ["Shift", "Tab"], description: "Move focus backward" },
      { keys: ["Space"], description: "Activate focused element" },
    ],
  },
];

export function KeyboardShortcutsDialog({
  open,
  onOpenChange,
}: KeyboardShortcutsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Navigate DevHub efficiently with these keyboard shortcuts
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {shortcuts.map((section) => (
            <div key={section.category}>
              <h3 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {section.category}
              </h3>
              <div className="space-y-2">
                {section.items.map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-md border border-zinc-200 bg-zinc-50 px-4 py-2 dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <span className="text-sm text-zinc-700 dark:text-zinc-300">
                      {item.description}
                    </span>
                    <div className="flex gap-1">
                      {item.keys.map((key, keyIndex) => (
                        <kbd
                          key={keyIndex}
                          className="inline-flex h-6 min-w-[24px] items-center justify-center rounded border border-zinc-300 bg-white px-2 font-mono text-xs font-medium text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
