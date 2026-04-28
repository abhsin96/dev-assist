# [DEVHUB-020] Streaming message component (AI SDK + custom SSE transport)

**Labels:** `epic:chat-streaming` `area:web` `type:feature` `priority:P0`
**Estimate:** 5 pts
**Depends on:** DEVHUB-010, DEVHUB-019

## Story
**As a** user,
**I want** assistant tokens, tool calls, and intermediate state to stream into the conversation,
**so that** I see progress immediately and can interrupt early.

## Acceptance criteria
- [ ] `lib/streaming/sseTransport.ts` adapts the API's SSE protocol to the Vercel AI SDK `Transport` interface.
- [ ] Messages are rendered as parts: text, tool-call, tool-result, error, interrupt.
- [ ] User can cancel a run mid-stream (`AbortController`); backend marks the run cancelled.
- [ ] Auto-scroll respects user manual scroll: if the user scrolls up, do not yank them back; show a "Jump to latest" pill.
- [ ] Reconnect logic handles transient disconnects using the `from=<seq>` resume capability from DEVHUB-010.
- [ ] Tokens render with subtle motion; final message switches to fully formatted Markdown via `react-markdown` + GFM.

## Definition of done
- Tested on slow-3G throttling: stream remains usable, no stuck UI states.
