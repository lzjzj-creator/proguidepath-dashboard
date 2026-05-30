# AI 助手增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 OfferLab AI 助手改造为功能完整、可配置、流式输出的真正 AI 助手

**Architecture:** 
- 前端：ReadableStream 解析 SSE + localStorage 持久化对话 + 可折叠 AI 配置面板
- 后端：server-ai 按 API Key 有无分支（真 AI stream / mock SSE），所有端点为统一 SSE 格式
- 对话记忆按 stepId 独立存储，切换步骤自动加载

**Tech Stack:** Next.js 16, OpenAI SDK (DashScope), SSE, localStorage

---

## 文件结构

| 文件 | 改动类型 | 职责 |
|------|----------|------|
| `src/lib/types.ts` | 修改 | 新增 AI 配置、ChatMessage、流式 event 类型 |
| `src/lib/streaming-ai.ts` | 重写 | 通用 SSE 工具函数 + 真 AI 流式调用 |
| `src/lib/server-ai.ts` | 修改 | streamAssistChat 接入 AI 流式调用 |
| `src/lib/mock-ai.ts` | 修改 | 保持原有启发式规则 |
| `src/lib/storage.ts` | 修改 | 新增对话历史、AI 配置的读写 |
| `src/components/ai-config.tsx` | 创建 | AI 配置面板组件 |
| `src/components/chat-assist.tsx` | 创建 | 对话区 + 流式渲染组件（从 resume-studio 拆分） |
| `src/components/resume-studio.tsx` | 修改 | 集成新组件，补全改写，简化自身 |
| `src/app/api/chat-assist/route.ts` | 修改 | 传递对话历史参数 |

---

### Task 1: 新增类型定义

**Files:**
- Modify: `src/lib/types.ts` (末尾追加)

- [ ] **Step 1: 在 types.ts 末尾新增 AI 配置和对话类型**

```typescript
// === AI 助手增强类型 ===

export type AiConfig = {
  apiKey: string;
  baseUrl: string;
  model: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  cards?: ChatAssistCard[];
  ts: number;
};

export type ChatHistory = Record<StepId, ChatMessage[]>;

export type SseEvent =
  | { event: "thought"; data: { content: string } }
  | { event: "text"; data: { content: string } }
  | { event: "tool_call"; data: { tool: string; field: string; value: string; label: string } }
  | { event: "done"; data: Record<string, never> };
```

- [ ] **Step 2: 运行类型检查**

Run: `cd offerlab && npx tsc --noEmit`
Expected: 类型检查通过（新增类型未在别处使用，应无错误）

- [ ] **Step 3: 提交**

```bash
git add src/lib/types.ts
git commit -m "feat: add AI config and chat message types"
```

---

### Task 2: storage 扩展 — 对话历史与 AI 配置持久化

**Files:**
- Modify: `src/lib/storage.ts`

- [ ] **Step 1: 新增存储 key 常量和读写函数**

在 `src/lib/storage.ts` 末尾追加：

```typescript
import type { AiConfig, ChatHistory, ChatMessage, StepId } from "@/lib/types";

export const CHAT_HISTORY_KEY = "offerlab.chat-history";
export const AI_CONFIG_KEY = "offerlab.ai-config";

export const AI_CONFIG_DEFAULTS: AiConfig = {
  apiKey: "",
  baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
  model: "qwen3-omni-flash",
};

export const saveAiConfig = (config: AiConfig) => {
  localStorage.setItem(AI_CONFIG_KEY, JSON.stringify(config));
};

export const loadAiConfig = (): AiConfig => {
  try {
    const raw = localStorage.getItem(AI_CONFIG_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        apiKey: parsed.apiKey ?? "",
        baseUrl: parsed.baseUrl ?? AI_CONFIG_DEFAULTS.baseUrl,
        model: parsed.model ?? AI_CONFIG_DEFAULTS.model,
      };
    }
  } catch { /* ignore */ }
  return { ...AI_CONFIG_DEFAULTS };
};

export const saveChatHistory = (history: ChatHistory) => {
  localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(history));
};

export const loadChatHistory = (): ChatHistory => {
  try {
    const raw = localStorage.getItem(CHAT_HISTORY_KEY);
    if (raw) return JSON.parse(raw) as ChatHistory;
  } catch { /* ignore */ }
  return { target: [], education: [], experience: [], skills: [] };
};

export const getStepMessages = (history: ChatHistory, stepId: StepId): ChatMessage[] =>
  history[stepId] ?? [];

export const appendStepMessage = (
  history: ChatHistory,
  stepId: StepId,
  message: ChatMessage,
): ChatHistory => ({
  ...history,
  [stepId]: [...(history[stepId] ?? []), message],
});
```

