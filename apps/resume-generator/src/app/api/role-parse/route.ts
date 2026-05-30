import { NextRequest, NextResponse } from "next/server";
import { parseRole } from "@/lib/server-ai";

export async function POST(request: NextRequest) {
  const { roleName, jobDescription } = await request.json();
  const result = await parseRole(roleName ?? "", jobDescription ?? "");
  return NextResponse.json(result);
}
