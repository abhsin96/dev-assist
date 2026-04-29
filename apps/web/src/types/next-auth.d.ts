import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      githubId?: number;
    } & DefaultSession["user"];
    accessToken?: string;
  }

  interface JWT {
    githubId?: number;
    accessToken?: string;
  }
}
