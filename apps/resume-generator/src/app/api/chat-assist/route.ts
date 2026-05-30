import { NextRequest } from "next/server";
import { streamAssistChat } from "@/lib/server-ai";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const config = {
    apiKey: process.env.OPENAI_API_KEY ?? "",
    baseUrl: process.env.OPENAI_BASE_URL ?? "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: process.env.OPENAI_MODEL ?? "qwen3-omni-flash",
  };

  const stream = await streamAssistChat(body, config, body.history ?? []);

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
