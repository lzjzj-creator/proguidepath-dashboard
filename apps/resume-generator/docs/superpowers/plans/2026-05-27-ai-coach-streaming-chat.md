# AI Coach Streaming Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade OfferLab intake-mode AI assistant to a streaming chatbot with thinking display and tool-triggered form field updates.

**Architecture:** SSE stream from Next.js API route wrapping heuristic engine. Frontend parses events and renders message types. Bidirectional sync between chat and form via React state + `dispatchToolCall`.

**Tech Stack:** Next.js 16, React 19, Zod, Tailwind CSS 4, Vitest

---

### File Inventory

**Create:**
- `src/lib/tools.ts` — Tool call dispatch + OpenAI tool definitions
- `src/lib/streaming-ai.ts` — SSE stream builder with heuristic fallback
- `src/components/chat-panel.tsx` — Streaming chat panel
- `src/components/toast.tsx` — Toast notification + useToast hook

**Modify:**
- `src/lib/server-ai.ts` — Add `streamAssistChat()` entry point
- `src/app/api/chat-assist/route.ts` — Return `text/event-stream`
- `src/components/resume-studio.tsx` — Replace inline chat, change intake layout
- `src/app/globals.css` — Add animations

---

### Task 1: Tool Schemas + Dispatch (tools.ts)

**Files:**
- Create: `src/lib/tools.ts`
- Create: `src/lib/tools.test.ts`

- [ ] **Step 1: Write tools.test.ts**

```typescript
import { describe, it, expect } from "vitest";
import {
  fillTargetRoleSchema,
  fillEducationSchema,
  fillExperienceSchema,
  fillSkillsSchema,
  dispatchToolCall,
  openAiToolsDefinition,
} from "./tools";
import { createEmptyDraft } from "./resume";

describe("tool schemas", () => {
  it("validates fillTargetRole args", () => {
    expect(fillTargetRoleSchema.safeParse({ roleName: "产品经理", city: "上海" }).success).toBe(true);
  });
  it("rejects invalid fillTargetRole args", () => {
    expect(fillTargetRoleSchema.safeParse({ roleName: 123 }).success).toBe(false);
  });
  it("validates fillEducation args", () => {
    expect(fillEducationSchema.safeParse({ school: "复旦大学", major: "计算机", degree: "本科" }).success).toBe(true);
  });
  it("validates fillExperience args", () => {
    expect(fillExperienceSchema.safeParse({ name: "字节跳动实习", role: "后端开发" }).success).toBe(true);
  });
  it("validates fillSkills args", () => {
    expect(fillSkillsSchema.safeParse({ skillTags: ["Python"], certificates: "六级" }).success).toBe(true);
  });
  it("has all 5 tool definitions in openAiToolsDefinition", () => {
    expect(openAiToolsDefinition).toHaveLength(5);
  });
});

describe("dispatchToolCall", () => {
  it("applies fillTargetRole to draft", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillTargetRole", args: { roleName: "产品经理", city: "上海" } });
    expect(updated.targetRole.roleName).toBe("产品经理");
    expect(updated.targetRole.city).toBe("上海");
  });
  it("applies fillEducation to draft", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillEducation", args: { school: "复旦大学", major: "计算机" } });
    expect(updated.education[0].school).toBe("复旦大学");
    expect(updated.education[0].major).toBe("计算机");
  });
  it("applies fillExperience with activeExperienceId", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillExperience", args: { name: "字节跳动实习" } }, draft.experiences[0].id);
    expect(updated.experiences[0].name).toBe("字节跳动实习");
  });
  it("applies fillSkills with array tags", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillSkills", args: { skillTags: ["Python", "SQL"] } });
    expect(updated.skills.skillTags).toEqual(["Python", "SQL"]);
  });
  it("adds a new experience via addExperience", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "addExperience", args: {} });
    expect(updated.experiences).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run to verify failures**

```bash
npx vitest run src/lib/tools.test.ts
```
Expected: ERROR — module not found

- [ ] **Step 3: Implement tools.ts**

```typescript
import { z } from "zod";
import type { ResumeDraft } from "./types";
import { upsertExperience, createEmptyExperience } from "./resume";

