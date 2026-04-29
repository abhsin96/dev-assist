# HITL Approval Components

React components for Human-in-the-Loop (HITL) approval workflows in DevHub.

## Overview

These components provide a rich, interactive UI for displaying approval requests inline with chat messages, allowing users to approve, edit, or reject agent actions that require human consent.

## Components

### HITLApprovalCard

Main approval interface component that displays approval requests with risk indicators, action summaries, and interactive buttons.

**Features:**
- Risk level badges (low, medium, high, critical)
- Action summary display
- Collapsible tool arguments viewer
- Three action buttons: Approve, Edit & Approve, Reject
- Status transitions: pending → approved/rejected/expired
- Expiration countdown
- Retry button for expired approvals

**Usage:**
```tsx
import { HITLApprovalCard } from '@/components/approvals';

function MyComponent() {
  const handleApprove = async (approvalId: string, patchedArgs?: Record<string, unknown>) => {
    await api.post(`/runs/${runId}/approvals`, {
      approval_id: approvalId,
      decision: 'approved',
      patched_args: patchedArgs,
    });
  };

  const handleReject = async (approvalId: string) => {
    await api.post(`/runs/${runId}/approvals`, {
      approval_id: approvalId,
      decision: 'rejected',
    });
  };

  return (
    <HITLApprovalCard
      data={{
        approvalId: 'approval-123',
        summary: 'Delete production database',
        risk: 'critical',
        toolName: 'delete_database',
        toolArgs: { database_name: 'users_prod' },
        expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
      }}
      onApprove={handleApprove}
      onReject={handleReject}
      onRetry={() => console.log('Retry')}
    />
  );
}
```

### HITLApprovalEditor

JSON editor for modifying tool arguments before approval.

**Features:**
- JSON textarea with syntax validation
- Real-time validation feedback
- Error display for invalid JSON
- Submit & Approve / Cancel actions

**Usage:**
```tsx
import { HITLApprovalEditor } from '@/components/approvals';

function MyComponent() {
  const [isEditing, setIsEditing] = useState(false);

  const handleSubmit = async (patchedArgs: Record<string, unknown>) => {
    await onApprove(approvalId, patchedArgs);
    setIsEditing(false);
  };

  return (
    <HITLApprovalEditor
      toolName="delete_database"
      initialArgs={{ database_name: 'users_prod' }}
      onSubmit={handleSubmit}
      onCancel={() => setIsEditing(false)}
      isSubmitting={false}
    />
  );
}
```

## Types

### HITLApprovalData
```typescript
interface HITLApprovalData {
  approvalId: string;
  summary: string;
  risk: RiskLevel; // 'low' | 'medium' | 'high' | 'critical'
  toolName: string;
  toolArgs: Record<string, unknown>;
  expiresAt: string; // ISO 8601 timestamp
  status?: ApprovalStatus; // 'pending' | 'approved' | 'rejected' | 'expired'
}
```

### ApprovalStatus
```typescript
type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';
```

### RiskLevel
```typescript
type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
```

## Styling

Components use Tailwind CSS with shadcn/ui design system:

- **Pending**: Amber border and background
- **Approved**: Green border and background
- **Rejected**: Red border and background
- **Expired**: Zinc border and background

## Accessibility

- Semantic HTML structure
- ARIA labels for interactive elements
- Keyboard navigation support
- Focus management
- Screen reader friendly

## Integration with Streaming

These components are designed to work with the SSE streaming infrastructure:

1. Backend emits `interrupt` events via SSE
2. `useStreamingMessage` hook captures interrupt events
3. `useHITLApprovals` hook manages approval state
4. `HITLApprovalCard` renders inline with messages
5. User interacts with approval card
6. API submission to `/runs/{id}/approvals`
7. Run resumes or terminates based on decision

## Dependencies

- `@radix-ui/react-collapsible`: Collapsible UI primitive
- `@radix-ui/react-dialog`: Dialog UI primitive
- `lucide-react`: Icons
- `class-variance-authority`: Variant styling
- `tailwind-merge`: Tailwind class merging

## Testing

See `/tests/e2e/hitl-approval.spec.ts` for comprehensive E2E tests covering:
- Approval card rendering
- Approve flow
- Edit & Approve flow
- Reject flow
- Expiration handling
- Multiple pending approvals
- JSON validation