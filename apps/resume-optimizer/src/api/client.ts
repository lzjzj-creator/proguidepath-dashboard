import type {
  ApplicationStrategyRequestPayload,
  ApplicationStrategyResponse,
  AnalyticsResponse,
  CareerPlanResponse,
  InterviewPrepareRequestPayload,
  InterviewPrepareResponse,
  JobExtractResponse,
  JobProfile,
  MatchResponse,
  OcrResponse,
  ResumeOptimizeResponse,
  ResumeTemplateLayout,
  StructuredResumePayload,
  TemplateStyleSettings,
  TemplateWorkspaceData,
  ResumeTemplateSummary,
  StructuredResume,
  SuggestionsResponse,
} from "../types";

const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "").replace(/\/api$/, "");
const DEFAULT_TIMEOUT_MS = 45_000;
const OCR_TIMEOUT_MS = 95_000;
const MATCH_TIMEOUT_MS = 95_000;
const OPTIMIZE_TIMEOUT_MS = 120_000;
const IS_DEV = import.meta.env.DEV;
const DEFAULT_USER_ROLE = String(import.meta.env.VITE_USER_ROLE || "student").trim().toLowerCase();
const DEFAULT_USER_ID = String(import.meta.env.VITE_USER_ID || `${DEFAULT_USER_ROLE}-demo`).trim();

export type UserRole = "student" | "admin" | "operator";

function currentUserHeaders(roleOverride?: UserRole) {
  const role = roleOverride || ((DEFAULT_USER_ROLE === "admin" || DEFAULT_USER_ROLE === "operator") ? DEFAULT_USER_ROLE : "student");

  return {
    "X-User-Id": DEFAULT_USER_ID,
    "X-User-Role": role,
  };
}

type ApiErrorInfo = {
  message: string;
  stage?: string;
  detail?: unknown;
  retryable?: boolean;
};

export class ApiRequestError extends Error {
  endpoint: string;
  stage: string;
  durationMs: number;
  isTimeout: boolean;
  detail?: unknown;
  retryable: boolean;
  status?: number;

  constructor(
    message: string,
    options: {
      endpoint: string;
      stage: string;
      durationMs: number;
      isTimeout?: boolean;
      detail?: unknown;
      retryable?: boolean;
      status?: number;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.endpoint = options.endpoint;
    this.stage = options.stage;
    this.durationMs = options.durationMs;
    this.isTimeout = Boolean(options.isTimeout);
    this.detail = options.detail;
    this.retryable = options.retryable ?? true;
    this.status = options.status;
  }
}

async function readError(resp: Response): Promise<ApiErrorInfo> {
  const text = await resp.text().catch(() => "");
  if (!text) return { message: resp.statusText };

  try {
    const parsed = JSON.parse(text);
    const detail = parsed.detail;
    if (detail && typeof detail === "object") {
      const payload = detail as Record<string, unknown>;
      return {
        message: String(payload.message || parsed.message || resp.statusText),
        stage: typeof payload.stage === "string" ? payload.stage : undefined,
        detail: payload.detail,
        retryable: typeof payload.retryable === "boolean" ? payload.retryable : true,
      };
    }
    return { message: String(detail || parsed.message || text) };
  } catch {
    return { message: text };
  }
}

async function requestWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMessage: string,
  timeoutMs = DEFAULT_TIMEOUT_MS,
) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const startedAt = performance.now();

  logRequest("start", { endpoint: url });

  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers: {
        ...currentUserHeaders(),
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });
    const durationMs = performance.now() - startedAt;
    (response as Response & { _durationMs?: number })._durationMs = durationMs;
    logRequest("success", {
      endpoint: url,
      status: response.status,
      durationMs,
    });
    return response;
  } catch (err: any) {
    const durationMs = performance.now() - startedAt;
    if (err?.name === "AbortError") {
      logRequest("failure", { endpoint: url, durationMs, error: timeoutMessage });
      throw new ApiRequestError(timeoutMessage, {
        endpoint: url,
        stage: endpointToStage(url),
        durationMs,
        isTimeout: true,
        retryable: true,
      });
    }

    const message = "后端服务暂时不可用，请确认服务已启动后重试。";
    logRequest("failure", { endpoint: url, durationMs, error: err?.message || message });
    throw new ApiRequestError(message, {
      endpoint: url,
      stage: endpointToStage(url),
      durationMs,
      retryable: true,
    });
  } finally {
    window.clearTimeout(timer);
  }
}