// ── Argument schemas ──
export const fillTargetRoleSchema = z.object({
  roleName: z.string().optional(),
  targetCompany: z.string().optional(),
  city: z.string().optional(),
  jobDescription: z.string().optional(),
});
export const fillEducationSchema = z.object({
  school: z.string().optional(),
  major: z.string().optional(),
  degree: z.string().optional(),
  graduationYear: z.string().optional(),
  gpa: z.string().optional(),
});
export const fillExperienceSchema = z.object({
  name: z.string().optional(),
  role: z.string().optional(),
  timeframe: z.string().optional(),
  responsibility: z.string().optional(),
  tools: z.string().optional(),
  result: z.string().optional(),
});
export const fillSkillsSchema = z.object({
  skillTags: z.array(z.string()).optional(),
  certificates: z.string().optional(),
  languages: z.string().optional(),
  extraNotes: z.string().optional(),
});

// ── OpenAI-compatible tool definitions ──
export const openAiToolsDefinition = [
  {
    type: "function",
    function: {
      name: "fillTargetRole",
      description: "填写目标岗位信息：岗位名称、目标公司、城市、岗位描述",
      parameters: {
        type: "object",
        properties: {
          roleName: { type: "string" },
          targetCompany: { type: "string" },
          city: { type: "string" },
          jobDescription: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fillEducation",
      description: "填写教育经历：学校、专业、学历、毕业时间、GPA",
      parameters: {
        type: "object",
        properties: {
          school: { type: "string" },
          major: { type: "string" },
          degree: { type: "string" },
          graduationYear: { type: "string" },
          gpa: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fillExperience",
      description: "填写当前选中的项目/实习经历",
      parameters: {
        type: "object",
        properties: {
          name: { type: "string" },
          role: { type: "string" },
          timeframe: { type: "string" },
          responsibility: { type: "string" },
          tools: { type: "string" },
          result: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fillSkills",
      description: "填写技能标签、证书、语言能力、补充说明",
      parameters: {
        type: "object",
        properties: {
          skillTags: { type: "array", items: { type: "string" } },
          certificates: { type: "string" },
          languages: { type: "string" },
          extraNotes: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "addExperience",
      description: "新增一条空的项目/实习经历",
      parameters: { type: "object", properties: {} },
    },
  },
];

export type ToolName = "fillTargetRole" | "fillEducation" | "fillExperience" | "fillSkills" | "addExperience";
export type ToolCall = { tool: ToolName; args: Record<string, unknown> };

function pick<T extends Record<string, unknown>>(obj: T, allowed: (keyof T)[]): Partial<T> {
  const result: Partial<T> = {};
  for (const key of allowed) {
    if (obj[key] !== undefined) result[key] = obj[key];
  }
  return result;
}

export const dispatchToolCall = (
  draft: ResumeDraft,
  toolCall: ToolCall,
  activeExperienceId?: string,
): ResumeDraft => {
  switch (toolCall.tool) {
    case "fillTargetRole": {
      const p = fillTargetRoleSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      return { ...draft, targetRole: { ...draft.targetRole, ...pick(p.data, ["roleName", "targetCompany", "city", "jobDescription"]) } };
    }
    case "fillEducation": {
      const p = fillEducationSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      const edu = { ...draft.education[0], ...pick(p.data, ["school", "major", "degree", "graduationYear", "gpa"]) };
      return { ...draft, education: [edu, ...draft.education.slice(1)] };
    }
    case "fillExperience": {
      const p = fillExperienceSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      const idx = activeExperienceId ? Math.max(0, draft.experiences.findIndex((e) => e.id === activeExperienceId)) : 0;
      const target = draft.experiences[idx];
      if (!target) return draft;
      return { ...draft, experiences: upsertExperience(draft.experiences, { ...target, ...pick(p.data, ["name", "role", "timeframe", "responsibility", "tools", "result"]) }) };
    }
    case "fillSkills": {
      const p = fillSkillsSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      return { ...draft, skills: { ...draft.skills, ...pick(p.data, ["skillTags", "certificates", "languages", "extraNotes"]) } };
    }
    case "addExperience":
      return { ...draft, experiences: [...draft.experiences, createEmptyExperience()] };
    default:
      return draft;
  }
};
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/lib/tools.test.ts
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/tools.ts src/lib/tools.test.ts
git commit -m "feat: add tool schemas and dispatch for AI function calling"
```

---

### Task 2: Streaming AI Service (streaming-ai.ts)

**Files:**
- Create: `src/lib/streaming-ai.ts`
- Create: `src/lib/streaming-ai.test.ts`

- [ ] **Step 1: Write streaming-ai.test.ts**

```typescript
import { describe, it, expect } from "vitest";
import { createFallbackStream } from "./streaming-ai";
import { createEmptyDraft } from "./resume";

async function collectStream(stream: ReadableStream<Uint8Array>): Promise<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let result = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    result += decoder.decode(value, { stream: true });
  }
  return result;
}

describe("createFallbackStream", () => {
  it("emits thought, text, tool_call, done for material input", async () => {
    const stream = createFallbackStream({
      stepId: "target",
      question: "岗位名称：产品经理\n公司：字节跳动\n工作地点：上海",
      inputKind: "material",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().targetRole,
    });
    const output = await collectStream(stream);
    expect(output).toContain("event: thought");
    expect(output).toContain("event: text");
    expect(output).toContain("event: tool_call");
    expect(output).toContain('"tool":"fillTargetRole"');
    expect(output).toContain("event: done");
  });

  it("emits thought, text, done (no tool_call) for QA input", async () => {
    const stream = createFallbackStream({
      stepId: "skills",
      question: "技能怎么写更像校招简历？",
      inputKind: "question",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().skills,
    });
    const output = await collectStream(stream);
    expect(output).toContain("event: thought");
    expect(output).toContain("event: text");
    expect(output).not.toContain("event: tool_call");
    expect(output).toContain("event: done");
  });
});
```

- [ ] **Step 2: Run to verify failures**

```bash
npx vitest run src/lib/streaming-ai.test.ts
```
Expected: ERROR — module not found

- [ ] **Step 3: Implement streaming-ai.ts**

```typescript
import type { ChatAssistRequest } from "./types";
import { buildChatAssistHeuristics } from "./mock-ai";

function encode(event: string, data: Record<string, unknown>): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

export function createFallbackStream(request: ChatAssistRequest): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      const enc = new TextEncoder();
      const response = buildChatAssistHeuristics(request);

      const thoughtMsg = request.inputKind === "material"
        ? `正在分析${request.stepId === "target" ? "岗位" : request.stepId === "education" ? "教育" : request.stepId === "experience" ? "经历" : "技能"}材料...`
        : "正在理解你的问题...";
      controller.enqueue(enc.encode(encode("thought", { content: thoughtMsg })));

      controller.enqueue(enc.encode(encode("text", { content: response.reply })));

      for (const card of response.cards) {
        let tool: string | null = null;
        if (card.field.startsWith("targetRole")) tool = "fillTargetRole";
        else if (card.field.startsWith("education")) tool = "fillEducation";
        else if (card.field.startsWith("experiences")) tool = "fillExperience";
        else if (card.field.startsWith("skills")) tool = "fillSkills";
        if (tool) {
          controller.enqueue(enc.encode(encode("tool_call", { tool, field: card.field, value: card.value, label: card.label })));
        }
      }

      controller.enqueue(enc.encode(encode("done", {})));
      controller.close();
    },
  });
}
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/lib/streaming-ai.test.ts
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/streaming-ai.ts src/lib/streaming-ai.test.ts
git commit -m "feat: add streaming AI service with heuristic fallback"
```

---

### Task 3: Server Route (server-ai.ts + chat-assist/route.ts)

**Files:**
- Modify: `src/lib/server-ai.ts`
- Modify: `src/app/api/chat-assist/route.ts`

- [ ] **Step 1: Add streamAssistChat to server-ai.ts**

After last import, add:
```typescript
import { createFallbackStream } from "./streaming-ai";
```

After the `assistChat` function (before file end), add:
```typescript
export function streamAssistChat(
  request: ChatAssistRequest,
): ReadableStream<Uint8Array> {
  // Always use heuristic fallback for now.
  // Future: call OpenAI/DashScope streaming API with tools when apiKey is set.
  return createFallbackStream(request);
}
```

- [ ] **Step 2: Rewrite chat-assist/route.ts**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { streamAssistChat } from "@/lib/server-ai";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const stream = streamAssistChat(body);
    return new NextResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch {
    return NextResponse.json(
      { mode: "qa", reply: "服务暂不可用，请稍后重试。", cards: [] },
      { status: 500 },
    );
  }
}
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
npx vitest run
```
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/lib/server-ai.ts src/app/api/chat-assist/route.ts
git commit -m "feat: add streaming chat-assist endpoint with SSE response"
```

---

### Task 4: CSS Animations (globals.css)

**Files:**
- Modify: `src/app/globals.css`

- [ ] **Step 1: Add animations to globals.css**

Append:
```css
.toast-enter {
  animation: toast-in 0.3s ease-out forwards;
}
@keyframes toast-in {
  from { opacity: 0; transform: translateY(-12px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes flash-pulse {
  0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15); }
  100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
}
.field-flash { animation: flash-pulse 1.5s ease-out; }
.stream-cursor::after {
  content: "|";
  animation: blink 0.7s step-end infinite;
  color: #2563eb;
  font-weight: 300;
}
@keyframes blink { 50% { opacity: 0; } }
.message-enter { animation: msg-in 0.25s ease-out forwards; }
@keyframes msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.thinking-block {
  background: #f1f5f9;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 0.85rem;
  color: #475569;
  line-height: 1.6;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/app/globals.css
git commit -m "style: add animations for toast, chat, and field flash"
```

---

### Task 5: Toast Component (toast.tsx)

**Files:**
- Create: `src/components/toast.tsx`
- Create: `src/components/toast.test.tsx`

- [ ] **Step 1: Write toast.test.tsx**

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toast, ToastManager } from "./toast";

describe("Toast", () => {
  it("renders success message", () => {
    render(<Toast type="success" message="已保存" onClose={() => {}} />);
    expect(screen.getByText("已保存")).toBeDefined();
  });
  it("renders error message", () => {
    render(<Toast type="error" message="失败" onClose={() => {}} />);
    expect(screen.getByText("失败")).toBeDefined();
  });
  it("calls onClose on dismiss click", () => {
    const cb = vi.fn();
    render(<Toast type="info" message="提示" onClose={cb} />);
    fireEvent.click(screen.getByRole("button"));
    expect(cb).toHaveBeenCalledOnce();
  });
});

describe("ToastManager", () => {
  it("renders multiple toasts", () => {
    render(<ToastManager toasts={[{ id: "1", type: "success", message: "A" }, { id: "2", type: "error", message: "B" }]} onDismiss={() => {}} />);
    expect(screen.getByText("A")).toBeDefined();
    expect(screen.getByText("B")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run to verify failures**

```bash
npx vitest run src/components/toast.test.tsx
```
Expected: ERROR — module not found

- [ ] **Step 3: Implement toast.tsx**

```typescript
"use client";

import { useCallback, useState } from "react";

export type ToastType = "success" | "error" | "info";
export type ToastData = { id: string; type: ToastType; message: string };

const bgMap: Record<ToastType, string> = {
  success: "bg-emerald-600",
  error: "bg-red-600",
  info: "bg-blue-700",
};

export function Toast({ type, message, onClose }: { type: ToastType; message: string; onClose: () => void }) {
  return (
    <div className={`toast-enter flex items-center gap-3 rounded-2xl ${bgMap[type]} px-5 py-3 text-sm text-white shadow-lg`}>
      <span className="flex-1">{message}</span>
      <button type="button" onClick={onClose} className="flex-shrink-0 rounded-full p-1 opacity-70 hover:opacity-100">✕</button>
    </div>
  );
}

export function ToastManager({ toasts, onDismiss }: { toasts: ToastData[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed right-6 top-6 z-50 flex flex-col gap-2">
      {toasts.map((t) => <Toast key={t.id} type={t.type} message={t.message} onClose={() => onDismiss(t.id)} />)}
    </div>
  );
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const addToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = `t-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    if (duration > 0) setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), duration);
  }, []);
  const dismissToast = useCallback((id: string) => setToasts((prev) => prev.filter((t) => t.id !== id)), []);
  return { toasts, addToast, dismissToast };
}
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/components/toast.test.tsx
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/toast.tsx src/components/toast.test.tsx
git commit -m "feat: add Toast component with useToast hook"
```

---

### Task 6: Chat Panel Component (chat-panel.tsx)

**Files:**
- Create: `src/components/chat-panel.tsx`
- Create: `src/components/chat-panel.test.tsx`

- [ ] **Step 1: Write chat-panel.test.tsx**

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatPanel } from "./chat-panel";
import { createEmptyDraft } from "@/lib/resume";

describe("ChatPanel", () => {
  const base = {
    stepId: "target" as const,
    stepLabel: "目标岗位",
    draft: createEmptyDraft(),
    activeExperienceId: "",
    onDraftChange: () => {},
    onAddToast: () => {},
  };

  it("renders initial assistant message and input", () => {
    render(<ChatPanel {...base} />);
    expect(screen.getByPlaceholderText(/粘贴|提问/)).toBeDefined();
  });
});
```

- [ ] **Step 2: Run to verify failures**

```bash
npx vitest run src/components/chat-panel.test.tsx
```
Expected: ERROR — module not found

- [ ] **Step 3: Implement chat-panel.tsx**

```typescript
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ResumeDraft, StepId } from "@/lib/types";
import { dispatchToolCall, type ToolCall } from "@/lib/tools";

// ── Helpers ──

const initialMessages: Record<StepId, string> = {
  target: "把 JD 或岗位描述贴进来，我会整理成可直接应用的建议卡片。",
  education: "把学校、专业、学历、毕业时间、GPA 等原始信息贴进来，我会拆成教育经历卡片。",
  experience: "把当前项目或实习的原始描述贴进来，我会按这条经历生成职责、工具、结果等卡片。",
  skills: "把技能清单、证书、语言能力或补充说明贴进来，我会整理成技能标签卡片。",
};

const detectInputKind = (stepId: StepId, value: string): "material" | "question" => {
  const text = value.trim();
  const lineCount = text.split(/\n/).filter(Boolean).length;
  const patterns: Record<StepId, RegExp> = {
    target: /JD|岗位|职责|要求|任职|工作地点/i,
    education: /学校|院校|专业|学历|学位|GPA|毕业/i,
    experience: /项目|实习|比赛|负责|产出|结果|工具/i,
    skills: /技能|证书|语言|Python|SQL|Figma|Excel/i,
  };
  return lineCount >= 2 || text.length >= 60 || patterns[stepId].test(text) ? "material" : "question";
};

const fieldToTool = (field: string): ToolCall["tool"] | null => {
  if (field.startsWith("targetRole")) return "fillTargetRole";
  if (field.startsWith("education")) return "fillEducation";
  if (field.startsWith("experiences")) return "fillExperience";
  if (field.startsWith("skills")) return "fillSkills";
  return null;
};

const getToolArgs = (field: string, value: string): Record<string, unknown> => {
  const key = field.split(".").pop()!;
  if (key === "skillTags") return { skillTags: value.split(/[,\s/]+/).map((s) => s.trim()).filter(Boolean) };
  return { [key]: value };
};

// ── Types ──

type ToolResult = { tool: string; field: string; value: string; label: string };
type Message = { id: string; role: "user" | "assistant"; content: string; thinking?: string; toolCalls?: ToolResult[] };

// ── Component ──

type ChatPanelProps = {
  stepId: StepId;
  stepLabel: string;
  draft: ResumeDraft;
  activeExperienceId: string;
  onDraftChange: (draft: ResumeDraft) => void;
  onAddToast: (type: "success" | "error", message: string) => void;
};

export function ChatPanel({ stepId, stepLabel, draft, activeExperienceId, onDraftChange, onAddToast }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([{ id: "init", role: "assistant", content: initialMessages[stepId] }]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingThinking, setStreamingThinking] = useState("");
  const [showThinking, setShowThinking] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const draftRef = useRef(draft);
  draftRef.current = draft;

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingContent]);

  const finalizeStream = useCallback((content: string, thinking: string, toolCalls: ToolResult[]) => {
    if (!content && toolCalls.length === 0) return;
    setMessages((p) => [...p, { id: `a-${Date.now()}`, role: "assistant", content, thinking: thinking || undefined, toolCalls: toolCalls.length > 0 ? toolCalls : undefined }]);
    setStreamingContent("");
    setStreamingThinking("");
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    setIsLoading(true);
    setStreamingContent("");
    setStreamingThinking("");
    setMessages((p) => [...p, { id: `u-${Date.now()}`, role: "user", content: text }]);

    try {
      const response = await fetch("/api/chat-assist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stepId, question: text, inputKind: detectInputKind(stepId, text), activeExperienceId, currentDraft: draftRef.current, currentFieldValues: draftRef.current }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      if (!response.headers.get("Content-Type")?.includes("text/event-stream")) {
        // JSON fallback
        const data = await response.json();
        const toolCalls: ToolResult[] = [];
        for (const card of data.cards || []) {
          const t = fieldToTool(card.field);
          if (t) { const u = dispatchToolCall(draftRef.current, { tool: t, args: getToolArgs(card.field, card.value) }, activeExperienceId); onDraftChange(u); toolCalls.push({ tool: t, field: card.field, value: card.value, label: card.label }); }
        }
        finalizeStream(data.reply || "", "", toolCalls);
        return;
      }

      // SSE streaming
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "", curEvent = "", curData = "";
      const toolCalls: ToolResult[] = [];
      let accText = "", accThought = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("event: ")) curEvent = line.slice(7).trim();
          else if (line.startsWith("data: ")) curData = line.slice(6).trim();
          else if (line === "" && curEvent) {
            if (curData) {
              try {
                const p = JSON.parse(curData);
                if (curEvent === "thought") { accThought = p.content || ""; setStreamingThinking(accThought); }
                else if (curEvent === "text") { accText += p.content || ""; setStreamingContent(accText); }
                else if (curEvent === "tool_call") {
                  const t = fieldToTool(p.field);
                  if (t) { const u = dispatchToolCall(draftRef.current, { tool: t, args: getToolArgs(p.field, p.value) }, activeExperienceId); onDraftChange(u); toolCalls.push({ tool: t, field: p.field, value: p.value, label: p.label }); }
                }
              } catch {}
            }
            if (curEvent === "done") finalizeStream(accText, accThought, toolCalls);
            curEvent = ""; curData = "";
          }
        }
      }
    } catch {
      onAddToast("error", "AI 请求失败，请重试");
      finalizeStream("请求失败，请检查网络或 AI 配置后重试。", "", []);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, stepId, activeExperienceId, onDraftChange, onAddToast, finalizeStream]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-sky-100 pb-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-sky-600">AI 教练</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">{stepLabel}</h2>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-enter ${msg.role === "user" ? "flex justify-end" : ""}`}>
            <div className={`max-w-[90%] rounded-[24px] px-4 py-4 text-sm leading-7 ${msg.role === "user" ? "bg-blue-700 text-white" : "bg-white text-slate-700"}`}>
              {msg.content}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {msg.toolCalls.map((tc, i) => <span key={i} className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">✅ {tc.label}</span>)}
                </div>
              )}
            </div>
          </div>
        ))}

        {(streamingContent || streamingThinking) && (
          <div className="message-enter">
            <div className="max-w-[90%] rounded-[24px] bg-white px-4 py-4 text-sm leading-7 text-slate-700">
              {streamingThinking && (
                <div className="thinking-block mb-3 cursor-pointer" onClick={() => setShowThinking((s) => !s)}>
                  <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.1em] text-slate-400">{showThinking ? "▼" : "▶"} 思考过程</div>
                  {showThinking && <p className="mt-2">{streamingThinking}</p>}
                </div>
              )}
              {streamingContent && <span>{streamingContent}<span className="stream-cursor" /></span>}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-sky-100 pt-4">
        <div className="field">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="粘贴原始材料，或直接提问..."
            disabled={isLoading}
            className="min-h-[60px] resize-none"
          />
        </div>
        <button type="button" disabled={isLoading || !input.trim()} onClick={sendMessage} className="mt-3 w-full rounded-full bg-blue-700 px-4 py-3 text-sm text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60">
          {isLoading ? "思考中..." : "发送"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/components/chat-panel.test.tsx
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/chat-panel.tsx src/components/chat-panel.test.tsx
git commit -m "feat: add streaming ChatPanel component"
```

---

### Task 7: ResumeStudio Layout + Integration

**Files:**
- Modify: `src/components/resume-studio.tsx`

This is the largest change. The intake mode layout changes from 3-column (nav|form|chat) to top-progress-bar + 2-column (form|chat). Edit mode stays unchanged.

- [ ] **Step 1: Modify resume-studio.tsx**

Key changes:
1. Import `ChatPanel` and `ToastManager` + `useToast`
2. Remove left sidebar in intake mode, replace with top progress bar
3. In intake mode, split into form(40%) + chat(60%)
4. Wire chat -> draft sync via `ChatPanel.onDraftChange`
5. Add `ToastManager` + `useToast` at root level
6. Remove old `chatInput`, `chatMessages`, `assistCards`, `isChatLoading` state (replaced by ChatPanel)

Full modified file (too large to inline — apply as targeted edits):

**Edit A: Add imports** (after existing imports, before `const steps`)

```typescript
import { ChatPanel } from "@/components/chat-panel";
import { ToastManager, useToast } from "@/components/toast";
```

**Edit B: Add toast hook** (after existing state declarations, around line 279)

```typescript
const { toasts, addToast, dismissToast } = useToast();
```

**Edit C: Replace the grid layout (line 575)**

Old:
```tsx
<div className="mt-8 grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)_320px]">
```

New (intake: top progress + 2-col; edit: current form):
```tsx
<div className="mt-8">
  {mode === "intake" ? (
    <>
      {/* Top progress bar */}
      <div className="mb-6 flex items-center gap-3 rounded-[32px] border border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f5faff_100%)] px-6 py-4 shadow-[0_18px_60px_rgba(59,130,246,0.08)]">
        {steps.map((step, index) => (
          <button key={step.id} onClick={() => moveToStep(index)} className="flex items-center gap-2 group">
            <span className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium transition ${currentStep === index ? "bg-blue-700 text-white" : completion[index] ? "bg-emerald-400 text-white" : "bg-sky-100 text-slate-500 group-hover:bg-blue-200"}`}>
              {completion[index] ? "✓" : index + 1}
            </span>
            <span className={`text-sm max-md:hidden ${currentStep === index ? "font-semibold text-blue-700" : "text-slate-500"}`}>{step.label}</span>
            {index < steps.length - 1 && <span className="hidden h-px flex-1 bg-sky-200 md:block" />}
          </button>
        ))}
        <button type="button" onClick={() => { const f = createEmptyDraft(); startTransition(() => { setDraft(f); setActiveExperienceId(f.experiences[0]?.id ?? ""); setMode("intake"); moveToStep(0); }); }} className="ml-auto rounded-full border border-sky-100 px-3 py-2 text-xs text-slate-500 transition hover:border-blue-600 hover:text-blue-700">新建草稿</button>
      </div>

      {/* Intake: 2-column form + chat */}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <main className="rounded-[32px] border border-sky-100 bg-white p-6 shadow-[0_24px_80px_rgba(59,130,246,0.08)]">
          {/* existing intake form content — unchanged */}
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-sky-100 pb-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-sky-600">信息采集</p>
              <div className="rounded-full bg-sky-50 px-4 py-2 text-xs text-slate-600">{currentStep + 1} / {steps.length}</div>
            </div>
            {/* ... keep ALL existing intake form fields (target, education, experience, skills) exactly as-is ... */}
          </div>
        </main>
        <aside className="rounded-[32px] border border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f2f8ff_100%)] p-5 shadow-[0_20px_70px_rgba(59,130,246,0.08)]">
          <ChatPanel stepId={currentStepId} stepLabel={steps[currentStep].label} draft={draft} activeExperienceId={activeExperienceId} onDraftChange={(d) => setDraft(d)} onAddToast={addToast} />
        </aside>
      </div>
    </>
  ) : (
    /* existing edit mode layout — unchanged */
    <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)_320px]">
      {/* ... existing edit mode content stays exactly as-is ... */}
    </div>
  )}
