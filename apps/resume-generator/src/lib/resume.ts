import type {
  ChatAssistCard,
  EducationEntry,
  ExperienceEntry,
  ResumeDraft,
  ResumeSections,
} from "@/lib/types";

const STEP_SEPARATOR = " · ";

const makeId = (prefix: string) =>
  `${prefix}-${Math.random().toString(36).slice(2, 10)}`;

export const createEmptyEducation = (): EducationEntry => ({
  id: makeId("edu"),
  school: "",
  major: "",
  degree: "",
  graduationYear: "",
  gpa: "",
});

export const createEmptyExperience = (
  kind?: "campus" | "social",
): ExperienceEntry => ({
  id: makeId("exp"),
  kind: kind ?? "campus",
  category: "project",
  name: "",
  role: "",
  timeframe: "",
  responsibility: "",
  tools: "",
  result: "",
});

export const createEmptyResumeSections = (): ResumeSections => ({
  summary: {
    title: "个人概述",
    content: "",
  },
  education: [],
  projects: [],
  skills: {
    groups: [],
  },
});

export const createEmptyDraft = (): ResumeDraft => ({
  personalInfo: { name: "", email: "", phone: "", personalWebsite: "", location: "" },
  targetRole: {
    roleName: "",
    targetCompany: "",
    city: "",
    jobDescription: "",
  },
  education: [createEmptyEducation()],
  experiences: [createEmptyExperience()],
  skills: {
    skillTags: [],
    certificates: "",
    languages: "",
    extraNotes: "",
  },
  summary: "",
  roleKeywords: [],
  resumeSections: createEmptyResumeSections(),
});

const hasText = (value: string) => value.trim().length > 0;

export const getStepCompletion = (draft?: ResumeDraft | null): boolean[] => {
  if (!draft?.targetRole) return [false, false, false, false, false];

  return [
    hasText(draft.targetRole.roleName),
    draft.education?.some((item) => hasText(item.school) && hasText(item.degree)) ?? false,
    draft.experiences?.some(
      (item) => item.kind === "campus" && hasText(item.name) && hasText(item.responsibility),
    ) ?? false,
    draft.experiences?.some(
      (item) => item.kind === "social" && hasText(item.name) && hasText(item.responsibility),
    ) ?? false,
    (draft.skills?.skillTags?.length ?? 0) > 0,
  ];
};

export const getStepSummaries = (draft?: ResumeDraft | null): string[] => {
  if (!draft?.targetRole) {
    return ["未设置目标岗位", "未设置教育经历", "0 段校园经历", "0 段社会经历", "未设置技能标签"];
  }

  const education = (draft.education ?? []).find(
    (item) => hasText(item.school) || hasText(item.major),
  );
  const socialCount = (draft.experiences ?? []).filter(
    (item) => item.kind === "social" && hasText(item.name),
  ).length;
  const campusCount = (draft.experiences ?? []).filter(
    (item) => item.kind === "campus" && hasText(item.name),
  ).length;
  const skillTags = draft.skills?.skillTags ?? [];

  return [
    [draft.targetRole.roleName, draft.targetRole.city]
      .filter(Boolean)
      .join(STEP_SEPARATOR) || "未设置目标岗位",
    education
      ? [education.school, education.major].filter(Boolean).join(STEP_SEPARATOR)
      : "未设置教育经历",
    `${campusCount} 段校园经历`,
    `${socialCount} 段社会经历`,
    skillTags.length
      ? `${skillTags.length} 个技能标签`
      : "未设置技能标签",
  ];
};

export const upsertExperience = (
  experiences: ExperienceEntry[],
  experience: ExperienceEntry,
) => {
  const index = experiences.findIndex((item) => item.id === experience.id);

  if (index === -1) {
    return [...experiences, experience];
  }

  return experiences.map((item) => (item.id === experience.id ? experience : item));
};

export const removeExperience = (
  experiences: ExperienceEntry[],
  experienceId: string,
) => {
  const next = experiences.filter((item) => item.id !== experienceId);
  return next.length > 0 ? next : [createEmptyExperience()];
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

const resolveExperienceIndex = (
  draft: ResumeDraft,
  activeExperienceId?: string,
) => {
  if (!activeExperienceId) {
    return 0;
  }

  const index = draft.experiences.findIndex((item) => item.id === activeExperienceId);
  return index === -1 ? 0 : index;
};

export const applyAssistCardToDraft = (
  draft: ResumeDraft,
  card: Pick<ChatAssistCard, "field" | "value">,
  options?: { activeExperienceId?: string },
): ResumeDraft => {
  const { field, value: rawValue } = card;

  if (field.startsWith("targetRole.")) {
    const key = field.replace("targetRole.", "") as keyof ResumeDraft["targetRole"];
    return {
      ...draft,
      targetRole: {
        ...draft.targetRole,
        [key]: rawValue,
      },
    };
  }

  if (field.startsWith("education.0.")) {
    const key = field.replace("education.0.", "") as keyof EducationEntry;
    return updateEducation(draft, 0, { [key]: rawValue });
  }

  if (field.startsWith("experiences.active.")) {
    const key = field.replace("experiences.active.", "") as keyof ExperienceEntry;
    const experienceIndex = resolveExperienceIndex(draft, options?.activeExperienceId);
    const next = {
      ...draft.experiences[experienceIndex],
      [key]: rawValue,
    };

    return {
      ...draft,
      experiences: upsertExperience(draft.experiences, next),
    };
  }

  if (field === "skills.skillTags") {
    const tags = Array.isArray(rawValue)
      ? rawValue
      : String(rawValue)
          .split(/[,\s/]+/)
          .map((item) => item.trim())
          .filter(Boolean);
    return {
      ...draft,
      skills: {
        ...draft.skills,
        skillTags: tags,
      },
    };
  }

  if (field.startsWith("skills.")) {
    const key = field.replace("skills.", "") as keyof ResumeDraft["skills"];
    return {
      ...draft,
      skills: {
        ...draft.skills,
        [key]: rawValue,
      },
    };
  }

  return draft;
};

export const hydrateDraft = (input: Partial<ResumeDraft> | null | undefined): ResumeDraft => {
  const base = createEmptyDraft();

  if (!input) return base;

  return {
    ...base,
    ...input,
    personalInfo: {
      ...base.personalInfo,
      ...input.personalInfo,
    },
    targetRole: {
      ...base.targetRole,
      ...input.targetRole,
    },
    education:
      input.education && input.education.length > 0
        ? input.education.map((entry) => ({ ...createEmptyEducation(), ...entry }))
        : base.education,
    experiences:
      input.experiences && input.experiences.length > 0
        ? input.experiences.map((entry) => ({
            ...createEmptyExperience(),
            ...entry,
          }))
        : base.experiences,
    skills: {
      ...base.skills,
      ...input.skills,
    },
    resumeSections: {
      ...base.resumeSections,
      ...input.resumeSections,
      summary: {
        ...base.resumeSections.summary,
        ...input.resumeSections?.summary,
      },
      education: input.resumeSections?.education ?? base.resumeSections.education,
      projects: input.resumeSections?.projects ?? base.resumeSections.projects,
      skills: input.resumeSections?.skills ?? base.resumeSections.skills,
    },
    roleKeywords: input.roleKeywords ?? base.roleKeywords,
  };
};