async function buildApiHttpError(resp: Response, endpoint: string, stage: string) {
  const reason = await readError(resp);
  const message = `${stage}失败：${resp.status} ${reason.message}`.trim();
  const durationMs = (resp as Response & { _durationMs?: number })._durationMs ?? 0;
  logRequest("failure", { endpoint, status: resp.status, durationMs, error: `[${stage}] ${message}` });
  return new ApiRequestError(message, {
    endpoint,
    stage: reason.stage || stage,
    durationMs,
    detail: reason.detail,
    retryable: reason.retryable,
    status: resp.status,
  });
}

function endpointToStage(endpoint: string) {
  if (endpoint.includes("/api/ocr")) return "简历解析";
  if (endpoint.includes("/api/match")) return "岗位匹配";
  if (endpoint.includes("/api/job/extract-requirements")) return "岗位解析";
  if (endpoint.includes("/api/resume/optimize")) return "简历优化";
  if (endpoint.includes("/api/application/strategy")) return "投递策略";
  if (endpoint.includes("/api/interview/prepare")) return "面试准备";
  if (endpoint.includes("/api/career/plan")) return "职业规划";
  if (endpoint.includes("/api/analytics/recruitment")) return "招聘分析";
  return "请求处理";
}

function logRequest(
  type: "start" | "success" | "failure",
  payload: { endpoint: string; durationMs?: number; status?: number; error?: string },
) {
  if (!IS_DEV) return;

  const duration = typeof payload.durationMs === "number" ? ` ${Math.round(payload.durationMs)}ms` : "";
  const status = typeof payload.status === "number" ? ` status=${payload.status}` : "";
  const prefix = `[api:${type}]`;

  if (type === "failure") {
    console.warn(`${prefix} ${payload.endpoint}${status}${duration}`, payload.error || "");
    return;
  }

  console.info(`${prefix} ${payload.endpoint}${status}${duration}`);
}

export async function ocrResume(file: File): Promise<OcrResponse> {
  const form = new FormData();
  form.append("file", file);

  const resp = await requestWithTimeout(
    "/api/ocr",
    {
      method: "POST",
      body: form,
    },
    "简历解析超时，请稍后重试。若连续两次超时，建议更换更清晰的 PDF 或检查后端模型服务。",
    OCR_TIMEOUT_MS,
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/ocr", "简历解析");
  }
  return (await resp.json()) as OcrResponse;
}

export async function generateSuggestions(resumeId: number): Promise<SuggestionsResponse> {
  const resp = await requestWithTimeout(
    "/api/suggestions",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeId }),
    },
    "AI 建议生成超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/suggestions", "建议生成");
  }
  return (await resp.json()) as SuggestionsResponse;
}

export async function extractJobProfile(description: string): Promise<JobExtractResponse> {
  const resp = await requestWithTimeout(
    "/api/job/extract-requirements",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobDescription: description }),
    },
    "岗位信息提取超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/job/extract-requirements", "岗位解析");
  }
  const data = await resp.json();
  return {
    title: data.title || "",
    must_haves: normalizeRequirementList(data.must_haves),
    nice_to_haves: normalizeRequirementList(data.nice_to_haves),
    keywords: Array.isArray(data.keywords) ? data.keywords.map(String).filter(Boolean) : [],
    experience_years: data.experience_years || "",
    responsibilities: String(data.responsibilities || ""),
    risk_flags: normalizeTextList(data.risk_flags),
    extraction_status: String(data.extraction_status || ""),
    fallback_reason: String(data.fallback_reason || ""),
    source_text_preview: String(data.source_text_preview || ""),
  };
}

export async function matchResume(
  resumeId: number,
  jobProfile: JobProfile,
): Promise<MatchResponse> {
  const resp = await requestWithTimeout(
    "/api/match",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeId, jobProfile }),
    },
    "岗位匹配超时，请重试一次；如果仍然超时，建议稍后再试。",
    MATCH_TIMEOUT_MS,
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/match", "岗位匹配");
  }
  return (await resp.json()) as MatchResponse;
}

