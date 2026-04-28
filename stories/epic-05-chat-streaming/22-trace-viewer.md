# [DEVHUB-022] Agent trace viewer (in-app)

**Labels:** `epic:chat-streaming` `area:web` `type:feature` `priority:P2`
**Estimate:** 5 pts
**Depends on:** DEVHUB-020

## Story
**As a** power user / developer,
**I want** to expand a message and see the full agent trace (router decisions, tool calls, timings),
**so that** I can understand and debug what the system did.

## Acceptance criteria
- [ ] A `<TraceDrawer>` opens from any assistant message and shows a tree of steps.
- [ ] Each step row: agent name, tool (if any), duration, status, expandable args/result.
- [ ] Deep-link to the corresponding LangSmith run if the user has access.
- [ ] Compound components: `<Trace>`, `<Trace.Step>`, `<Trace.Tool>`, `<Trace.Error>`.
- [ ] Performance: traces with up to 200 steps render under 100ms (virtualized).

## Definition of done
- Reviewing a complex multi-agent run is comprehensible without leaving the app.
