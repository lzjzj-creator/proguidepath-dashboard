# AI 助手增强设计

## 背景

OfferLab 现有的 AI 功能存在多个问题：
- `chat-assist` 端点返回 SSE stream 但前端用 `response.json()` 解析，类型不匹配导致报错
- `streamAssistChat()` 被注释写死为 "Always use heuristic fallback for now"，即使配置了 API Key 也不会调用真 AI
- 无对话记忆，每次消息独立
- 改写功能只支持 summary 和 project bullets，缺 education 和 skills
- 无 AI 配置界面，用户无法在 UI 中设置 API Key

## 目标

将 AI 助手改造为功能完整、可配置、流式输出的真正 AI 助手。

## 设计

### 1. AI 配置面板

右侧边栏底部可折叠配置区域。

| 字段 | 类型 | 默认值 |
|------|------|--------|
| API Key | password input | 空（优先读 `OPENAI_API_KEY` 环境变量） |
| Base URL | text | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Model | text | `qwen3-omni-flash` |

操作：保存（存 localStorage 并验证连通性）、测试连接、重置（清空配置回到 mock 模式）。

### 2. 流式 chat-assist

**数据流：**

```
用户输入 → sendAssist()
  → POST /api/chat-assist (携带对话历史)
    → server-ai:
        有 API Key → OpenAI SDK stream() → DashScope/Qwen
        无 API Key → 改造 mock 为流式 SSE
    → 返回 SSE stream
  → 前端 ReadableStream 逐块解析:
    event: thought → 显示"正在思考..."
    event: text → 逐字追加到当前消息
    event: tool_call → 显示建议卡片
    event: done → 结束
  → 保存完整消息到 localStorage
```

**对话记忆存储：**

每个步骤（target/education/experience/skills）独立保存对话历史至 localStorage，key 为 `offerlab.chat-history`，切换步骤时自动加载对应历史。

### 3. 改写功能补全

改写支持扩展到所有区块：

- 个人概述 (summary) — 已有，增强 prompt
- 项目要点 (project bullets) — 已有，增强 prompt
- 教育经历 (education) — 新增
- 技能标签 (skills) — 新增

改写 prompt 携带：目标岗位、原始内容、改写方向。

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `src/lib/server-ai.ts` | `streamAssistChat()` 接入真 AI 流式调用；`assistChat()` 携带对话历史 |
| `src/lib/mock-ai.ts` | 增强 mock 为可流式输出格式 |
| `src/lib/streaming-ai.ts` | 重构为通用 SSE 工具函数 |
| `src/components/resume-studio.tsx` | 添加 AI 配置面板；修改 `sendAssist()` 使用 ReadableStream 解析 SSE；添加对话历史管理；补全改写区块 |
| `src/app/api/chat-assist/route.ts` | 传递对话历史参数 |
| `src/lib/types.ts` | 添加对话消息、AI 配置等类型 |

## 验证方式

1. `npm test` — 已有测试应全部通过，新增覆盖流式输出和配置功能
2. `npx next build` — 类型检查和构建通过
3. `npm run dev` — 手动测试流式输出、配置保存、对话记忆、改写补全