export async function optimizeResumeForJob(
  resumeId: number,
  jobProfile: JobProfile,
  model: string,
): Promise<ResumeOptimizeResponse> {
  const resp = await requestWithTimeout(
    "/api/resume/optimize",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resumeId,
        model,
        jobDescription: jobProfile.responsibilities,
        jobRequirements: {
          title: jobProfile.title,
          responsibilities: jobProfile.responsibilities,
          must_haves: jobProfile.must_haves,
          nice_to_haves: jobProfile.nice_to_haves,
          keywords: jobProfile.keywords,
          experience_years: jobProfile.experience_years,
        },
      }),
    },
    "根据岗位优化简历超时，请稍后重试。",
    OPTIMIZE_TIMEOUT_MS,
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/resume/optimize", "简历优化");
  }
  const data = await resp.json();
  return normalizeOptimization(data, resumeId, jobProfile.title, model);
}

export async function batchMatch(
  resumeIds: number[],
  jobProfile: JobProfile,
): Promise<MatchResponse[]> {
  const resp = await requestWithTimeout(
    "/api/batch-match",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeIds, jobProfile }),
    },
    "批量匹配超时，请减少候选人数量后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/batch-match", "批量匹配");
  }
  return (await resp.json()) as MatchResponse[];
}

export async function structureResumeData(resumeData: Record<string, unknown>): Promise<StructuredResumePayload> {
  const resp = await requestWithTimeout(
    "/api/resume/structure",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeData }),
    },
    "排版简历结构化超时，请稍后重试。",
    OPTIMIZE_TIMEOUT_MS,
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/resume/structure", "排版结构化");
  }

  const data = await resp.json();
  return {
    structuredResume: normalizeStructuredResume(data?.structuredResume || {}),
    warnings: normalizeTextList(data?.warnings),
    missingFields: normalizeTextList(data?.missingFields),
    completeness: String(data?.completeness || "partial"),
  };
}

export async function getResumeTemplates(): Promise<ResumeTemplateSummary[]> {
  const resp = await requestWithTimeout(
    "/api/resume/templates",
    {
      method: "GET",
    },
    "模板列表加载超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/resume/templates", "模板列表");
  }

  const data = await resp.json();
  if (!Array.isArray(data)) return [];
  return data
    .map((item) => normalizeResumeTemplateSummary(item))
    .filter((item) => item.id && item.name);
}

export function createDefaultTemplateStyleSettings(): TemplateStyleSettings {
  return {
    themeColor: "#2f6f73",
    fontFamily: '"Noto Serif SC", "Microsoft YaHei", "PingFang SC", Georgia, serif',
    lineHeight: 1.6,
    baseFontSize: 12,
    sectionTitleSize: 15,
    nameSize: 30,
    pagePadding: 17,
    sectionGap: 12,
    entryGap: 8,
    showIcons: true,
    centerHeader: false,
    denseMode: false,
  };
}

export function createEmptyTemplateWorkspaceData(): TemplateWorkspaceData {
  return {
    profile: {
      name: "",
      title: "",
      phone: "",
      email: "",
      city: "",
      website: "",
      github: "",
      media: "",
      photo: "",
      target: "",
      summary: "",
    },
    education: [],
    experience: [],
    projects: [],
    skills: [],
    certificates: [],
    custom: [],
  };
}

function normalizeResumeTemplateSummary(item: unknown): ResumeTemplateSummary {
  const template = item && typeof item === "object" ? item as Record<string, unknown> : {};
  const scene = firstNonEmptyString(template.scene, template.category, template.track);
  const tone = firstNonEmptyString(template.tone, template.style, template.variant);
  const accent = firstNonEmptyString(template.accent, template.accentColor, template.themeColor);
  const source = firstNonEmptyString(template.source, template.provider, template.origin);
  const sourceUrl = firstNonEmptyString(template.sourceUrl, template.source_url, template.url, template.href);
  const license = firstNonEmptyString(template.license, template.licenseText, template.rights);

  return {
    id: String(template.id || template.templateId || ""),
    name: String(template.name || template.title || ""),
    scene: scene || undefined,
    tone: tone || undefined,
    accent: accent || undefined,
    layout: normalizeTemplateLayout(template.layout || template.layoutType || template.templateLayout),
    styleVariant: firstNonEmptyString(template.styleVariant, template.style_variant, template.variant) || undefined,
    suitableRoles: normalizeTemplateRoles(template.suitableRoles ?? template.roles ?? template.scenes),
    source: source || undefined,
    sourceUrl: sourceUrl || undefined,
    license: license || undefined,
  };
}