- [ ] **Step 2: 运行测试验证不破坏已有功能**

Run: `cd offerlab && npm test`
Expected: 6 test files passed, 33 tests passed

- [ ] **Step 3: 提交**

```bash
git add src/lib/storage.ts
git commit -m "feat: add chat history and AI config persistence"
```

---

### Task 3: 流式 SSE 通信层

**Files:**
- Modify: `src/lib/streaming-ai.ts` (重写为通用 SSE 工具)

- [ ] **Step 1: 重写 streaming-ai.ts 为 SSE 解析工具**

```typescript
import type { ChatAssistRequest, ChatAssistResponse } from "./types";
import { buildChatAssistHeuristics } from "./mock-ai";
import OpenAI from "openai";
import type { AiConfig } from "./types";

function encode(event: string, data: Record<string, unknown>): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

/** 用 OpenAI SDK 调用真 AI 流式接口 */
export async function createAiStream(
  request: ChatAssistRequest,
  config: AiConfig,
  history: Array<{ role: "user" | "assistant"; content: string }>,
): Promise<ReadableStream<Uint8Array>> {
  const openai = new OpenAI({
    apiKey: config.apiKey || "dummy",
    baseURL: config.baseUrl || "https://dashscope.aliyuncs.com/compatible-mode/v1",
  });

  const systemPrompt = `你是一名校招简历助手。当前步骤：${request.stepId}。
你的任务是根据用户提供的材料或问题，给出简洁的中文回复。
如果是材料（JD、教育信息、项目描述等），提取关键字段作为建议卡片。
如果是问题，直接回答即可。
所有输出使用简体中文。`;

  const messages: Array<{ role: "user" | "assistant"; content: string }> = [
    { role: "system", content: systemPrompt },
    ...history.slice(-6), // 最近 6 轮
    { role: "user", content: request.question },
  ];

  const stream = await openai.chat.completions.create({
    model: config.model || "qwen3-omni-flash",
    messages: messages as any,
    stream: true,
    temperature: 0.4,
  });

  return new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder();
      controller.enqueue(enc.encode(encode("thought", { content: "正在思考..." })));

      let fullContent = "";
      for await (const chunk of stream) {
        const delta = chunk.choices?.[0]?.delta?.content;
        if (delta) {
          fullContent += delta;
          controller.enqueue(enc.encode(encode("text", { content: delta })));
        }
      }

      // 用 mock-ai 的启发式规则从完整回复中提取卡片
      const heuristicResponse = buildChatAssistHeuristics(request);
      for (const card of heuristicResponse.cards) {
        let tool: string | null = null;
        if (card.field.startsWith("targetRole")) tool = "fillTargetRole";
        else if (card.field.startsWith("education")) tool = "fillEducation";
        else if (card.field.startsWith("experiences")) tool = "fillExperience";
        else if (card.field.startsWith("skills")) tool = "fillSkills";
        if (tool) {
          controller.enqueue(
            enc.encode(encode("tool_call", { tool, field: card.field, value: card.value, label: card.label })),
          );
        }
      }

      controller.enqueue(enc.encode(encode("done", {})));
      controller.close();
    },
  });
}

/** Mock 流式回退 — 生成与真 AI 相同格式的 SSE */
export function createFallbackStream(
  request: ChatAssistRequest,
): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      const enc = new TextEncoder();
      const response = buildChatAssistHeuristics(request);

      const thoughtMsg =
        request.inputKind === "material"
          ? `正在分析${request.stepId === "target" ? "岗位" : request.stepId === "education" ? "教育" : request.stepId === "experience" ? "经历" : "技能"}材料...`
          : "正在理解你的问题...";
      controller.enqueue(enc.encode(encode("thought", { content: thoughtMsg })));

      const words = response.reply.split("");
      let i = 0;
      const interval = setInterval(() => {
        if (i < words.length) {
          controller.enqueue(enc.encode(encode("text", { content: words[i] })));
          i++;
        } else {
          clearInterval(interval);
          for (const card of response.cards) {
            let tool: string | null = null;
            if (card.field.startsWith("targetRole")) tool = "fillTargetRole";
            else if (card.field.startsWith("education")) tool = "fillEducation";
            else if (card.field.startsWith("experiences")) tool = "fillExperience";
            else if (card.field.startsWith("skills")) tool = "fillSkills";
            if (tool) {
              controller.enqueue(
                enc.encode(encode("tool_call", { tool, field: card.field, value: card.value, label: card.label })),
              );
            }
          }
          controller.enqueue(enc.encode(encode("done", {})));
          controller.close();
        }
      }, 30); // 模拟逐字输出
    },
  });
}
```

