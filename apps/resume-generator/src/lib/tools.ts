import { z } from "zod";
import type { ResumeDraft } from "./types";
import { upsertExperience, createEmptyExperience } from "./resume";

// ── Argument schemas ──
export const fillTargetRoleSchema = z.object({
  roleName: z.string().optional(),
  targetCompany: z.string().optional(),
  city: z.string().optional(),
  jobDescription: z.string().optional(),
});
export const fillEducationSchema = z.object({
  school: z.string().optional(),
  major: z.string().optional(),
  degree: z.string().optional(),
  graduationYear: z.string().optional(),
  gpa: z.string().optional(),
});
export const fillExperienceSchema = z.object({
  name: z.string().optional(),
  role: z.string().optional(),
  timeframe: z.string().optional(),
  responsibility: z.string().optional(),
  tools: z.string().optional(),
  result: z.string().optional(),
});
export const fillSkillsSchema = z.object({
  skillTags: z.array(z.string()).optional(),
  certificates: z.string().optional(),
  languages: z.string().optional(),
  extraNotes: z.string().optional(),
});

// ── OpenAI-compatible tool definitions ──
export const openAiToolsDefinition = [
  {
    type: "function",
    function: {
      name: "fillTargetRole",
      description: "填写目标岗位信息：岗位名称、目标公司、城市、岗位描述",
      parameters: {
        type: "object",
        properties: {
          roleName: { type: "string" },
          targetCompany: { type: "string" },
          city: { type: "string" },
          jobDescription: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fillEducation",
      description: "填写教育经历：学校、专业、学历、毕业时间、GPA",
      parameters: {
        type: "object",
        properties: {
          school: { type: "string" },
          major: { type: "string" },
          degree: { type: "string" },
          graduationYear: { type: "string" },
          gpa: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fillExperience",
      description: "填写当前选中的项目/实习经历",
      parameters: {
        type: "object",
        properties: {
          name: { type: "string" },
          role: { type: "string" },
          timeframe: { type: "string" },
          responsibility: { type: "string" },
          tools: { type: "string" },
          result: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fillSkills",
      description: "填写技能标签、证书、语言能力、补充说明",
      parameters: {
        type: "object",
        properties: {
          skillTags: { type: "array", items: { type: "string" } },
          certificates: { type: "string" },
          languages: { type: "string" },
          extraNotes: { type: "string" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "addExperience",
      description: "新增一条空的项目/实习经历",
      parameters: { type: "object", properties: {} },
    },
  },
];

export type ToolName = "fillTargetRole" | "fillEducation" | "fillExperience" | "fillSkills" | "addExperience";
export type ToolCall = { tool: ToolName; args: Record<string, unknown> };

function pick<T extends Record<string, unknown>>(obj: T, allowed: (keyof T)[]): Partial<T> {
  const result: Partial<T> = {};
  for (const key of allowed) {
    if (obj[key] !== undefined) result[key] = obj[key];
  }
  return result;
}

export const dispatchToolCall = (
  draft: ResumeDraft,
  toolCall: ToolCall,
  activeExperienceId?: string,
): ResumeDraft => {
  switch (toolCall.tool) {
    case "fillTargetRole": {
      const p = fillTargetRoleSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      return { ...draft, targetRole: { ...draft.targetRole, ...pick(p.data, ["roleName", "targetCompany", "city", "jobDescription"]) } };
    }
    case "fillEducation": {
      const p = fillEducationSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      const edu = { ...draft.education[0], ...pick(p.data, ["school", "major", "degree", "graduationYear", "gpa"]) };
      return { ...draft, education: [edu, ...draft.education.slice(1)] };
    }
    case "fillExperience": {
      const p = fillExperienceSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      const idx = activeExperienceId ? draft.experiences.findIndex((e) => e.id === activeExperienceId) : 0;
      if (idx === -1) return draft;
      const target = draft.experiences[idx];
      if (!target) return draft;
      return { ...draft, experiences: upsertExperience(draft.experiences, { ...target, ...pick(p.data, ["name", "role", "timeframe", "responsibility", "tools", "result"]) }) };
    }
    case "fillSkills": {
      const p = fillSkillsSchema.safeParse(toolCall.args);
      if (!p.success) return draft;
      return { ...draft, skills: { ...draft.skills, ...pick(p.data, ["skillTags", "certificates", "languages", "extraNotes"]) } };
    }
    case "addExperience":
      return { ...draft, experiences: [...draft.experiences, createEmptyExperience()] };
    default:
      return draft;
  }
};
