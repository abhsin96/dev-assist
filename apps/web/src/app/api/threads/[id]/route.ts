import { auth } from "@/auth";
import { NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const params = await context.params;
  const session = await auth();

  if (!session?.accessToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const response = await fetch(`${API_BASE_URL}/threads/${params.id}`, {
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Thread not found" },
          { status: 404 },
        );
      }
      throw new Error(`Backend returned ${response.status}`);
    }

    const thread = await response.json();
    return NextResponse.json(thread);
  } catch (error) {
    console.error("Failed to fetch thread:", error);
    return NextResponse.json(
      { error: "Failed to fetch thread" },
      { status: 500 },
    );
  }
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const params = await context.params;
  const session = await auth();

  if (!session?.accessToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();
    const response = await fetch(`${API_BASE_URL}/threads/${params.id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.accessToken}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Thread not found" },
          { status: 404 },
        );
      }
      throw new Error(`Backend returned ${response.status}`);
    }

    const thread = await response.json();
    return NextResponse.json(thread);
  } catch (error) {
    console.error("Failed to update thread:", error);
    return NextResponse.json(
      { error: "Failed to update thread" },
      { status: 500 },
    );
  }
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const params = await context.params;
  const session = await auth();

  if (!session?.accessToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const response = await fetch(`${API_BASE_URL}/threads/${params.id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Thread not found" },
          { status: 404 },
        );
      }
      throw new Error(`Backend returned ${response.status}`);
    }

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error("Failed to delete thread:", error);
    return NextResponse.json(
      { error: "Failed to delete thread" },
      { status: 500 },
    );
  }
}
