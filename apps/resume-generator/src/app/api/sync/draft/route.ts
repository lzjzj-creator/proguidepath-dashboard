import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(request: NextRequest) {
  const deviceId = request.nextUrl.searchParams.get("device_id");
  if (!deviceId) {
    return NextResponse.json({ error: "device_id is required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("user_drafts")
    .select("draft_data")
    .eq("device_id", deviceId)
    .maybeSingle();

  if (error) {
    console.warn("sync/draft GET error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  if (!data) {
    return NextResponse.json({ draft: null }, { status: 404 });
  }

  return NextResponse.json({ draft: data.draft_data });
}

export async function PUT(request: NextRequest) {
  const { device_id, draft_data } = await request.json();

  const { error } = await supabase.from("user_drafts").upsert(
    { device_id, draft_data, updated_at: new Date().toISOString() },
    { onConflict: "device_id" },
  );

  if (error) {
    console.warn("sync/draft PUT error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
