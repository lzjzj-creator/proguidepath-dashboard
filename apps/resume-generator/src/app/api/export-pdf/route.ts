import { NextRequest, NextResponse } from "next/server";
import { renderResumeHtml } from "@/lib/resume-html";
import puppeteer from "puppeteer-core";

export async function POST(request: NextRequest) {
  try {
    const { draft } = await request.json();
    const html = renderResumeHtml(draft);

    const browser = await puppeteer.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });

    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "networkidle0" as any });
    const pdf = await page.pdf({ format: "A4", margin: { top: "0", bottom: "0", left: "0", right: "0" } });
    await browser.close();

    return new NextResponse(pdf as unknown as BodyInit, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${draft?.targetRole?.roleName || "resume"}.pdf"`,
      },
    });
  } catch (err) {
    return NextResponse.json(
      { message: `PDF 生成失败: ${err instanceof Error ? err.message : String(err)}` },
      { status: 500 },
    );
  }
}
