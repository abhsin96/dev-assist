import "server-only";
import { SignJWT } from "jose";
import { NextResponse } from "next/server";
import { auth } from "@/auth";

const secret = new TextEncoder().encode(process.env.API_JWT_SECRET);

export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const token = await new SignJWT({
    sub: session.user.email,
    name: session.user.name ?? null,
    image: session.user.image ?? null,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(secret);

  return NextResponse.json({ token });
}
