import type { ResumeDraft } from "@/lib/types";

const escapeHtml = (value: string) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

export const renderResumeHtml = (draft: ResumeDraft) => {
  const { resumeSections, personalInfo, targetRole, experiences } = draft;

  return `<!DOCTYPE html>
  <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <title>${escapeHtml(personalInfo.name || "简历导出")}</title>
      <style>
        @page { margin: 0; }
        body { margin: 0; font-family: "PingFang SC", "Segoe UI", "Microsoft YaHei", sans-serif; background: #fff; color: #0f172a; font-size: 11px; }
        .page { width: 794px; min-height: 1123px; margin: 0 auto; background: #ffffff; padding: 40px 44px; box-sizing: border-box; }
        h1 { margin: 6px 0 2px; font-size: 22px; font-weight: 700; }
        .position { font-size: 13px; color: #475569; margin: 2px 0 6px; }
        h2 { margin: 14px 0 6px; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #0284c7; border-bottom: 1px solid #e0e7ef; padding-bottom: 3px; }
        p { margin: 0; line-height: 1.4; }
        .meta { color: #64748b; display: flex; gap: 10px; flex-wrap: wrap; font-size: 10.5px; }
        .card { padding-top: 4px; }
        .project { margin-bottom: 8px; }
        .project-title { display: flex; justify-content: space-between; gap: 12px; font-weight: 600; font-size: 11.5px; margin-bottom: 2px; }
        .project-role { font-size: 10.5px; color: #64748b; margin-bottom: 2px; }
        .project-detail { font-size: 10px; color: #64748b; margin-top: 2px; }
        ul { margin: 2px 0 0 14px; padding: 0; }
        li { margin: 0 0 3px; line-height: 1.35; }
        .skills { display: grid; gap: 6px; }
        .skill-group strong { display: block; font-size: 10.5px; margin-bottom: 2px; }
        .skill-items { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 12px; }
        .skill-items span { font-size: 10.5px; }
      </style>
    </head>
    <body>
      <div class="page">
        <h1>${escapeHtml(personalInfo.name || "校招简历")}</h1>
        ${targetRole.roleName ? `<div class="position">${escapeHtml(targetRole.roleName)}</div>` : ""}
        <div class="meta">
          ${personalInfo.email ? `<span>${escapeHtml(personalInfo.email)}</span>` : ""}
          ${personalInfo.phone ? `<span>${escapeHtml(personalInfo.phone)}</span>` : ""}
          ${personalInfo.personalWebsite ? `<span>${escapeHtml(personalInfo.personalWebsite)}</span>` : ""}
          ${personalInfo.location ? `<span>${escapeHtml(personalInfo.location)}</span>` : ""}
        </div>

        ${resumeSections.education.length > 0 ? `
        <h2>教育经历</h2>
        <div class="card">
          ${resumeSections.education.map(
            (item) => `
            <div class="project">
              <div class="project-title">
                <span>${escapeHtml(item.school)}</span>
                <span>${escapeHtml(item.detailLine)}</span>
              </div>
              <p>${escapeHtml(item.degreeLine)}</p>
            </div>`,
          ).join("")}
        </div>` : ""}

        ${experiences.filter((exp) => exp.kind === "campus" && (exp.name || exp.responsibility)).length > 0 ? `
        <h2>校园经历</h2>
        <div class="card">
          ${experiences.filter((exp) => exp.kind === "campus" && (exp.name || exp.responsibility)).map(
            (exp) => `
            <div class="project">
              <div class="project-title">
                <span>${escapeHtml(exp.name || "经历")}</span>
                ${exp.timeframe ? `<span>${escapeHtml(exp.timeframe)}</span>` : ""}
              </div>
              ${exp.role ? `<div class="project-role">${escapeHtml(exp.role)}</div>` : ""}
              ${exp.responsibility ? `<p>${escapeHtml(exp.responsibility)}</p>` : ""}
              ${exp.tools ? `<div class="project-detail">工具/方法：${escapeHtml(exp.tools)}</div>` : ""}
              ${exp.result ? `<div class="project-detail">结果：${escapeHtml(exp.result)}</div>` : ""}
            </div>`,
          ).join("")}
        </div>` : ""}

        ${experiences.filter((exp) => exp.kind === "social" && (exp.name || exp.responsibility)).length > 0 ? `
        <h2>社会经历</h2>
        <div class="card">
          ${experiences.filter((exp) => exp.kind === "social" && (exp.name || exp.responsibility)).map(
            (exp) => `
            <div class="project">
              <div class="project-title">
                <span>${escapeHtml(exp.name || "经历")}</span>
                ${exp.timeframe ? `<span>${escapeHtml(exp.timeframe)}</span>` : ""}
              </div>
              ${exp.role ? `<div class="project-role">${escapeHtml(exp.role)}</div>` : ""}
              ${exp.responsibility ? `<p>${escapeHtml(exp.responsibility)}</p>` : ""}
              ${exp.tools ? `<div class="project-detail">工具/方法：${escapeHtml(exp.tools)}</div>` : ""}
              ${exp.result ? `<div class="project-detail">结果：${escapeHtml(exp.result)}</div>` : ""}
            </div>`,
          ).join("")}
        </div>` : ""}

        ${resumeSections.skills.groups.length > 0 ? `
        <h2>技能证书</h2>
        <div class="card skills">
          ${resumeSections.skills.groups.map(
            (group) => `
            <div class="skill-group"><strong>${escapeHtml(group.title)}</strong><div class="skill-items">${group.items.map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div></div>`,
          ).join("")}
        </div>` : ""}
      </div>
    </body>
  </html>`;
};