- [ ] **Step 2: 运行测试**

Run: `cd offerlab && npm test`
Expected: 6 test files passed, 33 tests passed

- [ ] **Step 3: 提交**

```bash
git add src/lib/streaming-ai.ts
git commit -m "feat: rewrite streaming-ai with real AI SSE and mock fallback"
```

---

### Task 4: server-ai 接入流式调用

**Files:**
- Modify: `src/lib/server-ai.ts`

- [ ] **Step 1: 修改 `streamAssistChat` 根据 API Key 分支**

定位到 `streamAssistChat` 函数，替换为：

```typescript
import { createAiStream, createFallbackStream } from "./streaming-ai";
import type { AiConfig, ChatMessage, StepId } from "./types";

export function streamAssistChat(
  request: ChatAssistRequest,
  config: AiConfig,
  history: ChatMessage[],
): ReadableStream<Uint8Array> {
  const formattedHistory = history.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  if (config.apiKey) {
    return createAiStream(request, config, formattedHistory);
  }
  return createFallbackStream(request);
}
```

在文件顶部新增 import，删除旧的 `streamAssistChat` 实现。

- [ ] **Step 2: 运行测试**

Run: `cd offerlab && npm test`
Expected: 6 test files passed, 33 tests passed

- [ ] **Step 3: 提交**

```bash
git add src/lib/server-ai.ts
git commit -m "feat: wire streamAssistChat to real AI when API key is present"
```

---

### Task 5: chat-assist API 路由改造

**Files:**
- Modify: `src/app/api/chat-assist/route.ts`

- [ ] **Step 1: 重写路由，接收配置和历史参数**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { streamAssistChat } from "@/lib/server-ai";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const stream = streamAssistChat(
      body,
      {
        apiKey: process.env.OPENAI_API_KEY ?? body.aiConfig?.apiKey ?? "",
        baseUrl: body.aiConfig?.baseUrl ?? process.env.OPENAI_BASE_URL ?? "",
        model: body.aiConfig?.model ?? process.env.OPENAI_MODEL ?? "",
      },
      body.history ?? [],
    );
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

- [ ] **Step 2: 构建验证**

Run: `cd offerlab && npx next build`
Expected: 编译成功

- [ ] **Step 3: 提交**

```bash
git add src/app/api/chat-assist/route.ts
git commit -m "feat: pass AI config and history to chat-assist route"
```

---

### Task 6: AI 配置面板组件

**Files:**
- Create: `src/components/ai-config.tsx`

- [ ] **Step 1: 创建 AI 配置面板组件**

