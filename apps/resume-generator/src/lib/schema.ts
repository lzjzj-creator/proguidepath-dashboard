import { z } from "zod";

export const personalInfoSchema = z.object({
  name: z.string(),
  email: z.string(),
  phone: z.string(),
  personalWebsite: z.string(),
  location: z.string(),
});

export const targetRoleSchema = z.object({
  roleName: z.string(),
  targetCompany: z.string(),
  city: z.string(),
  jobDescription: z.string(),
});

export const educationEntrySchema = z.object({
  id: z.string(),
  school: z.string(),
  major: z.string(),
  degree: z.string(),
  graduationYear: z.string(),
  gpa: z.string(),
});

export const experienceEntrySchema = z.object({
  id: z.string(),
  kind: z.enum(["campus", "social"]),
  category: z.enum(["project", "competition", "internship"]),
  name: z.string(),
  role: z.string(),
  timeframe: z.string(),
  responsibility: z.string(),
  tools: z.string(),
  result: z.string(),
});

export const skillsProfileSchema = z.object({
  skillTags: z.array(z.string()),
  certificates: z.string(),
  languages: z.string(),
  extraNotes: z.string(),
});

export const resumeSectionsSchema = z.object({
  summary: z.object({
    title: z.string(),
    content: z.string(),
  }),
  education: z.array(
    z.object({
      id: z.string(),
      school: z.string(),
      degreeLine: z.string(),
      detailLine: z.string(),
    }),
  ),
  projects: z.array(
    z.object({
      id: z.string(),
      heading: z.string(),
      timeframe: z.string(),
      bullets: z.array(z.string()),
    }),
  ),
  skills: z.object({
    groups: z.array(
      z.object({
        title: z.string(),
        items: z.array(z.string()),
      }),
    ),
  }),
});

export const resumeDraftSchema = z.object({
  personalInfo: personalInfoSchema,
  targetRole: targetRoleSchema,
  education: z.array(educationEntrySchema),
  experiences: z.array(experienceEntrySchema),
  skills: skillsProfileSchema,
  summary: z.string(),
  roleKeywords: z.array(z.string()),
  resumeSections: resumeSectionsSchema,
});

export const stepIdSchema = z.enum(["target", "campus", "education", "experience", "skills"]);

export const chatAssistCardSchema = z.object({
  id: z.string(),
  label: z.string(),
  field: z.string(),
  value: z.string(),
  reason: z.string().optional(),
  scopeStep: stepIdSchema,
});

export const chatAssistResponseSchema = z.object({
  mode: z.enum(["material_parse", "qa"]),
  reply: z.string(),
  cards: z.array(chatAssistCardSchema),
});
