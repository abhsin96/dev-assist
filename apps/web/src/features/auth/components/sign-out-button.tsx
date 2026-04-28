"use client";

import { useCurrentUser } from "@/features/auth/hooks/use-current-user";

export function SignOutButton() {
  const { logout } = useCurrentUser();

  return (
    <button
      onClick={logout}
      className="rounded-md border border-zinc-200 px-3 py-1.5 text-sm transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
    >
      Sign out
    </button>
  );
}
