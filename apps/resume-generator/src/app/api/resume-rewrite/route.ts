import { NextRequest, NextResponse } from "next/server";
import { rewriteBlock } from "@/lib/server-ai";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const result = await rewriteBlock(body);
  return NextResponse.json(result);
}
