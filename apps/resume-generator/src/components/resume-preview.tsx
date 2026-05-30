import type { ResumeDraft } from "@/lib/types";
import { cn } from "@/lib/cn";

type ResumePreviewProps = {
  draft: ResumeDraft;
  activeBlockId?: string;
  onSelectBlock?: (blockId: string) => void;
  onSummaryChange?: (value: string) => void;
};

const BlockButton = ({
  active,
  blockId,
  onSelect,
  children,
}: {
  active: boolean;
  blockId: string;
  onSelect?: (blockId: string) => void;
  children: React.ReactNode;
}) => (
  <div
    onClick={() => onSelect?.(blockId)}
    className={cn(
      "w-full rounded-[28px] border p-5 text-left transition",
      active
        ? "border-blue-700 bg-blue-700 text-white shadow-[0_20px_70px_rgba(37,99,235,0.18)]"
        : "border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f7fbff_100%)] text-slate-700 hover:border-blue-200 hover:bg-white",
    )}
  >
    {children}
  </div>
);

export function ResumePreview({
  draft,
  activeBlockId,
  onSelectBlock,
  onSummaryChange,
}: ResumePreviewProps) {
  return (
    <div className="space-y-5">
      <div className="rounded-[36px] border border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f2f8ff_100%)] p-8 shadow-[0_24px_90px_rgba(59,130,246,0.10)]">
        {/* Header: 姓名 + 职位 + 联系方式 */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-sky-100 pb-5">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-sky-600">
              简历工作台
            </p>
            <h3 className="mt-2 text-2xl font-semibold text-slate-950">
              {draft.personalInfo.name || "校招简历"}
            </h3>
            {draft.targetRole.roleName && (
              <p className="mt-1 text-base text-slate-600">{draft.targetRole.roleName}</p>
            )}
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
              {draft.personalInfo.email && <span>{draft.personalInfo.email}</span>}
              {draft.personalInfo.phone && <span>{draft.personalInfo.phone}</span>}
              {draft.personalInfo.personalWebsite && <span>{draft.personalInfo.personalWebsite}</span>}
              {draft.personalInfo.location && <span>{draft.personalInfo.location}</span>}
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-5">
          {/* 教育经历 */}
          {draft.resumeSections.education.length > 0 && draft.resumeSections.education.some((item) => item.school || item.degreeLine || item.detailLine) && (
            <div className="space-y-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-sky-600">教育经历</p>
              {draft.resumeSections.education.map((item) => (
                <BlockButton
                  key={item.id}
                  active={activeBlockId === "education"}
                  blockId="education"
                  onSelect={onSelectBlock}
                >
                  <div className="rounded-2xl border border-inherit p-4">
                    <p className="font-medium">{item.school}</p>
                    <p className="mt-1 text-sm opacity-80">{item.degreeLine}</p>
                    <p className="mt-2 text-xs opacity-60">{item.detailLine}</p>
                  </div>
                </BlockButton>
              ))}
            </div>
          )}

          {/* 校园经历 */}
          {draft.experiences.filter((exp) => exp.kind === "campus" && (exp.name || exp.responsibility)).length > 0 && (
            <div className="space-y-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-sky-600">校园经历</p>
              {draft.experiences
                .filter((exp) => exp.kind === "campus" && (exp.name || exp.responsibility))
                .map((exp) => (
                  <BlockButton
                    key={exp.id}
                    active={false}
                    blockId={`experience:${exp.id}`}
                    onSelect={onSelectBlock}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-medium">{exp.name || "经历"}</h4>
                        {exp.role && (
                          <p className="mt-0.5 text-sm text-slate-500">{exp.role}</p>
                        )}
                      </div>
                      {exp.timeframe && (
                        <span className="shrink-0 rounded-full bg-sky-50 px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-sky-700">
                          {exp.timeframe}
                        </span>
                      )}
                    </div>
                    <div className="mt-3 space-y-1.5">
                      {exp.responsibility && (
                        <p className="text-sm leading-6 text-slate-600">{exp.responsibility}</p>
                      )}
                      {exp.tools && (
                        <p className="text-xs text-slate-400">工具/方法：{exp.tools}</p>
                      )}
                      {exp.result && (
                        <p className="text-xs text-slate-400">结果：{exp.result}</p>
                      )}
                    </div>
                  </BlockButton>
                ))}
            </div>
          )}

          {/* 社会经历 */}
          {draft.experiences.filter((exp) => exp.kind === "social" && (exp.name || exp.responsibility)).length > 0 && (
            <div className="space-y-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-sky-600">社会经历</p>
              {draft.experiences
                .filter((exp) => exp.kind === "social" && (exp.name || exp.responsibility))
                .map((exp) => (
                  <BlockButton
                    key={exp.id}
                    active={false}
                    blockId={`experience:${exp.id}`}
                    onSelect={onSelectBlock}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-medium">{exp.name || "经历"}</h4>
                        {exp.role && (
                          <p className="mt-0.5 text-sm text-slate-500">{exp.role}</p>
                        )}
                      </div>
                      {exp.timeframe && (
                        <span className="shrink-0 rounded-full bg-sky-50 px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-sky-700">
                          {exp.timeframe}
                        </span>
                      )}
                    </div>
                    <div className="mt-3 space-y-1.5">
                      {exp.responsibility && (
                        <p className="text-sm leading-6 text-slate-600">{exp.responsibility}</p>
                      )}
                      {exp.tools && (
                        <p className="text-xs text-slate-400">工具/方法：{exp.tools}</p>
                      )}
                      {exp.result && (
                        <p className="text-xs text-slate-400">结果：{exp.result}</p>
                      )}
                    </div>
                  </BlockButton>
                ))}
            </div>
          )}

          {/* 技能证书 */}
          {draft.resumeSections.skills.groups.length > 0 && (
            <div className="space-y-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-sky-600">技能证书</p>
              <BlockButton
                active={activeBlockId === "skills"}
                blockId="skills"
                onSelect={onSelectBlock}
              >
                <div className="mt-3 space-y-4 text-sm">
                  {draft.resumeSections.skills.groups.map((group) => (
                    <div key={group.title}>
                      <p className="font-medium">{group.title}</p>
                      <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1">
                        {group.items.map((item) => (
                          <span key={item} className="opacity-75">{item}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </BlockButton>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
