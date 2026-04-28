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
      }
      return token;
    },
    session({ session, token }) {
      if (typeof token.githubId === "number") {
        (session.user as typeof session.user & { githubId: number }).githubId =
          token.githubId;
      }
      return session;
    },
  },
});
