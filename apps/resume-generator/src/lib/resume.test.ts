import {
  applyAssistCardToDraft,
  createEmptyDraft,
  getStepCompletion,
  getStepSummaries,
  upsertExperience,
} from "@/lib/resume";

describe("resume draft helpers", () => {
  it("creates an empty draft with four-step data scaffolding", () => {
    const draft = createEmptyDraft();

    expect(draft.targetRole.roleName).toBe("");
    expect(draft.education).toHaveLength(1);
    expect(draft.experiences).toHaveLength(1);
    expect(draft.skills.skillTags).toEqual([]);
    expect(draft.resumeSections.projects).toEqual([]);
  });

  it("tracks completion state for each wizard step", () => {
    const draft = createEmptyDraft();

    expect(getStepCompletion(draft)).toEqual([
      false, false, false, false, false,
    ]);

    draft.targetRole.roleName = "Product Manager";
    draft.education[0].school = "Fudan University";
    draft.education[0].degree = "Bachelor";
    draft.experiences[0].name = "Campus Marketplace";
    draft.experiences[0].responsibility =
      "Owned requirement breakdown and prototype planning";
    draft.skills.skillTags = ["Axure", "Figma"];

    expect(getStepCompletion(draft)).toEqual([
      true, true, true, false, true,
    ]);
  });

  it("builds terse step summaries from the current draft", () => {
    const draft = createEmptyDraft();
    draft.targetRole.roleName = "Data Analyst";
    draft.targetRole.city = "Shanghai";
    draft.education[0].school = "Tongji University";
    draft.education[0].major = "Statistics";
    draft.experiences[0].name = "User Growth Analysis";
    draft.experiences[0].result = "Improved weekly retention by 12%";
    draft.skills.skillTags = ["SQL", "Python", "Tableau"];

    expect(getStepSummaries(draft)).toEqual([
      "Data Analyst · Shanghai",
      "Tongji University · Statistics",
      "1 段校园经历",
      "0 段社会经历",
      "3 个技能标签",
    ]);
  });

  it("updates an existing experience instead of duplicating it", () => {
    const draft = createEmptyDraft();
    const firstExperienceId = draft.experiences[0].id;

    const updated = upsertExperience(draft.experiences, {
      ...draft.experiences[0],
      id: firstExperienceId,
      name: "AI Community Project",
      tools: "Cursor, Notion",
    });

    expect(updated).toHaveLength(1);
    expect(updated[0]).toMatchObject({
      id: firstExperienceId,
      name: "AI Community Project",
      tools: "Cursor, Notion",
    });
  });

  it("applies an experience assist card to the active experience only", () => {
    const draft = createEmptyDraft();
    const secondExperience = {
      ...draft.experiences[0],
      id: "exp-second",
      name: "Second",
    };
    draft.experiences = [draft.experiences[0], secondExperience];

    const updated = applyAssistCardToDraft(
      draft,
      {
        field: "experiences.active.result",
        value: "提升留存 12%",
      },
      { activeExperienceId: "exp-second" },
    );

    expect(updated.experiences[0].result).toBe("");
    expect(updated.experiences[1].result).toBe("提升留存 12%");
  });

  it("splits skill tags only when a skill card is applied", () => {
    const draft = createEmptyDraft();

    const updated = applyAssistCardToDraft(draft, {
      field: "skills.skillTags",
      value: "SQL, Python / Tableau",
    });

    expect(updated.skills.skillTags).toEqual(["SQL", "Python", "Tableau"]);
  });
});
