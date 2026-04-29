import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';

/**
 * API endpoint for starting a new run
 */
export async function POST(request: NextRequest) {
  try {
    // Get session for authentication
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Parse request body
    const body = await request.json();
    const { thread_id, message } = body;

    if (!thread_id || !message) {
      return NextResponse.json(
        { error: 'Missing thread_id or message' },
        { status: 400 }
      );
    }

    // Get access token from session (assuming it's stored in the session)
    // For now, we'll use a placeholder - this needs to be configured based on your auth setup
    const accessToken = (session as { accessToken?: string }).accessToken || '';

    // Call backend API
    const backendUrl = new URL(
      '/api/runs/start',
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    );

    const response = await fetch(backendUrl.toString(), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ thread_id, message }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `Backend request failed: ${response.status} ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Start run error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
