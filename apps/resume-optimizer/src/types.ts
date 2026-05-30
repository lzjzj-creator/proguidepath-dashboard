export type Section = {
  name: string;
  content: string;
};

export type OcrResponse = {
  resumeId: number;
  extractedTextPreview: string;
  sections: Section[] | unknown;
  recognitionMode?: string;
  layoutConfidence?: number;
  layoutWarnings?: string[];
  normalizedBlocks?: Array<{
    key: string;
    name: string;
    content: string;
    items?: Array<{ title: string; content: string }>;
  }>;
};

export type SuggestionsItem = {
  name: string;
  issues: string[];
  recommendations: string[];
  rewrite_example?: string;
};

export type SuggestionsResponse = {
  resumeId: number;
  overall_summary: string;
  items: SuggestionsItem[];
};

export type JobProfile = {
  title: string;
  responsibilities: string;
  must_haves: string[];
  nice_to_haves: string[];
  experience_years: string;
  keywords: string[];
};

export type JobExtractResponse = {
  title?: string;
  must_haves: string[];
  nice_to_haves: string[];
  keywords: string[];
  experience_years?: string;
  responsibilities?: string;
  risk_flags?: string[];
  extraction_status?: string;
  fallback_reason?: string;
  source_text_preview?: string;
};

export type MustHaveHit = {
  requirement: string;
  status: string;
  evidence: string;
};

export type InterviewQuestion = {
  category: "technical" | "project" | "collaboration" | "risk" | string;
  difficulty: "easy" | "medium" | "hard" | string;
  question: string;
};

export type MatchResult = {
  match_score: number;
  recommendation: string;
  must_have_hits: MustHaveHit[];
  strengths: string[];
  gaps: string[];
  evidence: string[];
  interview_questions: Array<string | InterviewQuestion>;
  next_step: string;
  skill_matches?: string[];
  experience_support?: string[];
  match_reason?: string;
  interview_focus?: string[];
};

export type MatchResponse = {
  resumeId: number;
  jobProfileId: number;
  matchResultId: number;
  match_score: number;
  recommendation: string;
  result: MatchResult;
};

export type ResumeOptimizeModule = {
  moduleName: string;
  originalContent: string;
  optimizedContent: string;
  changeReason: string;
  addedKeywords: string[];
  matchedRequirements: string[];
  riskWarnings: string[];
  skippedReason?: string;
  evidence?: string[];
  status?: string;
};

export type ResumeOptimizeCoverage = {
  totalModules: number;
  optimizedModules: number;
  skippedModules: number;
};

export type ResumeOptimizeSkippedModule = {
  moduleName: string;
  reason: string;
  originalContent?: string;
};

export type ResumeOptimizeBeforeAfterGroup = {
  moduleName: string;
  originalContent: string;
  optimizedContent: string;
  changeReason: string;
  addedKeywords: string[];
  matchedRequirements: string[];
  riskWarnings: string[];
  skippedReason?: string;
  evidence?: string[];
  status?: string;
};

export type ResumeOptimizeResponse = {
  resumeId: number;
  jobTitle: string;
  model: string;
  overallSummary: string;
  beforeScore?: number;
  afterScore?: number;
  modules: ResumeOptimizeModule[];
  keywordSuggestions: string[];
  requirementMatches: Array<{
    requirement: string;
    status: string;
    evidence: string;
  }>;
  riskWarnings: string[];
  isFallback?: boolean;
  fallbackReason?: string;
  hasRenderableModules?: boolean;
  warnings?: string[];
  missingFields?: string[];
  structuredResumeCompleteness?: string;
  structuredResume?: StructuredResume;
  optimizedStructure?: StructuredResume;
  coverage?: ResumeOptimizeCoverage;
  skippedModules?: ResumeOptimizeSkippedModule[];
  beforeAfterGroups?: ResumeOptimizeBeforeAfterGroup[];
  finalResumeText?: string;
  finalResumeSections?: Array<{
    title: string;
    content: string;
  }>;
  recognitionMode?: string;
  layoutConfidence?: number;
  layoutWarnings?: string[];
  normalizedBlocks?: Array<{
    key: string;
    name: string;
    content: string;
    items?: Array<{ title: string; content: string }>;
  }>;
  templateReady?: boolean;
  rawResult?: Record<string, unknown>;
};

export type StructuredResumeEntry = {
  title: string;
  organization: string;
  role: string;
  period: string;
  bullets: string[];
  coursework?: string[];
};

export type StructuredResumeSkillGroup = {
  category: string;
  items: string[];
};

export type ResumeTemplateLayout =
  | "cn-campus-single"
  | "cn-campus-double";

export type ResumeTemplateScene =
  | "campus"
  | "technical"
  | "product"
  | "design"
  | "research"
  | "general"
  | string;

export type ResumeTemplateTone =
  | "clean"
  | "confident"
  | "professional"
  | "creative"
  | "academic"
  | "classic"
  | string;

export type StructuredResume = {
  basics: {
    name: string;
    title: string;
    phone: string;
    email: string;
    location: string;
    summary: string;
    website?: string;
    github?: string;
    media?: string;
    photo?: string;
    links: string[];
  };
  targetRole: string;
  education: StructuredResumeEntry[];
  experiences: StructuredResumeEntry[];
  projects: StructuredResumeEntry[];
  skills: StructuredResumeSkillGroup[];
  certificates: string[];
  awards: string[];
  selfEvaluation: string;
  metadata: Record<string, unknown>;
};

export type StructuredResumePayload = {
  structuredResume: StructuredResume;
  warnings: string[];
  missingFields: string[];
  completeness: string;
};

