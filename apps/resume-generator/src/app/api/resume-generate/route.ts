import { NextRequest, NextResponse } from "next/server";
import { generateResume } from "@/lib/server-ai";

export async function POST(request: NextRequest) {
  const draft = await request.json();
  const result = await generateResume(draft);
  return NextResponse.json(result);
}
