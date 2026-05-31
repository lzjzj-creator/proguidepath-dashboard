"use client";

import {
  startTransition,
  useEffect,
  useMemo,
  useSyncExternalStore,
  useState,
} from "react";
import { ResumePreview } from "@/components/resume-preview";
import {
  applyAssistCardToDraft,
  createEmptyDraft,
  createEmptyExperience,
  getStepCompletion,
  getStepSummaries,
  hydrateDraft,
  removeExperience,
  upsertExperience,
} from "@/lib/resume";
import { loadDraftFromStorage, saveDraftToStorage, loadChatHistory, saveChatHistory, getStepMessages, appendStepMessage, syncDraftToSupabase, loadDraftFromSupabase, syncChatHistoryToSupabase, loadChatHistoryFromSupabase } from "@/lib/storage";
import { AiConfigPanel } from "@/components/ai-config";
import type {
  AssistInputKind,
  AssistMode,
  ChatAssistCard,
  ChatAssistResponse,
  ChatMessage,
  ChatHistory,
  EducationEntry,
  ExperienceEntry,
  ResumeDraft,
  SkillsProfile,
  StepId,
  TargetRole,
} from "@/lib/types";
import { cn } from "@/lib/cn";

const steps: Array<{ id: StepId; label: string; kicker: string }> = [
  { id: "target", label: "目标岗位", kicker: "步骤 01" },
  { id: "education", label: "教育经历", kicker: "步骤 02" },
  { id: "campus", label: "校园经历", kicker: "步骤 03" },
  { id: "experience", label: "社会经历", kicker: "步骤 04" },
  { id: "skills", label: "技能证书", kicker: "步骤 05" },
];

const initialAssist: Record<StepId, string> = {
  target: "把 JD 或岗位描述贴进来，我会先整理成目标岗位可直接应用的建议卡片。",
  campus: "把校园项目或比赛经历的原始描述贴进来，我会生成职责、工具、结果等卡片。",
  education: "把学校、专业、学历、毕业时间、GPA 等原始信息贴进来，我会拆成教育经历卡片。",
  experience: "把当前实习或社会经历的原始描述贴进来，我会按这条经历生成职责、工具、结果等卡片。",
  skills: "把技能清单、证书、语言能力或补充说明贴进来，我会整理成技能证书卡片。",
};

const intakeAssistCopy: Record<
  StepId,
  { title: string; description: string; promptLabel: string; placeholder: string }
> = {
  target: {
    title: "目标岗位 Agent",
    description: "支持粘贴 JD 或岗位描述。助手只生成目标岗位这一步的建议卡片，点击后才会回填。",
    promptLabel: "给目标岗位助手输入材料",
    placeholder: "粘贴 JD、岗位职责或任职要求，我会提炼岗位名称、城市和岗位描述摘要。",
  },
  education: {
    title: "教育经历 Agent",
    description: "支持粘贴教育原始信息。助手只生成教育经历相关卡片，不会改动项目或技能字段。",
    promptLabel: "给教育经历助手输入材料",
    placeholder: "例如：复旦大学，信息管理与信息系统，本科，2026 年毕业，GPA 3.7/4.0。",
  },
  experience: {
    title: "社会经历 Agent",
    description: "支持粘贴当前这条经历的原始描述。助手只作用于当前选中的经历卡。",
    promptLabel: "给社会经历助手输入材料",
    placeholder: "粘贴当前实习或社会经历的原始描述，我会提炼名称、职责、工具和结果。",
  },
  skills: {
    title: "技能证书 Agent",
    description: "支持粘贴技能、证书、语言或补充说明。助手只生成技能步骤的建议卡片。",
    promptLabel: "给技能证书助手输入材料",
    placeholder: "例如：熟悉 SQL、Python、Tableau；英语六级；阿里云 ACA；做过用户增长分析。",
  },
  campus: {
    title: "校园经历 Agent",
    description: "支持粘贴当前这条校园经历的原始描述。助手只作用于当前选中的经历卡。",
    promptLabel: "给校园经历助手输入材料",
    placeholder: "粘贴当前项目或比赛的原始描述，我会提炼名称、职责、工具和结果。",
  },
};

const getSelectedBlockLabel = (blockId: string) => {
  if (blockId === "summary") {
    return "个人概述";
  }

  if (blockId === "education") {
    return "教育经历";
  }

  if (blockId === "skills") {
    return "技能证书";
  }

  return blockId;
};

type AssistMessage = {
  role: "assistant" | "user";
  content: string;
};

const updateEducation = (
  draft: ResumeDraft,
  index: number,
  patch: Partial<EducationEntry>,
) => ({
  ...draft,
  education: draft.education.map((item, itemIndex) =>
    itemIndex === index ? { ...item, ...patch } : item,
  ),
});

