import { NextRequest } from 'next/server';
import { auth } from '@/auth';
import { mintApiToken } from '@/lib/mint-api-token';

/**
 * SSE endpoint for streaming run events
 * 
 * Proxies requests to the backend FastAPI SSE endpoint with authentication
 */
export async function GET(request: NextRequest) {
  try {
    // Get session for authentication
    const session = await auth();
    if (!session?.user) {
      return new Response('Unauthorized', { status: 401 });
    }

    // Get query parameters
    const searchParams = request.nextUrl.searchParams;
    const runId = searchParams.get('run_id');
    const fromSeq = searchParams.get('from') || '0';

    if (!runId) {
      return new Response('Missing run_id parameter', { status: 400 });
    }

    const apiToken = await mintApiToken(session);

    // Build backend URL
    const backendUrl = new URL(
      `/api/runs/${runId}/events`,
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    );
    backendUrl.searchParams.set('from', fromSeq);

    // Fetch from backend with SSE
    const response = await fetch(backendUrl.toString(), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Accept': 'text/event-stream',
      },
      // @ts-expect-error - Next.js supports duplex for streaming
      duplex: 'half',
    });

    if (!response.ok) {
      return new Response(
        `Backend request failed: ${response.status} ${response.statusText}`,
        { status: response.status }
      );
    }

    // Return SSE stream
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch (error) {
    console.error('SSE stream error:', error);
    return new Response(
      error instanceof Error ? error.message : 'Internal server error',
      { status: 500 }
    );
  }
}