```typescript
"use client";

import { useState } from "react";
import type { AiConfig } from "@/lib/types";
import { AI_CONFIG_DEFAULTS, saveAiConfig } from "@/lib/storage";

type AiConfigPanelProps = {
  config: AiConfig;
  onConfigChange: (config: AiConfig) => void;
  onTestConnection: () => void;
  testing: boolean;
};

export function AiConfigPanel({ config, onConfigChange, onTestConnection, testing }: AiConfigPanelProps) {
  const [open, setOpen] = useState(false);
  const [local, setLocal] = useState(config);

  const update = (patch: Partial<AiConfig>) => {
    const next = { ...local, ...patch };
    setLocal(next);
    onConfigChange(next);
    saveAiConfig(next);
  };

  const reset = () => {
    const defaults = { ...AI_CONFIG_DEFAULTS };
    // 保留环境变量中的 key
    defaults.apiKey = config.apiKey;
    setLocal(defaults);
    onConfigChange(defaults);
    saveAiConfig(defaults);
  };

  return (
    <div className="mt-4 rounded-[24px] border border-sky-100 bg-white">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-slate-700"
      >
        <span>AI 配置</span>
        <span className={`transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-sky-100 px-4 py-4">
          <label className="field">
            <span>API Key</span>
            <input
              type="password"
              value={local.apiKey}
              onChange={(e) => update({ apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </label>
          <label className="field">
            <span>Base URL</span>
            <input
              value={local.baseUrl}
              onChange={(e) => update({ baseUrl: e.target.value })}
              placeholder={AI_CONFIG_DEFAULTS.baseUrl}
            />
          </label>
          <label className="field">
            <span>Model</span>
            <input
              value={local.model}
              onChange={(e) => update({ model: e.target.value })}
              placeholder={AI_CONFIG_DEFAULTS.model}
            />
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onTestConnection}
              disabled={testing}
              className="rounded-full border border-sky-100 px-4 py-2 text-xs text-slate-600 transition hover:border-blue-600"
            >
              {testing ? "测试中..." : "测试连接"}
            </button>
            <button
              type="button"
              onClick={reset}
              className="rounded-full border border-sky-100 px-4 py-2 text-xs text-slate-600 transition hover:border-red-400"
            >
              重置
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 构建验证**

Run: `cd offerlab && npx next build`
Expected: 编译成功

- [ ] **Step 3: 提交**

```bash
git add src/components/ai-config.tsx
git commit -m "feat: add AI config panel component"
```

---

### Task 7: 前端流式 SSE 解析 + 对话历史管理（改造 resume-studio）

**Files:**
- Modify: `src/components/resume-studio.tsx`

这是最大的改动。改造 `sendAssist` 方法，新增对话历史管理、SSE 流式解析、AI 配置集成。

- [ ] **Step 1: 新增 import 和 state**

在 import 区域追加：

```typescript
import type { AiConfig, ChatMessage, ChatHistory } from "@/lib/types";
import { 
  AI_CONFIG_DEFAULTS, loadAiConfig, loadChatHistory, saveChatHistory, 
  appendStepMessage, getStepMessages 
} from "@/lib/storage";
import { AiConfigPanel } from "@/components/ai-config";
```

在 `ResumeStudioContent` 函数内新增 state（接在现有 state 之后）：

```typescript
const [aiConfig, setAiConfig] = useState<AiConfig>(AI_CONFIG_DEFAULTS);
const [chatHistory, setChatHistory] = useState<ChatHistory>({ target: [], education: [], experience: [], skills: [] });
const [streamingText, setStreamingText] = useState("");
const [isStreaming, setIsStreaming] = useState(false);
const [testingConnection, setTestingConnection] = useState(false);
```

- [ ] **Step 2: 添加加载 effect**

```typescript
// 加载 AI 配置和对话历史
useEffect(() => {
  const config = loadAiConfig();
  // 如果环境变量有 key 但 localStorage 没有，用环境变量的
  if (!config.apiKey && typeof window !== "undefined") {
    // 环境变量中的 key 通过 /api/ai-status 注入
  }
  setAiConfig(config);
  setChatHistory(loadChatHistory());
}, []);
```

- [ ] **Step 3: 改写 `resetAssistForStep` 加载对应步骤历史**

```typescript
const resetAssistForStep = (stepId: StepId) => {
  const stepMessages = getStepMessages(chatHistory, stepId);
  if (stepMessages.length > 0) {
    setChatMessages(stepMessages);
  } else {
    setChatMessages([{ role: "assistant", content: initialAssist[stepId] }]);
  }
  setAssistCards([]);
  setAssistMode("qa");
};
```

- [ ] **Step 4: 重写 `sendAssist` 为流式 SSE**

```typescript
const sendAssist = async () => {
  if (isChatLoading || isStreaming) return;

  const currentFieldValues = getCurrentFieldValues(draft, currentStepId, activeExperienceId);
  const fallbackMaterial = serializeCurrentFieldValues(currentStepId, currentFieldValues);
  const message = chatInput.trim() || fallbackMaterial;

  if (!message) {
    setStatus("请先填写当前步骤内容，或在右侧输入想让助手处理的材料。");
    return;
  }

  const userVisibleMessage = chatInput.trim() || "请根据我当前已填写的内容生成可回填卡片";
  const userMsg: ChatMessage = { role: "user", content: userVisibleMessage, ts: Date.now() };
  const assistantMsg: ChatMessage = { role: "assistant", content: "", cards: [], ts: Date.now() };

  // 更新 UI
  setChatMessages((prev) => [...prev, userMsg, assistantMsg]);
  setChatInput("");
  setIsChatLoading(true);
  setIsStreaming(true);
  setStreamingText("");

  const newHistory = appendStepMessage(chatHistory, currentStepId, userMsg);

  try {
    const response = await fetch("/api/chat-assist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stepId: currentStepId,
        question: message,
        inputKind: detectAssistInputKind(currentStepId, message),
        activeExperienceId,
        currentDraft: draft,
        currentFieldValues,
        aiConfig,
        history: getStepMessages(newHistory, currentStepId).slice(-10),
      }),
    });

    if (!response.ok) throw new Error(`请求失败 (${response.status})`);
    if (!response.body) throw new Error("无响应体");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullContent = "";
    const cards: ChatAssistCard[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          const eventType = line.slice(7).trim();
          continue;
        }
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (eventType === "thought") {
              setStatus(data.content);
            } else if (eventType === "text") {
              fullContent += data.content;
              setStreamingText(fullContent);
              // 更新最后一条 assistant 消息
              setChatMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = { ...next[next.length - 1], content: fullContent };
                return next;
              });
            } else if (eventType === "tool_call") {
              cards.push({
                id: `card-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                label: data.label,
                field: data.field,
                value: data.value,
                scopeStep: currentStepId,
              });
              setAssistCards([...cards]);
            }
          } catch { /* skip malformed JSON */ }
        }
      }
    }

    // 保存完整对话到 localStorage
    const finalAssistantMsg: ChatMessage = {
      role: "assistant",
      content: fullContent,
      cards: cards.length > 0 ? cards : undefined,
      ts: Date.now(),
    };
    const finalHistory = appendStepMessage(newHistory, currentStepId, finalAssistantMsg);
    setChatHistory(finalHistory);
    saveChatHistory(finalHistory);

  } catch (err) {
    setChatMessages((prev) => [
      ...prev.slice(0, -1),
      { role: "assistant", content: "请求失败，请检查网络或 AI 服务配置后重试。", ts: Date.now() },
    ]);
    setStatus("AI 助手请求失败");
  } finally {
    setIsChatLoading(false);
    setIsStreaming(false);
    setStreamingText("");
  }
};
```

- [ ] **Step 5: 在右侧边栏底部集成 AI 配置面板**

找到右侧 `<aside>` 的结尾 `</aside>`，在 `{status || "草稿已保存在本地..."}` 那行之后、`</aside>` 之前插入：

```tsx
<AiConfigPanel
  config={aiConfig}
  onConfigChange={setAiConfig}
  onTestConnection={async () => {
    setTestingConnection(true);
    try {
      const res = await fetch("/api/ai-status");
      const data = await res.json();
      setStatus(data.configured ? `AI 已就绪 (${data.model})` : "AI 未配置");
    } catch {
      setStatus("连接测试失败");
    } finally {
      setTestingConnection(false);
    }
  }}
  testing={testingConnection}
