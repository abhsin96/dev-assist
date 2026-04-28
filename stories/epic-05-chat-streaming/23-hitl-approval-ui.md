# [DEVHUB-023] HITL approval UI

**Labels:** `epic:chat-streaming` `area:web` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-015, DEVHUB-020

## Story
**As a** user,
**I want** an approval card to appear inline when an agent needs my consent,
**so that** I can approve, edit, or reject without losing context.

## Acceptance criteria
- [ ] On `event: interrupt`, a `<HITLApprovalCard>` renders inline with: action summary, risk badge, full args (collapsible), Approve / Edit & Approve / Reject buttons.
- [ ] "Edit & Approve" lets the user mutate the args (typed form, validated against the tool schema) before submitting.
- [ ] Submitting calls `POST /runs/{id}/approvals` and the run resumes; the card transitions to a final state showing the outcome.
- [ ] If the approval expires, the card shows a clear "Expired" state with a button to retry the action via a new run.
- [ ] Multiple pending approvals in the same thread are handled (FIFO order).

## Definition of done
- E2E Playwright test approves a fake destructive action; rejects another; both flows correct.