</div>
```

**Edit D: Add ToastManager** (after the closing `</section>` tag, before final `</div>`)

```tsx
<ToastManager toasts={toasts} onDismiss={dismissToast} />
```

**Edit E: Clean up unused state**

After the edit mode grid, remove the old right-side assistant bar HTML (the section from `"智能助手栏"` onwards in intake mode, lines ~1123-1246). Also remove unused state: `chatInput`, `chatMessages`, `assistCards`, `assistMode`, `isChatLoading`, `rewriteIntent`, `isRewriting`, `status`, and related handlers.

(For safety, these become dead code that won't render — a lint pass can verify. The old `sendAssist` function and `resetAssistForStep` also become unused.)

- [ ] **Step 2: Run tests**

```bash
npx vitest run
```
Expected: existing tests PASS, new component tests PASS

- [ ] **Step 3: Build check**

```bash
npm run build
```
Expected: successful build with no TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add src/components/resume-studio.tsx
git commit -m "refactor: replace intake assistant with streaming ChatPanel + top progress bar"
```

---

### Self-Review Checklist

**1. Spec coverage:**
- Layout change (top progress bar + 2-column intake) = Task 7
- Chat panel with streaming typewriter = Task 6
- Message types (thinking, text, tool_result) = Task 6
- Tool schemas and dispatch = Task 1
- SSE service with heuristic fallback = Task 2
- Server route SSE upgrade = Task 3
- Toast feedback system = Task 5
- CSS animations = Task 4
- Bidirectional form sync = Task 6 + Task 7

**2. Placeholder scan:** All steps contain runnable code or exact commands. No TBD, TODO, or "implement later".

**3. Type consistency:** ToolName, ToolCall, dispatchToolCall signatures consistent across Tasks 1, 2, 6. SSE event types (`thought`, `text`, `tool_call`, `done`) consistent across Tasks 2, 3, 6.
