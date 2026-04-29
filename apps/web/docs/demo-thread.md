# Live Demo: PR Review Thread with Generative UI

This document describes how to create a live demo thread that showcases the generative UI tool cards.

## Demo Scenario

A user is reviewing a pull request and the AI assistant helps by:
1. Fetching the PR diff
2. Analyzing the code changes
3. Suggesting improvements
4. Requesting HITL approval for a risky operation

## Demo Thread Flow

### Step 1: User Request

```
User: "Review PR #123 in the devhub repository and suggest improvements"
```

### Step 2: AI Fetches PR Diff

**Tool Call:** `github_get_pr_diff`

**Renders:** `PRDiffCard` in loading state

```typescript
{
  type: "tool-call",
  toolName: "github_get_pr_diff",
  toolCallId: "call_123",
  toolArgs: {
    repository: "publicis-sapient/devhub",
    pr_number: 123
  }
}
```

### Step 3: PR Diff Result

**Tool Result:** `github_get_pr_diff`

**Renders:** `PRDiffCard` in success state with expandable diff

```typescript
{
  type: "tool-result",
  toolName: "github_get_pr_diff",
  toolCallId: "call_123",
  toolResult: {
    prNumber: 123,
    title: "Add streaming message component",
    author: "john-doe",
    repository: "publicis-sapient/devhub",
    additions: 245,
    deletions: 18,
    changedFiles: 3,
    url: "https://github.com/publicis-sapient/devhub/pull/123",
    diff: "diff --git a/apps/web/src/components/messages/streaming-message.tsx..."
  }
}
```

### Step 4: AI Searches for Related Code

**Tool Call:** `code_search`

**Renders:** `CodeSearchResult` in loading state

```typescript
{
  type: "tool-call",
  toolName: "code_search",
  toolCallId: "call_124",
  toolArgs: {
    query: "streaming message",
    repository: "publicis-sapient/devhub"
  }
}
```

### Step 5: Code Search Results

**Tool Result:** `code_search`

**Renders:** `CodeSearchResult` in success state with expandable matches

```typescript
{
  type: "tool-result",
  toolName: "code_search",
  toolCallId: "call_124",
  toolResult: {
    query: "streaming message",
    repository: "publicis-sapient/devhub",
    totalMatches: 3,
    matches: [
      {
        file: "apps/web/src/features/threads/hooks/use-streaming-message.ts",
        line: 15,
        content: "export function useStreamingMessage() {",
        context: "Hook for managing streaming message state"
      },
      {
        file: "apps/web/src/components/messages/streaming-message.tsx",
        line: 42,
        content: "export function StreamingMessage({",
        context: "Main streaming message component"
      },
      {
        file: "apps/web/src/lib/streaming/sseTransport.ts",
        line: 78,
        content: "onMessage: (event: MessageEvent) => {",
        context: "SSE message handler"
      }
    ]
  }
}
```

### Step 6: AI Suggests Improvements

**Text Response:**

```typescript
{
  type: "text",
  content: `Based on the PR diff and related code, I have the following suggestions:

1. **Error Handling:** Consider adding error boundaries around the streaming message component
2. **Performance:** The component re-renders on every text delta - consider using React.memo
3. **Accessibility:** Add ARIA labels for screen readers
4. **Testing:** Add unit tests for edge cases

Would you like me to create a GitHub issue to track these improvements?`
}
```

### Step 7: User Approves Issue Creation

```
User: "Yes, create an issue for the error handling improvement"
```

### Step 8: AI Creates GitHub Issue

**Tool Call:** `github_create_issue`

**Renders:** `GenericToolCard` in loading state (no specific card registered)

```typescript
{
  type: "tool-call",
  toolName: "github_create_issue",
  toolCallId: "call_125",
  toolArgs: {
    repository: "publicis-sapient/devhub",
    title: "Add error boundaries to streaming message component",
    body: "Based on PR #123 review, we should add error boundaries...",
    labels: ["enhancement", "frontend"]
  }
}
```

### Step 9: HITL Interrupt for Issue Creation

**Interrupt:** HITL approval required

**Renders:** Existing interrupt card

```typescript
{
  type: "interrupt",
  interruptData: {
    approvalId: "approval_123",
    summary: "Create GitHub issue: Add error boundaries to streaming message component",
    risk: "low",
    expiresAt: "2024-01-15T12:00:00Z"
  }
}
```

### Step 10: User Approves