const ExperienceCard = ({
  experience,
  index,
  isActive,
  activeExperienceId,
  setActiveExperienceId,
  setExperienceField,
  onDelete,
}: {
  experience: ExperienceEntry;
  index: number;
  isActive: boolean;
  activeExperienceId: string;
  setActiveExperienceId: (id: string) => void;
  setExperienceField: (experience: ExperienceEntry, patch: Partial<ExperienceEntry>) => void;
  onDelete: (id: string) => void;
}) => (
  <div
    key={experience.id}
    onClick={() => setActiveExperienceId(experience.id)}
    className={cn(
      "rounded-[28px] border bg-surface p-5 transition",
      isActive
        ? "border-coral shadow-[0_18px_50px_rgba(232,169,155,0.12)]"
        : "border-border",
    )}
  >
    <div className="mb-4 flex items-center justify-between">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.26em] text-coral">
          经历 {index + 1}
        </p>
        <h3 className="mt-2 text-lg font-medium text-slate-950">
          项目 / 比赛 / 实习
        </h3>
      </div>
      <div className="flex items-center gap-2">
        {isActive && (
          <span className="rounded-full bg-coral px-3 py-2 text-[10px] uppercase tracking-[0.22em] text-white">
            AI 当前作用于此
          </span>
        )}
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onDelete(experience.id);
          }}
          className="rounded-full border border-border px-3 py-2 text-xs text-slate-500 transition hover:border-coral-deep hover:text-coral"
        >
          删除
        </button>
      </div>
    </div>
    <div className="grid gap-4 md:grid-cols-2">
      <label className="field">
        <span>名称</span>
        <input
          value={experience.name}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, { name: event.target.value })
          }
        />
      </label>
      <label className="field">
        <span>角色</span>
        <input
          value={experience.role}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, { role: event.target.value })
          }
        />
      </label>
      <label className="field">
        <span>时间</span>
        <input
          value={experience.timeframe}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, { timeframe: event.target.value })
          }
        />
      </label>
      <label className="field">
        <span>类型</span>
        <select
          value={experience.category}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, {
              category: event.target.value as ExperienceEntry["category"],
            })
          }
        >
          <option value="project">项目</option>
          <option value="competition">比赛</option>
          <option value="internship">实习</option>
        </select>
      </label>
      <label className="field md:col-span-2">
        <span>你做了什么</span>
        <textarea
          value={experience.responsibility}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, { responsibility: event.target.value })
          }
        />
      </label>
      <label className="field">
        <span>工具 / 方法</span>
        <input
          value={experience.tools}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, { tools: event.target.value })
          }
        />
      </label>
      <label className="field">
        <span>结果</span>
        <input
          value={experience.result}
          onFocus={() => setActiveExperienceId(experience.id)}
          onChange={(event) =>
            setExperienceField(experience, { result: event.target.value })
          }
        />
      </label>
    </div>
  </div>
);

const detectAssistInputKind = (stepId: StepId, value: string): AssistInputKind => {
  const text = value.trim();
  const lineCount = text.split(/\n/).filter(Boolean).length;
  const materialPattern =
    stepId === "target"
      ? /JD|岗位|职责|要求|任职|工作地点/i
      : stepId === "education"
        ? /学校|院校|专业|学历|学位|GPA|毕业/i
        : stepId === "experience" || stepId === "campus"
          ? /项目|实习|比赛|负责|产出|结果|工具/i
          : /技能|证书|语言|Python|SQL|Figma|Excel/i;

  if (lineCount >= 2 || text.length >= 60 || materialPattern.test(text)) {
    return "material";
  }

  return "question";
};

const getCurrentFieldValues = (
  draft: ResumeDraft,
  stepId: StepId,
  activeExperienceId: string,
) => {
  if (stepId === "target") {
    return draft.targetRole;
  }

  if (stepId === "education") {
    return draft.education[0];
  }

  if (stepId === "experience" || stepId === "campus") {
    return (
      draft.experiences.find((experience) => experience.id === activeExperienceId) ??
      draft.experiences[0] ??
      null
    );
  }

  return draft.skills;
};