export async function exportResumePdf(payload: {
  templateId: string;
  structuredResume: StructuredResume;
  filename?: string;
}): Promise<Blob> {
  const resp = await requestWithTimeout(
    "/api/resume/export-pdf",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "PDF 导出超时，请稍后重试。",
    OPTIMIZE_TIMEOUT_MS,
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/resume/export-pdf", "PDF 导出");
  }

  return await resp.blob();
}

export async function getRecruitmentAnalytics(role: UserRole = "admin"): Promise<AnalyticsResponse> {
  const resp = await requestWithTimeout(
    "/api/analytics/recruitment",
    {
      method: "GET",
      headers: currentUserHeaders(role),
    },
    "招聘分析数据加载超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/analytics/recruitment", "招聘分析");
  }
  return normalizeAnalytics(await resp.json());
}

export async function generateCareerPlan(payload: {
  major: string;
  grade: string;
  skills: string[];
  experience: string;
  targetCity: string;
  interests: string[];
}): Promise<CareerPlanResponse> {
  const resp = await requestWithTimeout(
    "/api/career/plan",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "职业规划生成超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/career/plan", "职业规划");
  }
  return (await resp.json()) as CareerPlanResponse;
}

export async function generateApplicationStrategy(
  payload: ApplicationStrategyRequestPayload,
): Promise<ApplicationStrategyResponse> {
  const resp = await requestWithTimeout(
    "/api/application/strategy",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "投递策略生成超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/application/strategy", "投递策略");
  }
  return (await resp.json()) as ApplicationStrategyResponse;
}

export async function generateInterviewPrepare(
  payload: InterviewPrepareRequestPayload,
): Promise<InterviewPrepareResponse> {
  const resp = await requestWithTimeout(
    "/api/interview/prepare",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "面试准备生成超时，请稍后重试。",
  );

  if (!resp.ok) {
    throw await buildApiHttpError(resp, "/api/interview/prepare", "面试准备");
  }
  return (await resp.json()) as InterviewPrepareResponse;
}

