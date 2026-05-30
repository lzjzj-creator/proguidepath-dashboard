import { NextResponse } from "next/server";

export async function POST() {
  const apiKey = process.env.OPENAI_API_KEY;
  const baseUrl = process.env.OPENAI_BASE_URL ?? "https://dashscope.aliyuncs.com/compatible-mode/v1";
  const model = process.env.OPENAI_MODEL ?? "qwen3-omni-flash";

  if (!apiKey) {
    return NextResponse.json({ ok: false, error: "未配置 API Key" });
  }

  try {
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: "ping" }],
        max_tokens: 5,
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      return NextResponse.json({ ok: false, error: `API 响应异常 (${response.status}): ${text}` });
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json({ ok: false, error: `连接失败: ${err instanceof Error ? err.message : String(err)}` });
  }
}