const serializeCurrentFieldValues = (
  stepId: StepId,
  currentFieldValues: ReturnType<typeof getCurrentFieldValues>,
) => {
  if (!currentFieldValues) return "";
  if (stepId === "target") {
    const fields = currentFieldValues as TargetRole;
    return [
      fields.roleName ? `职位：${fields.roleName}` : "",
      fields.targetCompany
        ? `公司：${fields.targetCompany}`
        : "",
      fields.city ? `城市：${fields.city}` : "",
      fields.jobDescription
        ? `岗位描述：${fields.jobDescription}`
        : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (stepId === "education") {
    const fields = currentFieldValues as EducationEntry;
    return [
      fields.school ? `学校：${fields.school}` : "",
      fields.major ? `专业：${fields.major}` : "",
      fields.degree ? `学历：${fields.degree}` : "",
      fields.graduationYear
        ? `毕业时间：${fields.graduationYear}`
        : "",
      fields.gpa ? `GPA：${fields.gpa}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (stepId === "experience" || stepId === "campus") {
    const fields = currentFieldValues as ExperienceEntry;
    return [
      fields.name ? `经历：${fields.name}` : "",
      fields.role ? `角色：${fields.role}` : "",
      fields.timeframe ? `时间：${fields.timeframe}` : "",
      fields.responsibility
        ? `职责：${fields.responsibility}`
        : "",
      fields.tools ? `工具：${fields.tools}` : "",
      fields.result ? `结果：${fields.result}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  const skillField = currentFieldValues as SkillsProfile;
  return [
    skillField.skillTags.length > 0
      ? `技能：${skillField.skillTags.join(", ")}`
      : "",
    skillField.certificates
      ? `证书：${skillField.certificates}`
      : "",
    skillField.languages ? `语言：${skillField.languages}` : "",
    skillField.extraNotes
      ? `补充说明：${skillField.extraNotes}`
      : "",
  ]
    .filter(Boolean)
    .join("\n");
};

const getModeFromDraft = (draft: ResumeDraft) =>
  draft.resumeSections.education.length > 0 ? "edit" : "intake";

const subscribeToHydration = () => () => {};

type ResumeStudioContentProps = {
  initialDraft: ResumeDraft;
  persistDraft: boolean;
};

function ResumeStudioContent({
  initialDraft,
  persistDraft,
}: ResumeStudioContentProps) {
  const [draft, setDraft] = useState<ResumeDraft>(initialDraft);
  const [currentStep, setCurrentStep] = useState(0);
  const [mode, setMode] = useState<"intake" | "edit">(
    getModeFromDraft(initialDraft),
  );
  const [isGenerating, setIsGenerating] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [aiConfigured, setAiConfigured] = useState(true);
  const [isRewriting, setIsRewriting] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<AssistMessage[]>([
    { role: "assistant", content: initialAssist.target },
  ]);
  const [assistCards, setAssistCards] = useState<ChatAssistCard[]>([]);
  const [assistMode, setAssistMode] = useState<AssistMode>("qa");
  const [selectedBlockId, setSelectedBlockId] = useState("summary");
  const [activeExperienceId, setActiveExperienceId] = useState(
    initialDraft.experiences[0]?.id ?? "",
  );
  const [rewriteIntent, setRewriteIntent] = useState(
    "让这段内容更具体、更有证据感，也更像真实校招简历中的表达。",
  );
  const [status, setStatus] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatHistory>({} as ChatHistory);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const currentStepId = steps[currentStep].id;
  const completion = useMemo(() => getStepCompletion(draft), [draft]);
  const summaries = useMemo(() => getStepSummaries(draft), [draft]);
  const currentAssistCopy = intakeAssistCopy[currentStepId];

  const resetAssistForStep = (stepId: StepId) => {
    const stepMessages = getStepMessages(chatHistory, stepId);
    if (stepMessages.length > 0) {
      setChatMessages(stepMessages);
    } else {
      setChatMessages([{ role: "assistant" as const, content: initialAssist[stepId] }]);
    }
    setAssistCards([]);
    setAssistMode("qa");
  };

  const moveToStep = (step: number) => {
    const nextStep = Math.min(steps.length - 1, Math.max(0, step));
    const nextStepId = steps[nextStep].id;
    setCurrentStep(nextStep);
    resetAssistForStep(nextStepId);
    if (nextStepId === "experience") {
      const firstSocial = draft.experiences.find((e) => e.kind === "social");
      if (firstSocial) setActiveExperienceId(firstSocial.id);
    } else if (nextStepId === "campus") {
      const firstCampus = draft.experiences.find((e) => e.kind === "campus");
      if (firstCampus) setActiveExperienceId(firstCampus.id);
    }
  };

  useEffect(() => {
    fetch("/api/ai-status")
      .then((response) => response.json())
      .then((data) => setAiConfigured(data.configured))
      .catch(() => setAiConfigured(false));
  }, []);

  useEffect(() => {
    if (!persistDraft) return;

    syncDraftToSupabase(draft).then(() => {
      saveDraftToStorage(draft);
    });
  }, [draft, persistDraft]);

  useEffect(() => {
    (async () => {
      const remote = await loadChatHistoryFromSupabase();
      if (remote) {
        const stepMsgs = remote.target ?? [];
        if (stepMsgs.length > 0) {
          setChatMessages(stepMsgs.map((m) => ({ role: m.role, content: m.content })));
        }
        setChatHistory(remote);
        saveChatHistory(remote);
        return;
      }
      const saved = loadChatHistory();
      const stepMsgs = saved.target ?? [];
      if (stepMsgs.length > 0) {
        setChatMessages(stepMsgs.map((m) => ({ role: m.role, content: m.content })));
      }
      setChatHistory(saved);
    })();
  }, []);

  const setExperienceField = (
    experience: ExperienceEntry,
    patch: Partial<ExperienceEntry>,
  ) => {
    setActiveExperienceId(experience.id);
    setDraft((current) => ({
      ...current,
      experiences: upsertExperience(current.experiences, {
        ...experience,
        ...patch,
      }),
    }));
  };

  const applyCard = (card: ChatAssistCard) => {
    setDraft((current) =>
      applyAssistCardToDraft(current, card, {
        activeExperienceId,
      }),
    );
    setStatus(`已应用到${steps[currentStep].label}`);
  };

  const sendAssist = async () => {
    if (isChatLoading || isStreaming) return;

    const currentFieldValues = getCurrentFieldValues(
      draft,
      currentStepId,
      activeExperienceId,
    );
    const fallbackMaterial = serializeCurrentFieldValues(
      currentStepId,
      currentFieldValues,
    );
    const message = chatInput.trim() || fallbackMaterial;

    if (!message) {
      setStatus("请先填写当前步骤内容，或在右侧输入想让助手处理的材料。");
      return;
    }

    const userVisibleMessage = chatInput.trim() || "请根据我当前已填写的内容生成可回填卡片";
    const inputKind = detectAssistInputKind(currentStepId, message);

    const userMsg: ChatMessage = { role: "user", content: userVisibleMessage, ts: Date.now() };
    const assistantMsg: ChatMessage = { role: "assistant", content: "", ts: Date.now() };

    setChatMessages((current) => [...current, userMsg, assistantMsg]);
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
          inputKind,
          activeExperienceId,
          currentDraft: draft,
          currentFieldValues,
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
      let currentEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
            continue;
          }
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (currentEvent === "thought") {
                setStatus(data.content);
              } else if (currentEvent === "text") {
                fullContent += data.content;
                setStreamingText(fullContent);
                setChatMessages((prev) => {
                  const next = [...prev];
                  next[next.length - 1] = { ...next[next.length - 1], content: fullContent };
                  return next;
                });
              } else if (currentEvent === "tool_call") {
                cards.push({
                  id: `card-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  label: data.label,
                  field: data.field,
                  value: data.value,
                  reason: data.reason,
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
      syncChatHistoryToSupabase(finalHistory);

    } catch {
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

  const generateResume = async () => {
    setIsGenerating(true);
    setStatus("正在生成结构化简历草稿...");

    try {
      const parsedResponse = await fetch("/api/role-parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          roleName: draft.targetRole.roleName,
          jobDescription: draft.targetRole.jobDescription,
        }),
      });

      if (!parsedResponse.ok) throw new Error("角色解析失败");

      const parsedRole = await parsedResponse.json();

      const response = await fetch("/api/resume-generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...draft,
          roleKeywords: parsedRole.keywords ?? draft.roleKeywords,
        }),
      });

      if (!response.ok) throw new Error("生成失败");

      const generated = await response.json();

      setDraft(hydrateDraft(generated));
      setMode("edit");
      setSelectedBlockId("summary");
      setStatus("简历已生成。你可以继续逐块润色，或直接导出 PDF。");
    } catch {
      setStatus("生成失败，请重试。");
    } finally {
      setIsGenerating(false);
    }
  };

  const rewriteSelectedBlock = async () => {
    let original = "";

    if (selectedBlockId === "summary") {
      original = draft.resumeSections.summary.content;
    } else if (selectedBlockId === "skills") {
      original = draft.resumeSections.skills.groups
        .flatMap((group) => group.items)
        .join(" / ");
    } else if (selectedBlockId === "education") {
      original = draft.resumeSections.education
        .map((e) => `${e.school} - ${e.degreeLine} (${e.detailLine})`)
        .join("\n");
    }

    if (!original.trim()) {
      return;
    }

    setIsRewriting(true);
    setStatus("正在改写当前选中内容...");

    try {
      const rewriteResponse = await fetch("/api/resume-rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sectionId: selectedBlockId,
          original,
          intent: rewriteIntent,
          targetRole: draft.targetRole,
        }),
      });

      if (!rewriteResponse.ok) throw new Error("改写失败");

      const payload = await rewriteResponse.json();

      if (selectedBlockId === "summary") {
        setDraft((current) => ({
          ...current,
          resumeSections: {
            ...current.resumeSections,
            summary: {
              ...current.resumeSections.summary,
              content: payload.content,
            },
          },
        }));
      } else if (selectedBlockId === "education") {
        setDraft((current) => ({
          ...current,
          resumeSections: {
            ...current.resumeSections,
            education: current.resumeSections.education.map((e, i) => ({
              ...e,
              detailLine: i === 0 ? payload.content : e.detailLine,
            })),
          },
        }));
      }

      setStatus("已应用改写结果。");
    } catch {
      setStatus("改写失败，请重试。");
    } finally {
      setIsRewriting(false);
    }
  };

  const exportPdf = async () => {
    setStatus("正在导出 PDF...");

    const response = await fetch("/api/export-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft }),
    });

    if (!response.ok) {
      const error = await response.json();
      setStatus(error.message ?? "导出失败。");
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${draft.targetRole?.roleName || "offerlab-resume"}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus("PDF 已开始下载。");
  };

  return (
    <div className="min-h-screen bg-bg text-slate-800">
      <section className="mx-auto max-w-7xl px-6 pb-10 pt-6 lg:px-10">

          <div className="mt-6 grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)_300px]">
            <aside className="rounded-[32px] border border-border bg-surface p-5 shadow-[0_18px_60px_rgba(45,42,40,0.05)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-coral">
                    工作流
                  </p>
                  <h2 className="mt-2 text-xl font-semibold text-slate-950">
                    {mode === "intake" ? "信息采集" : "简历工作台"}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const freshDraft = createEmptyDraft();
                    startTransition(() => {
                      setDraft(freshDraft);
                      setActiveExperienceId(freshDraft.experiences[0]?.id ?? "");
                      setMode("intake");
                      moveToStep(0);
                      setStatus("已开始新的草稿。");
                    });
                  }}
                  className="rounded-full border border-border px-3 py-2 text-xs text-slate-500 transition hover:border-coral-deep hover:text-coral"
                >
                  新建草稿
                </button>
              </div>

              <div className="mt-6 space-y-3">
                {steps.map((step, index) => (
                  <button
                    key={step.id}
                    type="button"
                    onClick={() => moveToStep(index)}
                    className={cn(
                      "w-full rounded-[24px] border px-4 py-4 text-left transition",
                      currentStep === index
                        ? "border-coral bg-coral text-white shadow-[0_18px_50px_rgba(232,169,155,0.22)]"
                        : "border-border bg-white hover:border-coral-deep/30",
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p
                          className={cn(
                            "font-mono text-[10px] uppercase tracking-[0.26em]",
                            currentStep === index ? "text-white/70" : "text-muted",
                          )}
                        >
                          {step.kicker}
                        </p>
                        <p className="mt-2 text-base font-medium">{step.label}</p>
                        <p
                          className={cn(
                            "mt-2 text-xs leading-6",
                            currentStep === index ? "text-white/70" : "text-slate-500",
                          )}
                        >
                          {summaries[index]}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "mt-1 h-3 w-3 rounded-full",
                          completion[index] ? "bg-sage" : "bg-border",
                        )}
                      />
                    </div>
                  </button>
                ))}
              </div>
            </aside>

            <main className="rounded-[32px] border border-border bg-white p-6 shadow-[0_24px_80px_rgba(45,42,40,0.05)]">
              {mode === "intake" ? (
                <div className="space-y-6">
                  <div className="flex items-center justify-between border-b border-border pb-4">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-coral">
                        信息采集
                      </p>
                      <h2 className="mt-2 text-3xl font-semibold text-slate-950">
                        {steps[currentStep].label}
                      </h2>
                    </div>
                    <div className="rounded-full bg-[var(--color-bg)] px-4 py-2 text-xs text-slate-600">
                      {currentStep + 1} / {steps.length}
                    </div>
                  </div>

                  {currentStepId === "target" && (
                    <div className="grid gap-4 md:grid-cols-3">
                      <label className="field md:col-span-3">
                        <span>姓名</span>
                        <input
                          value={draft.personalInfo.name}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              personalInfo: {
                                ...current.personalInfo,
                                name: event.target.value,
                              },
                            }))
                          }
                          placeholder="宋哈娜"
                        />
                      </label>
                      <label className="field">
                        <span>邮箱</span>
                        <input
                          value={draft.personalInfo.email}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              personalInfo: {
                                ...current.personalInfo,
                                email: event.target.value,
                              },
                            }))
                          }
                          placeholder="zhangsan@example.com"
                        />
                      </label>
                      <label className="field">
                        <span>电话</span>
                        <input
                          value={draft.personalInfo.phone}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              personalInfo: {
                                ...current.personalInfo,
                                phone: event.target.value,
                              },
                            }))
                          }
                          placeholder="13800138000"
                        />
                      </label>
                      <label className="field">
                        <span>个人网站</span>
                        <input
                          value={draft.personalInfo.personalWebsite}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              personalInfo: {
                                ...current.personalInfo,
                                personalWebsite: event.target.value,
                              },
                            }))
                          }
                          placeholder="https://zhangsan.dev"
                        />
                      </label>
                      <label className="field">
                        <span>所在地</span>
                        <input
                          value={draft.personalInfo.location}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              personalInfo: {
                                ...current.personalInfo,
                                location: event.target.value,
                              },
                            }))
                          }
                          placeholder="北京市朝阳区"
                        />
                      </label>
                      <label className="field">
                        <span>目标公司</span>
                        <input
                          value={draft.targetRole.targetCompany}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              targetRole: {
                                ...current.targetRole,
                                targetCompany: event.target.value,
                              },
                            }))
                          }
                          placeholder="字节跳动"
                        />
                      </label>
                      <label className="field md:col-span-2">
                        <span>岗位名称</span>
                        <input
                          value={draft.targetRole.roleName}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              targetRole: {
                                ...current.targetRole,
                                roleName: event.target.value,
                              },
                            }))
                          }
                          placeholder="高级前端工程师"
                        />
                      </label>
                      <label className="field">
                        <span>城市</span>
                        <input
                          value={draft.targetRole.city}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              targetRole: {
                                ...current.targetRole,
                                city: event.target.value,
                              },
                            }))
                          }
                          placeholder="上海"
                        />
                      </label>
                      <label className="field md:col-span-2">
                        <span>岗位描述</span>
                        <textarea
                          value={draft.targetRole.jobDescription}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              targetRole: {
                                ...current.targetRole,
                                jobDescription: event.target.value,
                              },
                            }))
                          }
                          placeholder="可选。粘贴 JD 后，系统会自动提取关键信息。"
                        />
                      </label>
                    </div>
                  )}

                  {currentStepId === "education" && (
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="field">
                        <span>学校</span>
                        <input
                          value={draft.education[0].school}
                          onChange={(event) =>
                            setDraft((current) =>
                              updateEducation(current, 0, { school: event.target.value }),
                            )
                          }
                        />
                      </label>
                      <label className="field">
                        <span>学历</span>
                        <input
                          value={draft.education[0].degree}
                          onChange={(event) =>
                            setDraft((current) =>
                              updateEducation(current, 0, { degree: event.target.value }),
                            )
                          }
                        />
                      </label>
                      <label className="field">
                        <span>专业</span>
                        <input
                          value={draft.education[0].major}
                          onChange={(event) =>
                            setDraft((current) =>
                              updateEducation(current, 0, { major: event.target.value }),
                            )
                          }
                        />
                      </label>
                      <label className="field">
                        <span>毕业时间</span>
                        <input
                          value={draft.education[0].graduationYear}
                          onChange={(event) =>
                            setDraft((current) =>
                              updateEducation(current, 0, {
                                graduationYear: event.target.value,
                              }),
                            )
                          }
                        />
                      </label>
                      <label className="field md:col-span-2">
                        <span>GPA / 排名</span>
                        <input
                          value={draft.education[0].gpa}
                          onChange={(event) =>
                            setDraft((current) =>
                              updateEducation(current, 0, { gpa: event.target.value }),
                            )
                          }
                          placeholder="可选"
                        />
                      </label>
                    </div>
                  )}

                  {currentStepId === "experience" && (
                    <div className="space-y-4">
                      <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-coral">
                        社会经历
                      </p>
                      {draft.experiences
                        .filter((exp) => exp.kind === "social")
                        .map((experience, index) => {
                          const isActiveExperience = experience.id === activeExperienceId;
                          return (
                            <ExperienceCard
                              key={experience.id}
                              experience={experience}
                              index={index}
                              isActive={isActiveExperience}
                              activeExperienceId={activeExperienceId}
                              setActiveExperienceId={setActiveExperienceId}
                              setExperienceField={setExperienceField}
                              onDelete={(id) => {
                                setDraft((current) => {
                                  const next = removeExperience(current.experiences, id);
                                  if (activeExperienceId === id) {
                                    setActiveExperienceId(next[0]?.id ?? "");
                                  }
                                  return { ...current, experiences: next };
                                });
                              }}
                            />
                          );
                        })}
                      <button
                        type="button"
                        onClick={() => {
                          const next = createEmptyExperience("social");
                          setActiveExperienceId(next.id);
                          setDraft((current) => ({
                            ...current,
                            experiences: [...current.experiences, next],
                          }));
                        }}
                        className="rounded-full border border-dashed border-coral/40 px-4 py-3 text-sm text-coral transition hover:border-coral-deep"
                      >
                        + 新增社会经历
                      </button>
                    </div>
                  )}


                  {currentStepId === "skills" && (
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="field md:col-span-2">
                        <span>技能证书</span>
                        <input
                          value={draft.skills.skillTags.join(", ")}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              skills: {
                                ...current.skills,
                                skillTags: event.target.value
                                  .split(/[,\s/]+/)
                                  .map((item) => item.trim())
                                  .filter(Boolean),
                              },
                            }))
                          }
                          placeholder="SQL, Python, Figma"
                        />
                      </label>
                      <label className="field">
                        <span>证书</span>
                        <input
                          value={draft.skills.certificates}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              skills: {
                                ...current.skills,
                                certificates: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                      <label className="field">
                        <span>语言能力</span>
                        <input
                          value={draft.skills.languages}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              skills: {
                                ...current.skills,
                                languages: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                      <label className="field md:col-span-2">
                        <span>补充备注</span>
                        <textarea
                          value={draft.skills.extraNotes}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              skills: {
                                ...current.skills,
                                extraNotes: event.target.value,
                              },
                            }))
                          }
                          placeholder="可选。补充你希望模型重点强调的信息。"
                        />
                      </label>
                    </div>
                  )}

                  {currentStepId === "campus" && (
                    <div className="space-y-4">
                      <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-coral">
                        校园经历
                      </p>
                      {draft.experiences
                        .filter((exp) => exp.kind === "campus")
                        .map((experience, index) => {
                          const isActiveExperience = experience.id === activeExperienceId;
                          return (
                            <ExperienceCard
                              key={experience.id}
                              experience={experience}
                              index={index}
                              isActive={isActiveExperience}
                              activeExperienceId={activeExperienceId}
                              setActiveExperienceId={setActiveExperienceId}
                              setExperienceField={setExperienceField}
                              onDelete={(id) => {
                                setDraft((current) => {
                                  const next = removeExperience(current.experiences, id);
                                  if (activeExperienceId === id) {
                                    setActiveExperienceId(next[0]?.id ?? "");
                                  }
                                  return { ...current, experiences: next };
                                });
                              }}
                            />
                          );
                        })}
                      <button
                        type="button"
                        onClick={() => {
                          const next = createEmptyExperience("campus");
                          setActiveExperienceId(next.id);
                          setDraft((current) => ({
                            ...current,
                            experiences: [...current.experiences, next],
                          }));
                        }}
                        className="rounded-full border border-dashed border-coral/40 px-4 py-3 text-sm text-coral transition hover:border-coral-deep"
                      >
                        + 新增校园经历
                      </button>
                    </div>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
                    <div className="text-sm text-slate-500">
                      {status || "这里先收集最基本的事实信息，真正的润色会在生成后的编辑区完成。"}
                    </div>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        disabled={currentStep === 0}
                        onClick={() => moveToStep(currentStep - 1)}
                        className="rounded-full border border-border px-5 py-3 text-sm transition hover:border-coral-deep hover:text-coral disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        上一步
                      </button>
                      {currentStep < steps.length - 1 ? (
                        <button
                          type="button"
                          onClick={() => moveToStep(currentStep + 1)}
                          className="rounded-full bg-coral px-5 py-3 text-sm text-white transition hover:bg-coral-deep"
                        >
                          下一步
                        </button>
                      ) : (
                        <button
                          type="button"
                          disabled={isGenerating}
                          onClick={generateResume}
                          className="rounded-full bg-coral px-5 py-3 text-sm text-white transition hover:bg-coral-deep disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isGenerating ? "生成中..." : "生成简历"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-coral">
                        生成后编辑区
                      </p>
                      <h2 className="mt-2 text-3xl font-semibold text-slate-950">
                        分块编辑与导出
                      </h2>
                    </div>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={() => setMode("intake")}
                        className="rounded-full border border-border px-4 py-3 text-sm transition hover:border-coral-deep hover:text-coral"
                      >
                        返回采集
                      </button>
                      <button
                        type="button"
                        onClick={exportPdf}
                        className="rounded-full bg-coral px-5 py-3 text-sm text-white transition hover:bg-coral-deep"
                      >
                        下载 PDF
                      </button>
                    </div>
                  </div>
                  <ResumePreview
                    draft={draft}
                    activeBlockId={selectedBlockId}
                    onSelectBlock={setSelectedBlockId}
                    onSummaryChange={(value) =>
                      setDraft((current) => ({
                        ...current,
                        resumeSections: {
                          ...current.resumeSections,
                          summary: {
                            ...current.resumeSections.summary,
                            content: value,
                          },
                        },
                      }))
                    }
                  />
                </div>
              )}
            </main>

            <aside className="ai-sidebar max-h-[calc(100vh-10rem)] overflow-y-auto rounded-[32px] border border-border bg-surface p-5 shadow-[0_20px_70px_rgba(45,42,40,0.05)]">
              <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-coral">
                智能助手栏
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">
                {mode === "intake" ? currentAssistCopy.title : "内容改写"}
              </h2>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                {mode === "intake"
                  ? currentAssistCopy.description
                  : "请先在中间选择一个区块，再只改写这一块内容，避免覆盖你手动修改过的其他部分。"}
              </p>

              {mode === "intake" && assistMode === "material_parse" && (
                <div className="mt-4 rounded-[22px] border border-coral/30 bg-coral/20 px-4 py-3 text-sm text-coral">
                  已识别为当前步骤材料，下面的建议卡片点击后才会写回表单。
                </div>
              )}

              <div className="mt-5 space-y-3">
                {chatMessages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={cn(
                      "rounded-[24px] px-4 py-4 text-sm leading-7",
                      message.role === "assistant"
                        ? "bg-white text-slate-700"
                        : "bg-coral text-white",
                    )}
                  >
                    {message.content}
                  </div>
                ))}
              </div>

              {assistCards.length > 0 && mode === "intake" && (
                <div className="mt-5 space-y-3">
                  {assistCards.map((card) => (
                    <button
                      key={card.id}
                      type="button"
                      onClick={() => applyCard(card)}
                      className="w-full rounded-[22px] border border-border bg-white px-4 py-3 text-left text-sm transition hover:border-coral-deep hover:text-coral"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium">{card.label}</p>
                        <span className="rounded-full bg-[var(--color-bg)] px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-coral">
                          一键应用
                        </span>
                      </div>
                      <p className="mt-2 text-xs leading-6 text-slate-500">{card.value}</p>
                      {card.reason && (
                        <p className="mt-2 text-xs leading-6 text-slate-400">
                          {card.reason}
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {mode === "edit" && selectedBlockId !== "skills" && (
                <div className="mt-5 rounded-[24px] border border-border bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.26em] text-coral">
                    当前选中
                  </p>
                  <p className="mt-2 text-sm font-medium text-slate-950">
                    {getSelectedBlockLabel(selectedBlockId)}
                  </p>
                  <label className="field mt-4">
                    <span>改写目标</span>
                    <textarea
                      value={rewriteIntent}
                      onChange={(event) => setRewriteIntent(event.target.value)}
                      placeholder="例如：更具体、更少套话、和岗位要求更贴近。"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={isRewriting}
                    onClick={rewriteSelectedBlock}
                    className="mt-4 w-full rounded-full bg-coral px-4 py-3 text-sm text-white transition hover:bg-coral-deep disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isRewriting ? "改写中..." : "改写当前区块"}
                  </button>
                </div>
              )}

              {mode === "intake" && isChatLoading && (
                <div className="mt-4 rounded-[24px] bg-white px-4 py-4 text-sm leading-7 text-slate-500">
                  正在思考...
                </div>
              )}

              {mode === "intake" ? (
                <div className="mt-5">
                  <label className="field">
                    <span>{currentAssistCopy.promptLabel}</span>
                    <textarea
                      value={chatInput}
                      disabled={isChatLoading}
                      onChange={(event) => setChatInput(event.target.value)}
                      placeholder={currentAssistCopy.placeholder}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={isChatLoading}
                    onClick={sendAssist}
                    className="mt-4 w-full rounded-full bg-coral px-4 py-3 text-sm text-white transition hover:bg-coral-deep disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isChatLoading ? "思考中..." : "发送"}
                  </button>
                </div>
              ) : (
                <div className="mt-5 rounded-[24px] border border-dashed border-coral/30 px-4 py-4 text-sm leading-7 text-slate-500">
                  建议按区块逐个修改。优先改“个人概述”和单条项目要点，最稳妥。
                </div>
              )}

              <div className="mt-5 rounded-[24px] bg-coral-deep px-4 py-4 text-sm leading-7 text-white">
                {status || "草稿已自动保存到云端，刷新页面后也会保留当前进度。"}
              </div>

              <AiConfigPanel
                onTestConnection={async () => {
                  setTestingConnection(true);
                  setStatus("正在测试 AI 连接...");
                  try {
                    const res = await fetch("/api/test-connection", { method: "POST" });
                    const data = await res.json();
                    setStatus(data.ok ? "连接成功" : `连接失败: ${data.error}`);
                  } catch {
                    setStatus("连接测试失败");
                  } finally {
                    setTestingConnection(false);
                  }
                }}
                testing={testingConnection}
              />
            </aside>
          </div>
      </section>
    </div>
  );
}

export function ResumeStudio() {
  const isHydrated = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );

  const [ready, setReady] = useState(false);
  const [initialDraft, setInitialDraft] = useState<ResumeDraft>(createEmptyDraft());

  useEffect(() => {
    if (!isHydrated) {
      setReady(true);
      return;
    }

    loadDraftFromSupabase().then((remote) => {
      if (remote) {
        setInitialDraft(remote);
        saveDraftToStorage(remote);
      } else {
        setInitialDraft(loadDraftFromStorage() ?? createEmptyDraft());
      }
      setReady(true);
    });
  }, [isHydrated]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="text-sm text-slate-500">正在加载草稿...</div>
      </div>
    );
  }

  return (
    <ResumeStudioContent
      key={isHydrated ? "hydrated" : "ssr"}
      initialDraft={initialDraft}
      persistDraft={isHydrated}
    />
  );
}
