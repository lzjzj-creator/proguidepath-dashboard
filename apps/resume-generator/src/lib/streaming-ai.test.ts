import { describe, it, expect } from "vitest";
import { createFallbackStream } from "./streaming-ai";
import { createEmptyDraft } from "./resume";

async function collectStream(stream: ReadableStream<Uint8Array>): Promise<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let result = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    result += decoder.decode(value, { stream: true });
  }
  return result;
}

describe("createFallbackStream", () => {
  it("emits thought, text, tool_call, done for material input", async () => {
    const stream = createFallbackStream({
      stepId: "target",
      question: "岗位名称：产品经理\n公司：字节跳动\n工作地点：上海",
      inputKind: "material",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().targetRole,
    });
    const output = await collectStream(stream);
    expect(output).toContain("event: thought");
    expect(output).toContain("event: text");
    expect(output).toContain("event: tool_call");
    expect(output).toContain('"tool":"fillTargetRole"');
    expect(output).toContain("event: done");
  });

  it("emits thought, text, done (no tool_call) for QA input", async () => {
    const stream = createFallbackStream({
      stepId: "skills",
      question: "技能怎么写更像校招简历？",
      inputKind: "question",
      currentDraft: createEmptyDraft(),
      currentFieldValues: createEmptyDraft().skills,
    });
    const output = await collectStream(stream);
    expect(output).toContain("event: thought");
    expect(output).toContain("event: text");
    expect(output).not.toContain("event: tool_call");
    expect(output).toContain("event: done");
  });
});
