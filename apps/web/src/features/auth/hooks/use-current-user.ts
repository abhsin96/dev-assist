"use client";

import { signOut, useSession } from "next-auth/react";
import { useQueryClient } from "@tanstack/react-query";

export interface CurrentUser {
  name?: string | null;
  email?: string | null;
  image?: string | null;
}

export function useCurrentUser() {
  const { data: session, status } = useSession();
  const queryClient = useQueryClient();

  const logout = async () => {
    queryClient.clear();
    await signOut({ redirectTo: "/login" });
  };

  return {
    user: (session?.user as CurrentUser | undefined) ?? null,
    isLoading: status === "loading",
    isAuthenticated: status === "authenticated",
    logout,
  };
}