function normalizeRequirementList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "requirement" in item) {
        return String((item as { requirement?: unknown }).requirement || "");
      }
      return "";
    })
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeOptimization(
  data: any,
  resumeId: number,
  jobTitle: string,
  model: string,
): ResumeOptimizeResponse {
  const optimized = data?.optimized_resume || {};
  const sections = Array.isArray(optimized.sections) ? optimized.sections : [];
  const keywordItems = Array.isArray(data?.keywords_to_add) ? data.keywords_to_add : [];
  const matched = Array.isArray(data?.matched_requirements) ? data.matched_requirements : [];
  const risks = Array.isArray(data?.risk_warnings) ? data.risk_warnings : [];
  const warnings = normalizeTextList(data?.structuredResumeWarnings);
  const missingFields = normalizeTextList(data?.structuredResumeMissingFields);
  const completeness = String(data?.structuredResumeCompleteness || "");
  const fallbackStatus = String(data?.fallback_status || data?.fallbackStatus || "");
  const aiError = String(data?.ai_error || data?.aiError || "");
  const coverageRaw = data?.coverage && typeof data.coverage === "object" ? data.coverage : {};
  const skippedModules = Array.isArray(data?.skippedModules)
    ? data.skippedModules
    : Array.isArray(data?.skipped_modules)
      ? data.skipped_modules
      : [];
  const beforeAfterSource = Array.isArray(data?.beforeAfterGroups)
    ? data.beforeAfterGroups
    : Array.isArray(data?.beforeAfterComparison)
      ? data.beforeAfterComparison
      : [];
  const finalResumeText = String(data?.finalResumeText || data?.final_resume_text || "").trim();
  const finalResumeSections = Array.isArray(data?.finalResumeSections)
    ? data.finalResumeSections
    : Array.isArray(data?.final_resume_sections)
      ? data.final_resume_sections
      : [];
  const normalizeModule = (section: any) => ({
    moduleName: section.name || section.moduleName || "简历模块",
    originalContent: section.before || section.originalContent || "",
    optimizedContent: section.after || section.optimizedContent || "",
    changeReason: normalizeTextList(section.reasons || section.changes).join("；") || section.reason || section.changeReason || "",
    addedKeywords: keywordItems
      .filter((item: any) => !item?.usage || String(item.usage).includes(section.name || section.moduleName || ""))
      .map((item: any) => String(item.keyword || item))
      .filter(Boolean),
    matchedRequirements: normalizeTextList(section.matched_requirements || section.matchedRequirements),
    riskWarnings: normalizeTextList(section.riskWarnings || section.risk_warnings),
    skippedReason: String(section.skippedReason || section.skipped_reason || ""),
    evidence: normalizeTextList(section.evidence || section.resumeEvidence || section.resume_evidence),
    status: String(
      section.status
        || ((section.skippedReason || section.skipped_reason)
          ? "skipped"
          : ((section.after || section.optimizedContent) && (section.after || section.optimizedContent) !== (section.before || section.originalContent))
            ? "optimized"
            : "skipped"),
    ),
  });
  const hasRenderableModules = sections.length > 0 || finalResumeSections.length > 0 || Boolean(finalResumeText);
  const sectionsLookLikeFallback = sections.some((section: any) =>
    String(section?.after || "")
      .includes("当前无法生成完整改写结果"),
  );
  const isFallback = Boolean(
    fallbackStatus && fallbackStatus !== "none"
      || aiError
      || sectionsLookLikeFallback,
  );
  const fallbackReason = String(
    aiError
      || data?.errorStage
      || (isFallback ? "本次返回的是 AI 失败后的兜底建议，不是完整润色结果。" : ""),
  );
  return {
    resumeId,
    jobTitle: optimized.target_title || jobTitle,
    model,
    overallSummary: optimized.summary || data?.overallSummary || data?.summary || "已生成岗位定制简历优化建议。",
    beforeScore: data?.beforeScore,
    afterScore: data?.afterScore,
    modules: sections.map(normalizeModule),
    keywordSuggestions: keywordItems.map((item: any) => String(item.keyword || item)).filter(Boolean),
    requirementMatches: matched.map((item: any) => ({
      requirement: String(item.requirement || ""),
      status: String(item.status || ""),
      evidence: String(item.resume_evidence || item.evidence || ""),
    })),
    riskWarnings: risks.map((item: any) => String(item.risk || item.reason || item)).filter(Boolean),
    isFallback,
    fallbackReason,
    hasRenderableModules,
    warnings,
    missingFields,
    structuredResumeCompleteness: completeness || (isFallback ? "partial" : "complete"),
    structuredResume: data?.structuredResume ? normalizeStructuredResume(data.structuredResume) : undefined,
    optimizedStructure: data?.optimizedStructure
      ? normalizeStructuredResume(data.optimizedStructure)
      : data?.optimized_structure
        ? normalizeStructuredResume(data.optimized_structure)
        : undefined,
    coverage: {
      totalModules: Number(coverageRaw.totalModules ?? coverageRaw.total_modules ?? sections.length),
      optimizedModules: Number(coverageRaw.optimizedModules ?? coverageRaw.optimized_modules ?? sections.length),
      skippedModules: Number(coverageRaw.skippedModules ?? coverageRaw.skipped_modules ?? skippedModules.length),
    },
    skippedModules: skippedModules.map((item: any) => ({
      moduleName: String(item.moduleName || item.name || "未命名模块"),
      reason: String(item.reason || item.skippedReason || item.skipped_reason || ""),
      originalContent: String(item.originalContent || item.before || ""),
    })),
    beforeAfterGroups: beforeAfterSource.map(normalizeModule),
    finalResumeText,
    finalResumeSections: finalResumeSections
      .map((item: any) => ({
        title: String(item?.title || item?.name || "").trim(),
        content: String(item?.content || item?.text || "").trim(),
      }))
      .filter((item: { title: string; content: string }) => item.title && item.content),
    recognitionMode: String(data?.recognitionMode || ""),
    layoutConfidence: Number(data?.layoutConfidence ?? 0),
    layoutWarnings: normalizeTextList(data?.layoutWarnings),
    normalizedBlocks: Array.isArray(data?.normalizedBlocks)
      ? data.normalizedBlocks.map((item: any) => ({
        key: String(item?.key || "").trim(),
        name: String(item?.name || "").trim(),
        content: String(item?.content || "").trim(),
        items: Array.isArray(item?.items)
          ? item.items.map((entry: any) => ({
            title: String(entry?.title || "").trim(),
            content: String(entry?.content || "").trim(),
          }))
          : [],
      })).filter((item: { key: string; name: string; content: string }) => item.key && item.name && item.content)
      : [],
    templateReady: Boolean(data?.templateReady ?? data?.template_ready ?? data?.structuredResume ?? sections.length),
    rawResult: data && typeof data === "object" ? data : undefined,
  };
}

