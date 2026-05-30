import { describe, it, expect } from "vitest";
import {
  fillTargetRoleSchema,
  fillEducationSchema,
  fillExperienceSchema,
  fillSkillsSchema,
  dispatchToolCall,
  openAiToolsDefinition,
} from "./tools";
import { createEmptyDraft } from "./resume";

describe("tool schemas", () => {
  it("validates fillTargetRole args", () => {
    expect(fillTargetRoleSchema.safeParse({ roleName: "产品经理", city: "上海" }).success).toBe(true);
  });
  it("rejects invalid fillTargetRole args", () => {
    expect(fillTargetRoleSchema.safeParse({ roleName: 123 }).success).toBe(false);
  });
  it("validates fillEducation args", () => {
    expect(fillEducationSchema.safeParse({ school: "复旦大学", major: "计算机", degree: "本科" }).success).toBe(true);
  });
  it("validates fillExperience args", () => {
    expect(fillExperienceSchema.safeParse({ name: "字节跳动实习", role: "后端开发" }).success).toBe(true);
  });
  it("validates fillSkills args", () => {
    expect(fillSkillsSchema.safeParse({ skillTags: ["Python"], certificates: "六级" }).success).toBe(true);
  });
  it("has all 5 tool definitions in openAiToolsDefinition", () => {
    expect(openAiToolsDefinition).toHaveLength(5);
  });
});

describe("dispatchToolCall", () => {
  it("applies fillTargetRole to draft", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillTargetRole", args: { roleName: "产品经理", city: "上海" } });
    expect(updated.targetRole.roleName).toBe("产品经理");
    expect(updated.targetRole.city).toBe("上海");
  });
  it("applies fillEducation to draft", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillEducation", args: { school: "复旦大学", major: "计算机" } });
    expect(updated.education[0].school).toBe("复旦大学");
    expect(updated.education[0].major).toBe("计算机");
  });
  it("applies fillExperience with activeExperienceId", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillExperience", args: { name: "字节跳动实习" } }, draft.experiences[0].id);
    expect(updated.experiences[0].name).toBe("字节跳动实习");
  });
  it("applies fillSkills with array tags", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "fillSkills", args: { skillTags: ["Python", "SQL"] } });
    expect(updated.skills.skillTags).toEqual(["Python", "SQL"]);
  });
  it("adds a new experience via addExperience", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "addExperience", args: {} });
    expect(updated.experiences).toHaveLength(2);
    expect(updated.experiences[1].id).toBeDefined();
    expect(updated.experiences[1].category).toBe("project");
  });

  it("returns draft unchanged for unknown tool name", () => {
    const draft = createEmptyDraft();
    const updated = dispatchToolCall(draft, { tool: "unknown" as any, args: {} });
    expect(updated).toBe(draft);
  });

  it("returns draft unchanged when activeExperienceId not found", () => {
    const draft = createEmptyDraft();
    draft.experiences[0].name = "Original";
    const updated = dispatchToolCall(draft, { tool: "fillExperience", args: { name: "Hacked" } }, "nonexistent-id");
    expect(updated.experiences[0].name).toBe("Original");
  });

  it("fillExperience without activeExperienceId applies to first experience", () => {
    const draft = createEmptyDraft();
    draft.experiences[0].name = "Old";
    const updated = dispatchToolCall(draft, { tool: "fillExperience", args: { name: "New" } });
    expect(updated.experiences[0].name).toBe("New");
  });
});
