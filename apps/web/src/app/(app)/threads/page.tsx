import { auth } from "@/auth";
import { SignOutButton } from "@/features/auth/components/sign-out-button";

export default async function ThreadsPage() {
  const session = await auth();

  return (
    <main className="flex min-h-screen flex-col p-8">
      <header className="flex items-center justify-between border-b border-zinc-200 pb-4 dark:border-zinc-800">
        <h1 className="text-xl font-semibold">DevHub AI</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">
            {session?.user?.name ?? session?.user?.email}
          </span>
          <SignOutButton />
        </div>
      </header>
      <div className="flex flex-1 items-center justify-center">
        <p className="text-zinc-500">No threads yet. Start a conversation to get started.</p>
      </div>
    </main>
  );
}
