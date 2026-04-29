import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [GitHub],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    jwt({ token, account, profile }) {
      if (account?.provider === "github" && profile) {
        token.githubId = profile.id;
        // Store the access token from GitHub OAuth
        if (account.access_token) {
          token.accessToken = account.access_token;
        }
      }
      return token;
    },
    session({ session, token }) {
      if (typeof token.githubId === "number") {
        (session.user as typeof session.user & { githubId: number }).githubId =
          token.githubId;
      }
      // Add accessToken to session for API route authentication
      if (token.accessToken) {
        (session as typeof session & { accessToken: string }).accessToken =
          token.accessToken as string;
      }
      return session;
    },
  },
});