export type ResumeTemplateSummary = {
  id: string;
  name: string;
  scene?: ResumeTemplateScene;
  tone?: ResumeTemplateTone;
  accent?: string;
  layout?: ResumeTemplateLayout;
  styleVariant?: string;
  suitableRoles?: string[];
  source?: string;
  sourceUrl?: string;
  license?: string;
};

export type TemplateWorkspaceEntry = {
  id: string;
  title: string;
  organization: string;
  role: string;
  start: string;
  end: string;
  details: string;
  coursework?: string;
};

export type TemplateWorkspaceCertificate = {
  id: string;
  name: string;
  issuer: string;
  date: string;
};

export type TemplateWorkspaceCustomSection = {
  id: string;
  title: string;
  details: string;
};

export type TemplateWorkspaceProfile = {
  name: string;
  title: string;
  phone: string;
  email: string;
  city: string;
  website: string;
  github: string;
  media: string;
  photo: string;
  target: string;
  summary: string;
};

export type TemplateWorkspaceData = {
  profile: TemplateWorkspaceProfile;
  education: TemplateWorkspaceEntry[];
  experience: TemplateWorkspaceEntry[];
  projects: TemplateWorkspaceEntry[];
  skills: string[];
  certificates: TemplateWorkspaceCertificate[];
  custom: TemplateWorkspaceCustomSection[];
};

export type TemplateStyleSettings = {
  themeColor: string;
  fontFamily: string;
  lineHeight: number;
  baseFontSize: number;
  sectionTitleSize: number;
  nameSize: number;
  pagePadding: number;
  sectionGap: number;
  entryGap: number;
  showIcons: boolean;
  centerHeader: boolean;
  denseMode: boolean;
};

export type AnalyticsSource = {
  title: string;
  link: string;
  organization: string;
  publishedAt: string;
  accessedAt: string;
};

export type AnalyticsResponse = {
  dataMode?: string;
  sourcePolicy?: string;
  notes?: string;
  dashboardAudience?: string[];
  candidateSourcesStatus?: string;
  estimatedFields?: string[];
  sources?: AnalyticsSource[];
  totalUsers?: number;
  totalResumes?: number;
  recommendedCount?: number;
  averageScore?: number;
  estimatedTimeSavedHours?: number;
  aiCalls?: number;
  aiSuccessRate?: number;
  aiFailedCount?: number;
  aiFeatureBreakdown?: Array<{
    feature: string;
    total: number;
    successTotal: number;
    failedTotal: number;
  }>;
  roleBreakdown?: Array<{
    role: string;
    total: number;
  }>;
  aiCallLogs?: Array<{
    id: number;
    userId: string;
    userRole: string;
    feature: string;
    endpoint: string;
    status: string;
    durationMs: number;
    errorMessage: string;
    metadata?: Record<string, unknown>;
    createdAt: string;
  }>;
  positionEfficiency?: Array<{
    jobTitle: string;
    screened: number;
    recommended: number;
    efficiencyRate: number;
  }>;
  candidateSources?: Array<{
    source: string;
    count: number;
    recommended: number;
  }>;
  recruitmentFunnel?: Array<{
    stage: string;
    count: number;
    conversionRate: number;
  }>;
  interviewPassRate?: number;
};

export type CareerDirection = {
  direction: string;
  score: number;
  reason: string;
  gaps: string[];
  actionPlan: string[];
};

export type CareerPlanResponse = {
  recommendedDirections: CareerDirection[];
  learningRoadmap: Array<{
    stage: string;
    tasks: string[];
    outcome: string;
  }>;
  portfolioSuggestions: string[];
  cityAdvice: string;
  riskWarnings: string[];
  valuePrinciples?: string[];
};

export type ResumeContextPayload = {
  rawResumeText?: string;
  sections?: unknown;
  structuredResume?: StructuredResume;
};

export type ApplicationStrategyRequestPayload = {
  studentProfile: Record<string, unknown>;
  jobDescription: string;
  jobRequirements: Record<string, unknown>;
  matchResult: Record<string, unknown>;
  resumeId?: number;
  rawResumeText?: string;
  sections?: unknown;
  structuredResume?: StructuredResume;
};

export type ApplicationStrategyResponse = {
  shouldApply: boolean;
  priority: string;
  resumeVersionAdvice: string;
  applicationMessage: string;
  riskWarnings: string[];
  resumeContentToImprove: string[];
  bestChannels: string[];
  followUpPlan: string[];
  jobRequirementsUsed?: Record<string, unknown>;
  resumeContext?: Record<string, unknown>;
  nonFabricationReminder?: string;
};

export type InterviewPrepQuestion = {
  question: string;
  answerFramework?: string;
  scoreDimensions?: string[];
  riskPoint?: string;
};

export type InterviewPrepareRequestPayload = {
  studentProfile: Record<string, unknown>;
  jobDescription: string;
  jobRequirements: Record<string, unknown>;
  matchResult: Record<string, unknown>;
  resumeId?: number;
  rawResumeText?: string;
  sections?: unknown;
  structuredResume?: StructuredResume;
};

export type InterviewPrepareResponse = {
  highFrequencyQuestions: InterviewPrepQuestion[];
  resumeFollowUpQuestions: InterviewPrepQuestion[];
  projectQuestions: InterviewPrepQuestion[];
  behavioralQuestions: InterviewPrepQuestion[];
  answerFrameworks: Array<{
    name: string;
    usage: string;
    structure: string[];
  }>;
  scoreDimensions: string[];
  riskPoints: string[];
  practicePlan: string[];
  jobRequirementsUsed?: Record<string, unknown>;
  resumeContext?: Record<string, unknown>;
  nonFabricationReminder?: string;
};
