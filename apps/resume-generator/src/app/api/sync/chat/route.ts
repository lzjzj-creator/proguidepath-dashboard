import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(request: NextRequest) {
  const deviceId = request.nextUrl.searchParams.get("device_id");
  if (!deviceId) {
    return NextResponse.json({ error: "device_id is required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("chat_histories")
    .select("step_id, messages")
    .eq("device_id", deviceId);

  if (error) {
    console.warn("sync/chat GET error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const history: Record<string, unknown[]> = {};
  for (const row of data ?? []) {
    history[row.step_id] = row.messages;
  }

  return NextResponse.json({ history });
}

export async function PUT(request: NextRequest) {
  const { device_id, history } = await request.json();

  const rows = Object.entries(history).map(([step_id, messages]) => ({
    device_id,
    step_id,
    messages,
    updated_at: new Date().toISOString(),
  }));

  const { error } = await supabase.from("chat_histories").upsert(rows, {
    onConflict: "device_id, step_id",
  });

  if (error) {
    console.warn("sync/chat PUT error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