/>
```

- [ ] **Step 6: 构建验证**

Run: `cd offerlab && npx next build`
Expected: 编译成功

- [ ] **Step 7: 提交**

```bash
git add src/components/resume-studio.tsx
git commit -m "feat: streaming SSE chat with history persistence and AI config"
```

---

### Task 8: 补全改写功能（education + skills）

**Files:**
- Modify: `src/components/resume-studio.tsx` (rewriteSelectedBlock 函数)

- [ ] **Step 1: 在 `rewriteSelectedBlock` 中补全 education 和 skills 分支**

定位到 `rewriteSelectedBlock` 函数，在现有的 if-else 链中追加：

```typescript
} else if (selectedBlockId === "education") {
  original = draft.resumeSections.education
    .map((e) => `${e.school} - ${e.degreeLine} (${e.detailLine})`)
    .join("\n");
} else if (selectedBlockId.startsWith("skills") || selectedBlockId === "skills") {
  original = draft.resumeSections.skills.groups
    .flatMap((g) => g.items)
    .join(" / ");
}
```

在改写结果应用部分追加：

```typescript
} else if (selectedBlockId === "education") {
  // 教育经历改写结果应用到所有 education 的 detailLine
  setDraft((current) => ({
    ...current,
    resumeSections: {
      ...current.resumeSections,
      education: current.resumeSections.education.map((e) => ({
        ...e,
        detailLine: payload.content,
      })),
    },
  }));
}
```

（skills 分支已在现有代码中覆盖）

- [ ] **Step 2: 构建验证**

Run: `cd offerlab && npx next build`
Expected: 编译成功

- [ ] **Step 3: 提交**

```bash
git add src/components/resume-studio.tsx
git commit -m "feat: extend rewrite to support education and skills blocks"
```

---

### Task 9: 测试

**Files:**
- Modify: `src/lib/storage.test.ts` (追加)
- Modify: `src/lib/streaming-ai.test.ts` (重写)

- [ ] **Step 1: 给 storage 追加 AI 配置和对话历史的测试**

在 `src/lib/storage.test.ts` 末尾追加：

```typescript
import { 
  loadAiConfig, saveAiConfig, AI_CONFIG_DEFAULTS,
  loadChatHistory, saveChatHistory, appendStepMessage,
} from "@/lib/storage";

