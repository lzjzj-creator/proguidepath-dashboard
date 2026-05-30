export type StepId = "target" | "campus" | "education" | "experience" | "skills";

export type PersonalInfo = {
  name: string;
  email: string;
  phone: string;
  personalWebsite: string;
  location: string;
};

export type TargetRole = {
  roleName: string;
  targetCompany: string;
  city: string;
  jobDescription: string;
};

export type EducationEntry = {
  id: string;
  school: string;
  major: string;
  degree: string;
  graduationYear: string;
  gpa: string;
};

export type ExperienceEntry = {
  id: string;
  kind: "campus" | "social";
  category: "project" | "competition" | "internship";
  name: string;
  role: string;
  timeframe: string;
  responsibility: string;
  tools: string;
  result: string;
};

export type SkillsProfile = {
  skillTags: string[];
  certificates: string;
  languages: string;
  extraNotes: string;
};

export type ResumeSummarySection = {
  title: string;
  content: string;
};

export type ResumeEducationSection = {
  id: string;
  school: string;
  degreeLine: string;
  detailLine: string;
};

export type ResumeProjectSection = {
  id: string;
  heading: string;
  timeframe: string;
  bullets: string[];
};

export type ResumeSkillSection = {
  groups: Array<{
    title: string;
    items: string[];
  }>;
};

export type ResumeSections = {
  summary: ResumeSummarySection;
  education: ResumeEducationSection[];
  projects: ResumeProjectSection[];
  skills: ResumeSkillSection;
};

export type ResumeDraft = {
  personalInfo: PersonalInfo;
  targetRole: TargetRole;
  education: EducationEntry[];
  experiences: ExperienceEntry[];
  skills: SkillsProfile;
  summary: string;
  roleKeywords: string[];
  resumeSections: ResumeSections;
};

export type RoleParseResponse = {
  keywords: string[];
  responsibilities: string[];
  toneHint: string;
};

export type AssistMode = "material_parse" | "qa";

export type AssistInputKind = "material" | "question";

export type ChatAssistCard = {
  id: string;
  label: string;
  field: string;
  value: string;
  reason?: string;
  scopeStep: StepId;
};

export type ChatAssistRequest = {
  stepId: StepId;
  question: string;
  inputKind?: AssistInputKind;
  activeExperienceId?: string;
  currentDraft: ResumeDraft;
  currentFieldValues: Record<string, string | string[]>;
};

export type ChatAssistResponse = {
  mode: AssistMode;
  reply: string;
  cards: ChatAssistCard[];
};

export type ResumeRewriteRequest = {
  sectionId: string;
  original: string;
  intent: string;
  targetRole: TargetRole;
};

export type ResumeRewriteResponse = {
  content: string;
};

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
