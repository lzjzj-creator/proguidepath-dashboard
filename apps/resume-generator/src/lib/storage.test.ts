import {
  DRAFT_STORAGE_KEY,
  loadDraftFromStorage,
  saveDraftToStorage,
} from "@/lib/storage";
import { createEmptyDraft } from "@/lib/resume";

describe("draft storage", () => {
  const storage = new Map<string, string>();

  beforeEach(() => {
    storage.clear();
    Object.defineProperty(globalThis, "localStorage", {
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
        removeItem: (key: string) => storage.delete(key),
        clear: () => storage.clear(),
      },
      configurable: true,
    });
  });

  it("round-trips a valid draft in localStorage", () => {
    const draft = createEmptyDraft();
    draft.targetRole.roleName = "运营";

    saveDraftToStorage(draft);

    expect(globalThis.localStorage.getItem(DRAFT_STORAGE_KEY)).toContain("运营");
    expect(loadDraftFromStorage()?.targetRole.roleName).toBe("运营");
  });

  it("falls back to a clean draft when storage is corrupted", () => {
    globalThis.localStorage.setItem(DRAFT_STORAGE_KEY, "{broken json");

    const restored = loadDraftFromStorage();

    expect(restored?.targetRole.roleName).toBe("");
    expect(restored?.experiences).toHaveLength(1);
  });
});

import { AI_CONFIG_DEFAULTS, loadAiConfig, saveAiConfig, loadChatHistory, saveChatHistory, appendStepMessage } from "@/lib/storage";

describe("AI config storage", () => {
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
    globalThis.localStorage.setItem("offerlab.ai-config", "{invalid}");
    const config = loadAiConfig();
    expect(config.apiKey).toBe("");
  });
});

describe("chat history storage", () => {
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
    expect(updated.education).toEqual([]); // 不影响其他步骤
  });
});
