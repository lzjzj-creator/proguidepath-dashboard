import { buildChatAssistHeuristics } from "@/lib/mock-ai";
import { createEmptyDraft } from "@/lib/resume";

describe("chat assist heuristics", () => {
  it("parses JD into target-only cards", () => {
    const result = buildChatAssistHeuristics({
      stepId: "target",
      question: `岗位名称：产品经理
公司：OfferLab
工作地点：上海
岗位职责：负责用户研究、需求分析和跨团队协作`,
      inputKind: "material",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().targetRole,
    });

    expect(result.mode).toBe("material_parse");
    expect(result.cards.length).toBeGreaterThan(0);
    expect(result.cards.every((card) => card.scopeStep === "target")).toBe(true);
    expect(result.cards.some((card) => card.field === "targetRole.roleName")).toBe(true);
    expect(result.cards.some((card) => card.field === "targetRole.city")).toBe(true);
  });

  it("parses education material without inventing unrelated fields", () => {
    const result = buildChatAssistHeuristics({
      stepId: "education",
      question: "学校：同济大学；专业：统计学；学历：本科；2026 年毕业；GPA 3.8/4.0",
      inputKind: "material",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().education[0],
    });

    expect(result.cards.map((card) => card.field)).toEqual(
      expect.arrayContaining([
        "education.0.school",
        "education.0.major",
        "education.0.degree",
        "education.0.graduationYear",
      ]),
    );
    expect(result.cards.some((card) => card.field.startsWith("skills."))).toBe(false);
  });

  it("uses filled education fields when the user asks for cards without pasting material again", () => {
    const draft = createEmptyDraft();
    draft.education[0] = {
      ...draft.education[0],
      school: "同济大学",
      major: "统计学",
      degree: "本科",
      graduationYear: "2026 年毕业",
      gpa: "GPA 3.8/4.0",
    };

    const result = buildChatAssistHeuristics({
      stepId: "education",
      question: "帮我拆成可回填卡片",
      inputKind: "question",
      currentDraft: draft,
      currentFieldValues: draft.education[0],
    });

    expect(result.mode).toBe("material_parse");
    expect(result.cards.map((card) => card.field)).toEqual(
      expect.arrayContaining([
        "education.0.school",
        "education.0.major",
        "education.0.degree",
        "education.0.graduationYear",
        "education.0.gpa",
      ]),
    );
  });

  it("uses active experience fields for experience parsing", () => {
    const result = buildChatAssistHeuristics({
      stepId: "experience",
      question:
        "项目：校园二手平台；角色：产品实习生；负责用户访谈和需求拆解；工具：Figma、Notion；结果：完成原型并上线内测",
      inputKind: "material",
      activeExperienceId: "exp-1",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().experiences[0],
    });

    expect(result.cards.some((card) => card.field === "experiences.active.responsibility")).toBe(
      true,
    );
    expect(result.cards.every((card) => card.scopeStep === "experience")).toBe(true);
  });

  it("falls back to qa mode for short questions", () => {
    const result = buildChatAssistHeuristics({
      stepId: "skills",
      question: "技能怎么写更像校招简历？",
      inputKind: "question",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().skills,
    });

    expect(result.mode).toBe("qa");
    expect(result.cards).toEqual([]);
  });
});
