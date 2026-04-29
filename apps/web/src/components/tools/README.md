# Tool Card Components

This directory contains rich, interactive card components for rendering tool calls and results with generative UI.

## Overview

The tool renderer system provides a registry-based approach to map tool names to React components. When a tool is called during streaming, the system automatically selects the appropriate card component to render the tool's loading state, success state, or error state.

## Architecture

### Tool Renderer Registry

The `toolRendererRegistry` is a singleton that maintains a mapping of tool names to their corresponding React components.

```typescript
import { toolRendererRegistry } from "@/lib/tools";

// Register a tool renderer
toolRendererRegistry.register("github_get_pr_diff", PRDiffCard);

// Get a renderer for a tool
const ToolRenderer = toolRendererRegistry.get("github_get_pr_diff");
```

### Tool Renderer Props

All tool card components receive the following props:

```typescript
interface ToolRendererProps {
  toolName: string;        // Name of the tool
  toolCallId: string;      // Unique ID for this tool call
  args: Record<string, unknown>;  // Tool arguments
  result?: unknown;        // Tool result (if available)
  error?: string;          // Error message (if failed)
  status: "loading" | "success" | "error";  // Current status
  onRetry?: () => void;    // Retry callback (optional)
}
```

## Available Components

### PRDiffCard

Renders GitHub pull request diffs with:
- PR title, number, and repository
- Author information
- Addition/deletion statistics
- Expandable diff view
- Link to GitHub PR

**Registered for tools:**
- `github_get_pr_diff`
- `github_fetch_pr`
- `get_pr_diff`

### IssueCard

Renders GitHub issues with:
- Issue title, number, and repository
- Author and state (open/closed)
- Labels
- Expandable issue description
- Link to GitHub issue

**Registered for tools:**
- `github_get_issue`
- `github_fetch_issue`
- `get_issue`

### CodeSearchResult

Renders code search results with:
- Search query and repository
- Total match count
- Expandable list of matches with file paths and line numbers
- Code snippets with context

**Registered for tools:**
- `code_search`
- `search_code`
- `grep_code`

### DocDiffCard

Renders documentation diffs with:
- File name and version information
- Addition/deletion statistics
- Expandable diff view
- Link to documentation (if available)

**Registered for tools:**
- `doc_diff`
- `get_doc_diff`
- `compare_docs`

### GenericToolCard

Fallback renderer for tools without a specific card. Displays:
- Tool name and status
- Expandable arguments (JSON)
- Expandable result (JSON)
- Error message with retry button

**Used for:** Any tool not registered in the registry

## States

Each card component handles three states:

### Loading State
- Displays loading indicator
- Shows tool name and "Calling..." message
- Animated pulse effect on icon
- Blue color scheme

### Success State
- Displays tool result in rich, interactive format
- Expandable sections for large payloads
- Green/themed color scheme
- Links to external resources (GitHub, docs, etc.)

### Error State
- Displays error message
- Retry button (if `onRetry` callback provided)
- Red color scheme
- Clear error messaging

## Accessibility Features

All card components follow accessibility best practices:

- **Keyboard Navigation:** All interactive elements (expand/collapse buttons, links) are keyboard accessible
- **ARIA Labels:** Proper ARIA labels and descriptions for screen readers
- **Semantic HTML:** Proper heading hierarchy and semantic elements
- **Focus Management:** Clear focus indicators and logical tab order
- **Expandable Sections:** Proper `aria-expanded` and `aria-controls` attributes

## Large Payload Handling

Cards automatically detect large payloads and collapse them by default:

- **PR Diffs:** Collapsed if diff > 1000 characters
- **Issue Descriptions:** Collapsed if body > 1000 characters
- **Code Search Results:** Collapsed if > 5 matches
- **Doc Diffs:** Collapsed if diff > 1000 characters
- **Generic Tool Results:** Collapsed if JSON > 500 characters

Users can expand/collapse these sections with a single click.

## Adding New Tool Cards

### 1. Create the Component

Create a new file in this directory:

```typescript
// my-tool-card.tsx
import { ToolRendererProps } from "@/lib/tools/tool-renderer-registry";
import { Card } from "@/components/ui/card";

export function MyToolCard({
  args,
  result,
  error,
  status,
  onRetry,
}: ToolRendererProps) {
  // Parse result data
  const data = result as MyToolData | undefined;

  return (
    <Card>
      {/* Implement loading, success, and error states */}
    </Card>
  );
}
```

### 2. Export the Component

Add to `index.ts`:

```typescript
export { MyToolCard } from "./my-tool-card";
```

### 3. Register the Tool

Add to `@/lib/tools/register-tools.ts`:

```typescript
import { MyToolCard } from "@/components/tools";

export function registerToolRenderers(): void {
  // ... existing registrations
  toolRendererRegistry.register("my_tool_name", MyToolCard);
}
```

## Best Practices

1. **Always handle all three states:** loading, success, and error
2. **Provide retry functionality** for error states when applicable
3. **Collapse large payloads** by default to improve performance
4. **Use semantic HTML** and proper ARIA attributes for accessibility
5. **Include links** to external resources when available
6. **Show meaningful metadata** (author, timestamps, stats, etc.)
7. **Use consistent color schemes** for different states
8. **Test keyboard navigation** and screen reader compatibility
9. **Handle edge cases** (missing data, null values, etc.)
10. **Keep cards visually consistent** with the design system

## Integration

The tool cards are automatically integrated into the `StreamingMessage` component. When a tool call or result is received during streaming, the system:

1. Checks if a custom renderer exists in the registry
2. If found, renders the custom card component
3. If not found, falls back to `GenericToolCard`
4. Passes the appropriate props based on the tool's status

No additional integration code is needed when adding new tool cards - just register them in the registry.
