import { resumeDraftSchema } from "@/lib/schema";
import { createEmptyDraft, hydrateDraft } from "@/lib/resume";
import type { ResumeDraft } from "@/lib/types";
import type { AiConfig, ChatHistory, ChatMessage, StepId } from "@/lib/types";
import { getDeviceId } from "@/lib/device";

export const DRAFT_STORAGE_KEY = "offerlab.resume-draft";

export const saveDraftToStorage = (draft: ResumeDraft) => {
  localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
};

export const loadDraftFromStorage = (): ResumeDraft | null => {
  const raw = localStorage.getItem(DRAFT_STORAGE_KEY);

  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw);
    const validated = resumeDraftSchema.safeParse(parsed);

    if (!validated.success) {
      return createEmptyDraft();
    }

    return hydrateDraft(validated.data);
  } catch {
    return createEmptyDraft();
  }
};

// === AI 配置持久化 ===

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
  return { target: [], campus: [], education: [], experience: [], skills: [] };
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

// === Supabase 云端同步 ===

export async function syncDraftToSupabase(draft: ResumeDraft): Promise<boolean> {
  try {
    const deviceId = getDeviceId();
    const res = await fetch("/api/sync/draft", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId, draft_data: draft }),
    });
    if (!res.ok) {
      console.warn("syncDraftToSupabase failed:", res.status, await res.text());
      return false;
    }
    return true;
  } catch (err) {
    console.warn("syncDraftToSupabase error:", err);
    return false;
  }
}

export async function loadDraftFromSupabase(): Promise<ResumeDraft | null> {
  try {
    const deviceId = getDeviceId();
    const res = await fetch(`/api/sync/draft?device_id=${encodeURIComponent(deviceId)}`);
    if (!res.ok) {
      if (res.status !== 404) console.warn("loadDraftFromSupabase failed:", res.status);
      return null;
    }
    const { draft } = await res.json();
    if (!draft) return null;
    const validated = resumeDraftSchema.safeParse(draft);
    if (!validated.success) {
      console.warn("loadDraftFromSupabase: schema validation failed");
      return null;
    }
    return hydrateDraft(validated.data);
  } catch (err) {
    console.warn("loadDraftFromSupabase error:", err);
    return null;
  }
}

export async function syncChatHistoryToSupabase(history: ChatHistory): Promise<boolean> {
  try {
    const deviceId = getDeviceId();
    const res = await fetch("/api/sync/chat", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId, history }),
    });
    if (!res.ok) {
      console.warn("syncChatHistoryToSupabase failed:", res.status, await res.text());
      return false;
    }
    return true;
  } catch (err) {
    console.warn("syncChatHistoryToSupabase error:", err);
    return false;
  }
}

export async function loadChatHistoryFromSupabase(): Promise<ChatHistory | null> {
  try {
    const deviceId = getDeviceId();
    const res = await fetch(`/api/sync/chat?device_id=${encodeURIComponent(deviceId)}`);
    if (!res.ok) {
      if (res.status !== 404) console.warn("loadChatHistoryFromSupabase failed:", res.status);
      return null;
    }
    const { history } = await res.json();
    return history ?? null;
  } catch (err) {
    console.warn("loadChatHistoryFromSupabase error:", err);
    return null;
  }
}
