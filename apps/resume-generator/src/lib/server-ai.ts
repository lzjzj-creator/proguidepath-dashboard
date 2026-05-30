import { createAiStream, createFallbackStream } from "./streaming-ai";
import type { AiConfig, ChatMessage } from "./types";
import {
  buildChatAssistHeuristics,
  generateResumeHeuristics,
  parseRoleHeuristics,
  rewriteBlockHeuristics,
} from "@/lib/mock-ai";
import { chatAssistResponseSchema, resumeDraftSchema } from "@/lib/schema";
import type {
  ChatAssistRequest,
  ChatAssistResponse,
  ResumeDraft,
  ResumeRewriteRequest,
  ResumeRewriteResponse,
  RoleParseResponse,
} from "@/lib/types";

const apiKey = process.env.OPENAI_API_KEY;
const baseUrl =
  process.env.OPENAI_BASE_URL ?? "https://dashscope.aliyuncs.com/compatible-mode/v1";
const model = process.env.OPENAI_MODEL ?? "qwen3-omni-flash";

const getJsonFromContent = async <T>(
  prompt: string,
  fallback: T,
  validate?: (payload: unknown) => T | null,
): Promise<T> => {
  if (!apiKey) {
    return fallback;
  }

  try {
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        temperature: 0.4,
        enable_thinking: false,
        modalities: ["text"],
        messages: [
          {
            role: "system",
            content:
              "你是一名校招简历助手。所有面向用户展示的文案都必须使用简体中文。只返回 JSON，不要返回 Markdown，也不要添加额外解释。",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    });

    if (!response.ok) {
      return fallback;
    }

    const payload = await response.json();
    let content = payload?.choices?.[0]?.message?.content;

    if (typeof content !== "string") {
      return fallback;
    }

    // Strip markdown code fences (```json ... ```) that many LLMs wrap around JSON
    content = content.replace(/^```(?:json)?\s*([\s\S]*?)```$/m, "$1").trim();

    const parsed = JSON.parse(content) as unknown;
    const validated = validate?.(parsed);
    if (validated !== undefined && validated !== null) return validated;
    return fallback;
  } catch {
    return fallback;
  }
};

export const parseRole = async (
  roleName: string,
  jobDescription: string,
): Promise<RoleParseResponse> => {
  const fallback = parseRoleHeuristics(roleName, jobDescription);

  return getJsonFromContent<RoleParseResponse>(
    `请从这个求职目标中提取岗位关键词和职责要点，所有字符串使用简体中文返回，只返回 JSON。${JSON.stringify(
      {
        roleName,
        jobDescription,
        output: {
          keywords: ["string"],
          responsibilities: ["string"],
          toneHint: "string",
        },
      },
    )}`,
    fallback,
  );
};

export const generateResume = async (draft: ResumeDraft): Promise<ResumeDraft> => {
  const validated = resumeDraftSchema.safeParse(draft);
  const safeDraft = validated.success ? validated.data : generateResumeHeuristics(draft);
  const fallback = generateResumeHeuristics(safeDraft);

  // 去掉 roleKeywords，防止 AI 把它当成技能类别引入简历正文
  const { roleKeywords: _rk, ...draftWithoutKeywords } = safeDraft;

  return getJsonFromContent<ResumeDraft>(
    `请把这份校招简历采集信息整理为结构化简历草稿，所有面向用户展示的字段内容使用简体中文。保留原始事实，不要虚构经历，只返回 JSON。\n重要：skills.groups 必须直接使用用户输入的 skillTags / certificates / languages / extraNotes 原文，不要改写、润色或新增内容。skillTags 放入「技能」组。certificates 和 languages 合并放入「证书」组。extraNotes 放入「补充备注」组。不要创建其他自定义分组。${JSON.stringify(
      {
        draft: draftWithoutKeywords,
        outputShape: fallback,
      },
    )}`,
    fallback,
    (payload) => {
      const parsed = resumeDraftSchema.safeParse(payload);
      if (!parsed.success) return null;

      // 拒绝 AI 返回的空壳 — summary/projects/education 全空时降级到 fallback
      const sections = parsed.data.resumeSections;

      // 剔除 AI 可能仍然添加的非标准分组（只保留 技能/证书/补充备注）
      const ALLOWED_TITLES = new Set(["技能", "证书", "补充备注"]);
      sections.skills.groups = sections.skills.groups.filter(
        (g) => ALLOWED_TITLES.has(g.title),
      );

      const hasContent =
        sections.summary.content.trim().length > 0 ||
        sections.education.length > 0 ||
        sections.skills.groups.length > 0;

      return hasContent ? parsed.data : null;
    },
  );
};

export const assistChat = async (
  request: ChatAssistRequest,
): Promise<ChatAssistResponse> => {
  const fallback = buildChatAssistHeuristics(request);

  return getJsonFromContent<ChatAssistResponse>(
    `你是校招简历产品中的步骤助手。请针对当前步骤给出简洁中文建议，并按需返回字段建议，只返回 JSON。${JSON.stringify(
      {
        request,
        output: fallback,
      },
    )}`,
    fallback,
    (payload) => {
      const parsed = chatAssistResponseSchema.safeParse(payload);
      return parsed.success ? parsed.data : null;
    },
  );
};

export async function streamAssistChat(
  request: ChatAssistRequest,
  config: AiConfig,
  history: ChatMessage[],
): Promise<ReadableStream<Uint8Array>> {
  const formattedHistory = history.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  if (config.apiKey) {
    return createAiStream(request, config, formattedHistory);
  }
  return createFallbackStream(request);
}

export const rewriteBlock = async (
  request: ResumeRewriteRequest,
): Promise<ResumeRewriteResponse> => {
  const fallback = rewriteBlockHeuristics(request);

  return getJsonFromContent<ResumeRewriteResponse>(
    `请改写这段简历内容，使其更贴合目标岗位。语气保持克制、真实、具体，不要虚构事实，所有输出使用简体中文，只返回 JSON。重点关注用户的改写方向：${request.intent}。${JSON.stringify(
      {
        original: request.original,
        intent: request.intent,
        targetRole: request.targetRole,
        output: fallback,
      },
    )}`,
    fallback,
  );
};
