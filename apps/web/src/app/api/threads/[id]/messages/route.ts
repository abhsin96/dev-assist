import { auth } from "@/auth";
import { mintApiToken } from "@/lib/mint-api-token";
import { NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const params = await context.params;
  const session = await auth();

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const token = await mintApiToken(session);
    const response = await fetch(
      `${API_BASE_URL}/api/threads/${params.id}/messages`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json([], { status: 200 });
      }
      throw new Error(`Backend returned ${response.status}`);
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Failed to fetch thread messages:", error);
    return NextResponse.json([], { status: 200 });
  }
}
