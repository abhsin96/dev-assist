export default async function ThreadsPage() {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Welcome to DevHub AI
        </h2>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">
          Select a thread from the sidebar or create a new one to get started.
        </p>
      </div>
    </div>
  );
}
