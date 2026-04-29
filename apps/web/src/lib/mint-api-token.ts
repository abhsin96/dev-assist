import "server-only";
import { SignJWT } from "jose";
import type { Session } from "next-auth";

const secret = new TextEncoder().encode(process.env.API_JWT_SECRET);

/**
 * Mint a short-lived HS256 JWT for authenticating server-to-backend calls.
 * The FastAPI backend validates these with the same API_JWT_SECRET.
 */
export async function mintApiToken(session: Session): Promise<string> {
  return new SignJWT({
    sub: session.user?.email ?? "",
    name: session.user?.name ?? null,
    image: session.user?.image ?? null,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(secret);
}
