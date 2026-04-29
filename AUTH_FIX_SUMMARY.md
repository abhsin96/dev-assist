# Authentication Fix Summary - 401 Unauthorized Error

## Problem

The `/api/threads` endpoint was returning **401 Unauthorized** error when accessed from the frontend.

### Root Cause

The NextAuth configuration was not storing the GitHub OAuth `access_token` in the JWT token and session, even though the TypeScript types were properly defined.

**Error Flow:**
1. Frontend calls `/api/threads` (Next.js API route)
2. API route checks for `session.accessToken` 
3. `session.accessToken` was `undefined` because it wasn't being stored during OAuth callback
4. API route returns 401 Unauthorized

## Solution

### Modified File: `apps/web/src/auth.ts`

**Changes Made:**

1. **JWT Callback** - Store the access token from GitHub OAuth:
```typescript
jwt({ token, account, profile }) {
  if (account?.provider === "github" && profile) {
    token.githubId = profile.id;
    // Store the access token from GitHub OAuth
    if (account.access_token) {
      token.accessToken = account.access_token;
    }
  }
  return token;
}
```

2. **Session Callback** - Add the access token to the session:
```typescript
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
}
```

## How It Works Now

1. **OAuth Login Flow:**
   - User logs in with GitHub
   - GitHub returns `access_token` in the account object
   - JWT callback stores `access_token` in the JWT token
   - Session callback adds `access_token` to the session

2. **API Route Authentication:**
   - Frontend calls `/api/threads`
   - Next.js API route calls `await auth()` to get session
   - Session now contains `accessToken`
   - API route uses `session.accessToken` to authenticate with backend
   - Backend API call succeeds with proper Authorization header

## Testing

1. **Sign out and sign in again** to get a fresh session with the access token
2. Navigate to `/threads` page
3. The threads list should now load successfully
4. Check browser DevTools Network tab - `/api/threads` should return 200 OK

## TypeScript Types

The types were already properly defined in `apps/web/src/types/next-auth.d.ts`:

```typescript
declare module "next-auth" {
  interface Session {
    user: {
      githubId?: number;
    } & DefaultSession["user"];
    accessToken?: string;  // ✅ Already defined
  }

  interface JWT {
    githubId?: number;
    accessToken?: string;  // ✅ Already defined
  }
}
```

## Impact

- ✅ Fixes 401 Unauthorized error on `/api/threads` endpoint
- ✅ Enables proper backend API authentication
- ✅ Allows thread list and creation to work correctly
- ✅ No breaking changes to existing functionality

## Next Steps

1. Sign out of the application
2. Sign in again to get a new session with the access token
3. Test thread creation and listing functionality
4. Verify other API routes that depend on `session.accessToken` work correctly