function normalizeTextList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item || "").trim()).filter(Boolean);
}

function normalizeTemplateRoles(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean);
  if (typeof value === "string") {
    return value
      .split(/[\/|,，、]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function normalizeTemplateLayout(value: unknown): ResumeTemplateLayout | undefined {
  const layout = String(value || "").trim().toLowerCase();
  switch (layout) {
    case "cn-campus-single":
    case "cn-campus-double":
      return layout;
    default:
      return undefined;
  }
}

function firstNonEmptyString(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text) return text;
  }
  return "";
}

function normalizeStructuredResume(data: any): StructuredResume {
  const basics = data?.basics && typeof data.basics === "object" ? data.basics : {};
  return {
    basics: {
      name: String(basics?.name || ""),
      title: String(basics?.title || ""),
      phone: String(basics?.phone || ""),
      email: String(basics?.email || ""),
      location: String(basics?.location || ""),
      summary: String(basics?.summary || ""),
      website: String(basics?.website || basics?.portfolio || ""),
      github: String(basics?.github || ""),
      media: String(basics?.media || basics?.social || ""),
      photo: String(basics?.photo || basics?.avatar || ""),
      links: Array.isArray(basics?.links) ? basics.links.map(String).filter(Boolean) : [],
    },
    targetRole: String(data?.targetRole || data?.target_role || ""),
    education: normalizeStructuredEntries(data?.education),
    experiences: normalizeStructuredEntries(data?.experiences),
    projects: normalizeStructuredEntries(data?.projects),
    skills: normalizeStructuredSkills(data?.skills),
    certificates: normalizeTextList(data?.certificates),
    awards: normalizeTextList(data?.awards),
    selfEvaluation: String(data?.selfEvaluation || data?.self_evaluation || ""),
    metadata: data?.metadata && typeof data.metadata === "object" ? data.metadata : {},
  };
}

function normalizeStructuredEntries(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const entry = item && typeof item === "object" ? item as Record<string, unknown> : {};
    return {
      title: String(entry.title || ""),
      organization: String(entry.organization || ""),
      role: String(entry.role || ""),
      period: String(entry.period || ""),
      bullets: normalizeTextList(entry.bullets),
      coursework: normalizeTextList(entry.coursework),
    };
  });
}

function normalizeStructuredSkills(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const group = item && typeof item === "object" ? item as Record<string, unknown> : {};
    return {
      category: String(group.category || "技能"),
      items: normalizeTextList(group.items),
    };
  });
}

function normalizeAnalytics(data: any): AnalyticsResponse {
  const sources = collectSources(data);
  const metricValue = (key: string) => {
    const value = data?.[key];
    return value && typeof value === "object" && "value" in value ? value.value : value;
  };

  return {
    ...data,
    sources,
    candidateSourcesStatus: String(data?.candidateSourcesStatus || ""),
    estimatedFields: Array.isArray(data?.estimatedFields) ? data.estimatedFields.map(String) : [],
    totalResumes: Number(metricValue("totalResumes") ?? 0),
    recommendedCount: Number(metricValue("recommendedCount") ?? 0),
    averageScore: Number(metricValue("averageScore") ?? 0),
    estimatedTimeSavedHours: Number(metricValue("estimatedTimeSavedHours") ?? 0),
  };
}

function collectSources(value: unknown): AnalyticsResponse["sources"] {
  const found = new Map<string, NonNullable<AnalyticsResponse["sources"]>[number]>();

  function visit(node: unknown) {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      node.forEach(visit);
      return;
    }

    const obj = node as Record<string, any>;
    if (Array.isArray(obj.sources)) {
      for (const source of obj.sources) {
        const link = source?.link || source?.url || "";
        if (!link) continue;
        found.set(link, {
          title: String(source.title || "Public source"),
          link: String(link),
          organization: String(source.organization || source.publisher || ""),
          publishedAt: String(source.publishedAt || ""),
          accessedAt: String(source.accessedAt || ""),
        });
      }
    }

    Object.values(obj).forEach(visit);
  }

  visit(value);
  return Array.from(found.values());
}