describe("AI config storage", () => {
  beforeEach(() => localStorage.clear());

  it("returns defaults when nothing is stored", () => {
    const config = loadAiConfig();
    expect(config.apiKey).toBe("");
    expect(config.baseUrl).toBe(AI_CONFIG_DEFAULTS.baseUrl);
    expect(config.model).toBe(AI_CONFIG_DEFAULTS.model);
  });

  it("saves and loads AI config", () => {
    saveAiConfig({ apiKey: "sk-test", baseUrl: "https://test.com", model: "test-model" });
    const loaded = loadAiConfig();
    expect(loaded.apiKey).toBe("sk-test");
    expect(loaded.model).toBe("test-model");
  });

  it("handles corrupted localStorage gracefully", () => {
    localStorage.setItem("offerlab.ai-config", "{invalid}");
    const config = loadAiConfig();
    expect(config.apiKey).toBe("");
  });
});

describe("chat history storage", () => {
  beforeEach(() => localStorage.clear());

  it("returns empty history when nothing is stored", () => {
    const history = loadChatHistory();
    expect(history.target).toEqual([]);
    expect(history.education).toEqual([]);
  });

  it("appends messages to step history", () => {
    const history = loadChatHistory();
    const msg = { role: "user" as const, content: "test", ts: 100 };
    const updated = appendStepMessage(history, "target", msg);
    expect(updated.target).toHaveLength(1);
    expect(updated.target[0].content).toBe("test");
  });
});
```

- [ ] **Step 2: 运行测试**

Run: `cd offerlab && npm test`
Expected: 8 test files passed, 38+ tests passed

- [ ] **Step 3: 提交**

```bash
git add src/lib/storage.test.ts
git commit -m "test: add AI config and chat history storage tests"
```

---

## 验证清单

1. `npm test` — 全部测试通过
2. `npx next build` — 类型检查和构建通过
3. `npm run dev` — 手动验证：
   - AI 配置面板可展开/折叠，保存后刷新保留
   - 输入消息后流式输出逐字显示
   - 切换步骤后对话历史切换
   - 改写功能支持所有区块
   - 点击建议卡片可回填表单
