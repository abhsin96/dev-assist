import { notFound } from "next/navigation";
import { ThreadDetail } from "@/features/threads/components/thread-detail";

interface ThreadPageProps {
  params: {
    id: string;
  };
}

// Server component that fetches initial thread data
export default async function ThreadPage({ params }: ThreadPageProps) {
  const { id } = params;

  // Validate UUID format
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(id)) {
    notFound();
  }

  // Server-side fetch for initial data (SSR)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  let thread = null;

  try {
    const response = await fetch(`${apiUrl}/api/threads/${id}`, {
      cache: "no-store", // Always fetch fresh data
    });

    if (response.ok) {
      thread = await response.json();
    } else if (response.status === 404) {
      notFound();
    }
  } catch (error) {
    console.error("Failed to fetch thread:", error);
    // Continue to render - client component will handle error state
  }

  // Hand off to client component for streaming and interactivity
  return <ThreadDetail threadId={id} initialThread={thread} />;
}