```
User clicks "Approve" button
```

### Step 11: Issue Created Successfully

**Tool Result:** `github_create_issue`

**Renders:** `GenericToolCard` in success state

```typescript
{
  type: "tool-result",
  toolName: "github_create_issue",
  toolCallId: "call_125",
  toolResult: {
    issueNumber: 456,
    url: "https://github.com/publicis-sapient/devhub/issues/456",
    state: "open"
  }
}
```

### Step 12: AI Fetches Created Issue

**Tool Call:** `github_get_issue`

**Renders:** `IssueCard` in loading state

```typescript
{
  type: "tool-call",
  toolName: "github_get_issue",
  toolCallId: "call_126",
  toolArgs: {
    repository: "publicis-sapient/devhub",
    issue_number: 456
  }
}
```

### Step 13: Issue Details

**Tool Result:** `github_get_issue`

**Renders:** `IssueCard` in success state with labels and description

```typescript
{
  type: "tool-result",
  toolName: "github_get_issue",
  toolCallId: "call_126",
  toolResult: {
    issueNumber: 456,
    title: "Add error boundaries to streaming message component",
    author: "devhub-bot",
    repository: "publicis-sapient/devhub",
    state: "open",
    labels: ["enhancement", "frontend"],
    body: "Based on PR #123 review, we should add error boundaries around the streaming message component to handle errors gracefully...",
    url: "https://github.com/publicis-sapient/devhub/issues/456",
    createdAt: "2024-01-15T10:30:00Z",
    updatedAt: "2024-01-15T10:30:00Z"
  }
}
```

### Step 14: Final AI Response

**Text Response:**

```typescript
{
  type: "text",
  content: `✅ Successfully created issue #456 to track the error handling improvement. The issue has been labeled with "enhancement" and "frontend" for easy tracking.

The PR review is complete. Here's a summary:
- Reviewed PR #123 with 245 additions and 18 deletions across 3 files
- Found 3 related code files that may be affected
- Created issue #456 to track the error boundary improvement

Would you like me to review any other PRs or help with something else?`
}
```

## Visual Flow

The demo thread will show:

1. **PRDiffCard** (loading → success) - Shows PR details with expandable diff
2. **CodeSearchResult** (loading → success) - Shows 3 code matches with file paths
3. **Text** - AI suggestions
4. **GenericToolCard** (loading) - Creating GitHub issue
5. **Interrupt Card** - HITL approval request
6. **GenericToolCard** (success) - Issue created
7. **IssueCard** (loading → success) - Shows created issue with labels
8. **Text** - Final summary

## How to Run the Demo

### Option 1: Mock Data (Recommended for Demo)

Create a demo page at `/demo/tool-cards` that renders a static thread with all the message parts above.

```typescript
// apps/web/src/app/demo/tool-cards/page.tsx
import { StreamingMessage } from "@/components/messages/streaming-message";

const demoMessages = [
  // ... message parts from above
];

export default function ToolCardsDemo() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Tool Cards Demo</h1>
      <div className="space-y-4">
        {demoMessages.map((message, index) => (
          <StreamingMessage
            key={index}
            parts={[message]}
            isStreaming={false}
            role="assistant"
          />
        ))}
      </div>
    </div>
  );
}
```

### Option 2: Live Integration

1. Set up GitHub API credentials
2. Create a test PR in a test repository
3. Start a new thread in DevHub
4. Ask: "Review PR #123 in test-repo and suggest improvements"
5. Watch the tool cards render in real-time

## Expected Outcome

The demo should showcase:

✅ **Rich Interactive Cards** - Each tool renders with a custom card instead of raw JSON

✅ **Loading States** - Animated loading indicators while tools are running

✅ **Success States** - Rich data display with expandable sections

✅ **Error Handling** - Clear error messages with retry buttons

✅ **Large Payload Handling** - Diffs and results are collapsed by default

✅ **Accessibility** - All cards are keyboard navigable with proper ARIA labels

✅ **Fallback Mechanism** - Unknown tools render with GenericToolCard

✅ **HITL Integration** - Approval workflow works seamlessly with tool cards

## Screenshots

_(To be added after implementation)_

1. PRDiffCard in loading state
2. PRDiffCard in success state (collapsed)
3. PRDiffCard in success state (expanded)
4. CodeSearchResult with multiple matches
5. IssueCard with labels and description
6. GenericToolCard fallback
7. Full thread view with all cards
