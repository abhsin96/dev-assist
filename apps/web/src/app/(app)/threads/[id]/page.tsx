import { notFound } from "next/navigation";
import { ThreadDetail } from "@/features/threads/components/thread-detail";

interface ThreadPageProps {
  params: {
    id: string;
  };
}

// Server component that validates the thread ID and renders the client component
export default async function ThreadPage({ params }: ThreadPageProps) {
  const { id } = params;

  // Validate UUID format
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(id)) {
    notFound();
  }

  // Let the client component handle data fetching with proper authentication
  // The ThreadDetail component uses React Query and the authenticated API client
  return <ThreadDetail threadId={id} initialThread={null} />;
}
