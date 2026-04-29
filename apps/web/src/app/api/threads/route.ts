import { auth } from "@/auth";
import { NextResponse } from "next/server";

// Mock thread data for now - will be replaced with actual API calls
const mockThreads = [
  {
    id: "1",
    title: "Getting started with DevHub",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "2",
    title: "How to use AI agents",
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    updatedAt: new Date(Date.now() - 172800000).toISOString(),
  },
];

export async function GET() {
  const session = await auth();
  
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // TODO: Fetch actual threads from backend API
  return NextResponse.json(mockThreads);
}

export async function POST() {
  const session = await auth();
  
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // TODO: Create thread via backend API
  const newThread = {
    id: String(Date.now()),
    title: "New conversation",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  return NextResponse.json(newThread, { status: 201 });
}
