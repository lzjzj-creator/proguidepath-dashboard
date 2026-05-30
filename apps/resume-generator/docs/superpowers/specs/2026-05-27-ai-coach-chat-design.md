# OfferLab AI Coach: Streaming Chat + Tool Calling

## Goal
Upgrade the intake-mode AI assistant from a stateless material extractor to an intelligent coaching chatbot with real streaming, thinking display, and tool-calling that directly controls form fields.

## Scope
- Intake mode only (steps: target → education → experience → skills)
- Edit mode (ResumePreview + PDF export) is untouched

## Layout Change
- Remove left sidebar step navigation → top progress bar with step labels + click-to-switch
- Right chat panel expands to ~60% width
- Center form shrinks to ~40% as real-time preview + manual edit anchor

## Chat Panel (new component: `chat-panel.tsx`)
- Full conversation UI with streaming typewriter effect
- Message types:
  - `thinking` — gray collapsible block showing AI reasoning
  - `text` — streaming text tokens, user/AI bubbles
  - `tool_result` — green pill "✅ 已回填 学校 → 复旦大学"
  - `quick_reply` — inline choice buttons rendered by AI
  - `gap_card` — missing-field reminder card
- Auto-scroll, fade-in entrance animation
- Independent of the step form; syncs via draft state

## Server: Streaming + Tools Architecture

### New files
- `src/lib/tools.ts` — Zod schemas for tool definitions (fillTargetRole, fillEducation, fillExperience, fillSkills, addExperience, suggestNextStep)
- `src/lib/streaming-ai.ts` — SSE stream builder, tool dispatcher, fallback logic

### Modified files
- `src/lib/server-ai.ts` — add streaming entry point alongside existing JSON helpers
- `src/app/api/chat-assist/route.ts` — return `text/event-stream` instead of JSON
- `src/components/resume-studio.tsx` — replace inline chat UI with ChatPanel component
- `src/lib/resume.ts` — minor additions for tool-based field updates

### Streaming Protocol (SSE)
```
event: thought
data: {"content":"..."}

event: text
data: {"content":"..."}

event: tool_call
data: {"tool":"fillTargetRole","args":{...},"status":"ok"}

event: done
data: {}
```

### Tool Definitions
| Tool | Updates | Trigger |
|------|---------|---------|
| `fillTargetRole` | roleName, targetCompany, city, jobDescription | AI extracts from JD or conversation |
| `fillEducation` | school, major, degree, graduationYear, gpa | Same |
| `fillExperience` | name, role, timeframe, responsibility, tools, result | AI parses user's raw experience text |
| `fillSkills` | skillTags, certificates, languages, extraNotes | Same |
| `addExperience` | Creates new empty experience entry | AI detects multiple experiences |
| `suggestNextStep` | Returns missing-field hints | Auto-triggered each turn |

### Fallback
- No API key → wrap existing `buildChatAssistHeuristics()` in a non-streaming response
- Stream interrupted → client shows "连接中断" + retry button
- Tool execution error → show red warning label in chat, user can copy manually

## Bidirectional Form Sync
- AI→Form: tool_call events update draft state → field flash animation (1.5s blue pulse)
- Form→AI: manual edits silently feed into next AI turn context
- Step switch: chat resets to step-specific initial message + loads existing field values

## Feedback System
- Remove the single status text line at bottom-right
- Add: inline chat feedback (tool result pills, gap cards) + short-lived Toast component for success/error

## Migration Strategy
- Add new files, don't delete old ones
- Old mock-ai.ts stays as pure heuristic fallback (unchanged)
- Rollout: merge and test streaming flow first; old path still works if env key is missing
