import type { ChatAssistCard, ChatAssistRequest, AiConfig } from "./types";
import { buildChatAssistHeuristics } from "./mock-ai";
import OpenAI from "openai";

function encode(event: string, data: Record<string, unknown>): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

const STEP_FIELD_MAP: Record<string, string> = {
  target: "targetRole",
  campus: "experiences.active",
  education: "education",
  experience: "experiences.active",
  skills: "skills",
};

/** AI 从对话内容中提取结构化卡片 */
async function extractCardsFromAi(
  openai: OpenAI,
  model: string,
  request: ChatAssistRequest,
  conversationText: string,
): Promise<ChatAssistCard[]> {
  const stepField = STEP_FIELD_MAP[request.stepId] ?? "targetRole";

  const cardPrompt = `你是一名校招简历助手。请分析下面的对话内容，提取可用于回填简历表单的结构化字段。

当前步骤：${request.stepId}
字段前缀：${stepField}

请从对话中提取尽可能多的字段，以 JSON 数组格式返回，每个元素包含：
- label: 字段的中文标题（如"建议填写岗位名称"）
- field: 字段名（以 "${stepField}." 开头，如 "${stepField}.roleName"）
- value: 提取到的值
- reason: 简短的提取理由

注意事项：
- 如果某字段在对话中没有出现，不要虚构
- 至少返回 label / field / value 三个字段
- 只返回 JSON 数组，不要 Markdown

可用的字段前缀参考：
- targetRole.roleName / targetRole.targetCompany / targetRole.city / targetRole.jobDescription
- education.0.school / education.0.major / education.0.degree / education.0.graduationYear / education.0.gpa
- experiences.active.name / experiences.active.role / experiences.active.timeframe / experiences.active.responsibility / experiences.active.tools / experiences.active.result
- skills.skillTags / skills.certificates / skills.languages / skills.extraNotes

对话内容：
${conversationText}`;

  try {
    const response = await openai.chat.completions.create({
      model,
      messages: [{ role: "user", content: cardPrompt }],
      temperature: 0.1,
    });

    let content = response.choices?.[0]?.message?.content ?? "";
    content = content.replace(/^```(?:json)?\s*([\s\S]*?)```$/m, "$1").trim();
    const parsed = JSON.parse(content) as Array<{ label: string; field: string; value: string; reason?: string }>;

    return parsed
      .filter((c) => c.field && c.value)
      .map((c) => ({
        id: `card-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        label: c.label,
        field: c.field,
        value: Array.isArray(c.value) ? c.value.join(", ") : String(c.value),
        reason: c.reason,
        scopeStep: request.stepId,
      }));
  } catch {
    return [];
  }
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
如果是材料（JD、教育信息、项目描述等），帮助用户整理关键信息。
如果是问题，直接回答即可。
所有输出使用简体中文。`;

  const messages: Array<{ role: string; content: string }> = [
    { role: "system", content: systemPrompt },
    ...history.slice(-6),
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

      // 让 AI 自己从对话中提取卡片，而非正则匹配用户原始输入
      const conversationText = `用户：${request.question}\n助手：${fullContent}`;
      const cards = await extractCardsFromAi(openai, config.model || "qwen3-omni-flash", request, conversationText);

      for (const card of cards) {
        let tool: string | null = null;
        if (card.field.startsWith("targetRole")) tool = "fillTargetRole";
        else if (card.field.startsWith("education")) tool = "fillEducation";
        else if (card.field.startsWith("experiences")) tool = "fillExperience";
        else if (card.field.startsWith("skills")) tool = "fillSkills";
        if (tool) {
          controller.enqueue(
            enc.encode(encode("tool_call", {
              tool,
              field: card.field,
              value: card.value,
              label: card.label,
              reason: card.reason,
            })),
          );
        }
      }

      controller.enqueue(enc.encode(encode("done", {})));
      controller.close();
    },
  });
}

/** Mock 流式回退 — 保持原有启发式规则 */
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

      const chars = response.reply.split("");
      let i = 0;
      const interval = setInterval(() => {
        if (i < chars.length) {
          controller.enqueue(enc.encode(encode("text", { content: chars[i] })));
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
      }, 30);
    },
  });
}
