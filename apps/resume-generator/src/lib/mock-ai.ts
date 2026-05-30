import { createEmptyResumeSections, hydrateDraft } from "@/lib/resume";
import type {
  ChatAssistCard,
  ChatAssistRequest,
  ChatAssistResponse,
  ResumeDraft,
  ResumeRewriteRequest,
  ResumeRewriteResponse,
  RoleParseResponse,
} from "@/lib/types";

const unique = (values: string[]) => [...new Set(values.filter(Boolean))];
const FIELD_SEPARATOR = " · ";
const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "by",
  "for",
  "from",
  "in",
  "into",
  "of",
  "on",
  "or",
  "the",
  "to",
  "with",
]);

const compactText = (value: string) => value.replace(/\s+/g, " ").trim();

const stripTrailingPunctuation = (value: string) =>
  compactText(value).replace(/[.,;:!?]+$/, "");

const sentenceCase = (value: string) => {
  if (!value) {
    return "";
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
};

const joinWithAnd = (values: string[]) => {
  if (values.length <= 1) {
    return values[0] ?? "";
  }

  if (values.length === 2) {
    return `${values[0]} and ${values[1]}`;
  }

  return `${values.slice(0, -1).join(", ")}, and ${values.at(-1)}`;
};

const tokenize = (value: string) =>
  unique(
    value
      .split(/[\s,.;:/|]+/)
      .map((item) => item.trim())
      .filter((item) => item.length >= 2),
  );

const normalizeKeyword = (value: string) => {
  const cleaned = stripTrailingPunctuation(value).replace(/\s+/g, " ");

  if (!cleaned) {
    return "";
  }

  if (/^[A-Z0-9-]+$/.test(cleaned)) {
    return cleaned;
  }

  return cleaned
    .split(" ")
    .map((part) => {
      if (/^[A-Z0-9-]+$/.test(part)) {
        return part;
      }

      if (/^[a-z]{2,6}$/.test(part) && part === part.toLowerCase()) {
        return part;
      }

      const lower = part.toLowerCase();
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
};

const extractKeywordPhrases = (value: string) =>
  unique(
    value
      .split(/[\n,;|]+|\s+\band\b\s+/i)
      .map((item) => stripTrailingPunctuation(item).replace(/\s+/g, " ").trim())
      .filter((item) => {
        if (item.length < 3) {
          return false;
        }

        const words = item.toLowerCase().split(/\s+/);
        return words.some((word) => !STOP_WORDS.has(word));
      })
      .map(normalizeKeyword),
  );

const roleKeywordDefaults = (roleName: string) => {
  if (roleName.toLowerCase().includes("product")) {
    return ["用户研究", "需求分析", "PRD 撰写", "原型迭代", "跨团队协作"];
  }

  if (roleName.toLowerCase().includes("data")) {
    return ["SQL", "数据看板", "数据清洗", "洞察分析", "业务汇报"];
  }

  if (roleName.toLowerCase().includes("operation")) {
    return ["活动策划", "增长运营", "内容执行", "数据分析", "跨部门协同"];
  }

  if (
    roleName.toLowerCase().includes("engineer") ||
    roleName.toLowerCase().includes("developer")
  ) {
    return ["编码实现", "API 开发", "问题排查", "功能交付", "性能优化"];
  }

  return ["沟通表达", "主人翁意识", "执行力", "学习速度"];
};

const normalizeResponsibility = (value: string) => {
  const cleaned = stripTrailingPunctuation(value);

  if (!cleaned) {
    return "";
  }

  if (
    /^(led|owned|drove|built|managed|created|launched|supported)\b/i.test(cleaned)
  ) {
    return `${sentenceCase(cleaned)}.`;
  }

  return `Led ${cleaned}.`;
};

const normalizeResult = (value: string) => {
  const cleaned = stripTrailingPunctuation(value);

  if (!cleaned) {
    return "";
  }

  return `${sentenceCase(cleaned)}.`;
};

const splitMaterialLines = (value: string) =>
  value
    .split(/[\n。；;]+/)
    .map((item) => compactText(item))
    .filter(Boolean);

const toCard = (
  scopeStep: ChatAssistCard["scopeStep"],
  label: string,
  field: string,
  value: string,
  reason?: string,
): ChatAssistCard | null => {
  const trimmed = compactText(value);

  if (!trimmed) {
    return null;
  }

  return {
    id: `${scopeStep}-${field}-${trimmed.slice(0, 24)}`,
    label,
    field,
    value: trimmed,
    reason,
    scopeStep,
  };
};

const dedupeCards = (cards: Array<ChatAssistCard | null>) => {
  const seen = new Set<string>();

  return cards.filter((card): card is ChatAssistCard => {
    if (!card) {
      return false;
    }

    const key = `${card.scopeStep}:${card.field}:${card.value}`;
    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
};

const looksLikeMaterial = (request: ChatAssistRequest) => {
  if (request.inputKind === "material") {
    return true;
  }

  const question = request.question.trim();
  const lineCount = question.split(/\n/).filter(Boolean).length;
  const looksLikeQuestion = /[?？]$/.test(question) || /^怎么|如何|能不能|是否/.test(question);

  if (looksLikeQuestion && question.length < 80 && lineCount <= 1) {
    return false;
  }

  if (lineCount >= 2 || question.length >= 60) {
    return true;
  }

  return /职责|要求|负责|任职|岗位|专业|GPA|项目|实习|技能|证书|语言|校园|课题/i.test(question);
};

const hasFilledCurrentFields = (request: ChatAssistRequest) =>
  Object.values(request.currentFieldValues ?? {}).some((value) => {
    if (Array.isArray(value)) {
      return value.some((item) => compactText(item).length > 0);
    }

    return typeof value === "string" && compactText(value).length > 0;
  });

const buildMaterialFromCurrentFields = (request: ChatAssistRequest) => {
  const fields = request.currentFieldValues ?? {};

  if (request.stepId === "target") {
    return [
      fields.roleName ? `职位：${fields.roleName}` : "",
      fields.targetCompany ? `公司：${fields.targetCompany}` : "",
      fields.city ? `城市：${fields.city}` : "",
      fields.jobDescription ? `岗位描述：${fields.jobDescription}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (request.stepId === "education") {
    return [
      fields.school ? `学校：${fields.school}` : "",
      fields.major ? `专业：${fields.major}` : "",
      fields.degree ? `学历：${fields.degree}` : "",
      fields.graduationYear ? `毕业时间：${fields.graduationYear}` : "",
      fields.gpa ? `GPA：${fields.gpa}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (request.stepId === "experience" || request.stepId === "campus") {
    return [
      fields.name ? `经历：${fields.name}` : "",
      fields.role ? `角色：${fields.role}` : "",
      fields.timeframe ? `时间：${fields.timeframe}` : "",
      fields.responsibility ? `职责：${fields.responsibility}` : "",
      fields.tools ? `工具：${fields.tools}` : "",
      fields.result ? `结果：${fields.result}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  const skillTags = Array.isArray(fields.skillTags)
    ? fields.skillTags.filter((item) => compactText(item).length > 0).join(", ")
    : "";

  return [
    skillTags ? `技能：${skillTags}` : "",
    fields.certificates ? `证书：${fields.certificates}` : "",
    fields.languages ? `语言：${fields.languages}` : "",
    fields.extraNotes ? `补充说明：${fields.extraNotes}` : "",
  ]
    .filter(Boolean)
    .join("\n");
};

const pickFirstMatch = (value: string, patterns: RegExp[]) => {
  for (const pattern of patterns) {
    const match = value.match(pattern);
    if (match?.[1]) {
      return compactText(match[1]);
    }
  }

  return "";
};

const summarizeJobDescription = (value: string) =>
  splitMaterialLines(value).slice(0, 3).join("；");

const parseTargetCards = (request: ChatAssistRequest) => {
  const text = request.question;
  const roleName =
    pickFirstMatch(text, [
      /(?:职位|岗位|招聘岗位|岗位名称)[:：]?\s*([^\n，。,；;]{2,24})/i,
      /(?:应聘|招聘)\s*([^\n，。,；;]{2,24})/i,
    ]) || request.currentDraft.targetRole.roleName;
  const targetCompany = pickFirstMatch(text, [
    /(?:公司|企业|品牌)[:：]?\s*([^\n，。,；;]{2,24})/i,
  ]);
  const city = pickFirstMatch(text, [
    /(?:工作地点|城市|地点)[:：]?\s*([^\n，。,；;]{2,16})/i,
  ]);
  const summary = summarizeJobDescription(text);
  const keywords = unique(extractKeywordPhrases(text).slice(0, 8));

  return dedupeCards([
    toCard("target", "建议填写岗位名称", "targetRole.roleName", roleName, "从 JD 标题或岗位描述提炼"),
    toCard("target", "建议填写目标公司", "targetRole.targetCompany", targetCompany, "从 JD 文本识别公司信息"),
    toCard("target", "建议填写工作城市", "targetRole.city", city, "从 JD 文本识别地点"),
    toCard("target", "建议回填岗位描述摘要", "targetRole.jobDescription", summary, "保留 JD 重点，压缩成便于保存的摘要"),
    toCard("target", "建议整理岗位关键词", "targetRole.jobDescription", keywords.join(" / "), "可先作为岗位描述里的关键词参考"),
  ]);
};

const parseEducationCards = (request: ChatAssistRequest) => {
  const text = request.question;
  const school = pickFirstMatch(text, [
    /(?:学校|院校|毕业院校)[:：]?\s*([^\n，。,；;]{2,40})/i,
  ]);
  const major = pickFirstMatch(text, [/(?:专业|方向)[:：]?\s*([^\n，。,；;]{2,40})/i]);
  const degree = pickFirstMatch(text, [/(?:学历|学位)[:：]?\s*([^\n，。,；;]{2,20})/i]);
  const graduationYear = pickFirstMatch(text, [
    /((?:20\d{2}|19\d{2})\s*(?:年)?(?:毕业|毕业时间)?)/,
  ]);
  const gpa = pickFirstMatch(text, [/(GPA[^，。\n；;]{0,16})/i, /(绩点[^，。\n；;]{0,16})/]);

  return dedupeCards([
    toCard("education", "建议填写学校", "education.0.school", school, "从教育原始信息提炼"),
    toCard("education", "建议填写专业", "education.0.major", major, "从教育原始信息提炼"),
    toCard("education", "建议填写学历", "education.0.degree", degree, "从教育原始信息提炼"),
    toCard("education", "建议填写毕业时间", "education.0.graduationYear", graduationYear, "保留你提供的时间表达"),
    toCard("education", "建议填写 GPA / 排名", "education.0.gpa", gpa, "只回填文本里明确出现的信息"),
  ]);
};

const parseExperienceCards = (request: ChatAssistRequest) => {
  const text = request.question;
  const lines = splitMaterialLines(text);
  const name =
    pickFirstMatch(text, [/(?:项目|实习|比赛|经历)[:：]?\s*([^\n，。,；;]{2,40})/i]) ||
    lines[0] ||
    "";
  const role = pickFirstMatch(text, [/(?:角色|岗位|职责角色)[:：]?\s*([^\n，。,；;]{2,24})/i]);
  const timeframe = pickFirstMatch(text, [
    /((?:20\d{2}[./-]\d{1,2}\s*[-~至到]+\s*(?:20\d{2}[./-]\d{1,2}|至今)))/,
    /((?:20\d{2}\s*年[^，。\n]{0,16}(?:至今|结束|毕业)))/,
  ]);
  const responsibility =
    pickFirstMatch(text, [/(?:负责|职责|做了什么)[:：]?\s*([^\n]{6,120})/i]) ||
    lines.find((line) => /负责|设计|完成|推进|搭建|分析|调研/.test(line)) ||
    "";
  const tools =
    pickFirstMatch(text, [/(?:工具|技术栈|方法)[:：]?\s*([^\n]{2,80})/i]) ||
    unique(tokenize(text)).slice(0, 6).join(", ");
  const result =
    pickFirstMatch(text, [/(?:结果|成果|产出)[:：]?\s*([^\n]{2,100})/i]) ||
    lines.find((line) => /提升|完成|落地|上线|增长|优化|获奖/.test(line)) ||
    "";

  return dedupeCards([
    toCard("experience", "建议填写经历名称", "experiences.active.name", name, "从原始描述提炼标题"),
    toCard("experience", "建议填写角色", "experiences.active.role", role, "从原始描述提炼角色"),
    toCard("experience", "建议填写时间", "experiences.active.timeframe", timeframe, "保留文本里的时间范围"),
    toCard("experience", "建议填写职责", "experiences.active.responsibility", responsibility, "优先保留你原始动作表述"),
    toCard("experience", "建议填写工具 / 方法", "experiences.active.tools", tools, "提炼文本中的工具或方法"),
    toCard("experience", "建议填写结果", "experiences.active.result", result, "只回填文本里出现的结果"),
  ]);
};

const parseSkillsCards = (request: ChatAssistRequest) => {
  const text = request.question;
  const skillTags = unique(
    [
      ...extractKeywordPhrases(text),
      ...tokenize(text).filter((item) => item.length <= 20),
    ].slice(0, 10),
  ).join(", ");
  const certificates = pickFirstMatch(text, [/(?:证书|认证)[:：]?\s*([^\n]{2,80})/i]);
  const languages = pickFirstMatch(text, [/(?:语言|外语)[:：]?\s*([^\n]{2,80})/i]);
  const extraNotes = splitMaterialLines(text)
    .filter((line) => !/证书|认证|语言|外语/.test(line))
    .slice(0, 2)
    .join("；");

  return dedupeCards([
    toCard("skills", "建议填写技能标签", "skills.skillTags", skillTags, "提炼可被验证的工具或技能"),
    toCard("skills", "建议填写证书", "skills.certificates", certificates, "只回填明确提到的证书"),
    toCard("skills", "建议填写语言能力", "skills.languages", languages, "只回填明确提到的语言能力"),
    toCard("skills", "建议填写补充备注", "skills.extraNotes", extraNotes, "保留适合面试展开的补充信息"),
  ]);
};

export const parseRoleHeuristics = (
  roleName: string,
  jobDescription: string,
): RoleParseResponse => {
  const keywords = extractKeywordPhrases(jobDescription).slice(0, 10);

  return {
    keywords: keywords.length > 0 ? keywords : roleKeywordDefaults(roleName),
    responsibilities: unique(
      extractKeywordPhrases(jobDescription)
        .filter((item) => item.length >= 4)
        .slice(0, 5),
    ),
    toneHint: roleName
      ? `简历内容应围绕 ${roleName} 展开，语气保持具体、克制、真实。`
      : "面向校招场景，保持语气具体、克制、真实。",
  };
};

export const generateResumeHeuristics = (draft: ResumeDraft): ResumeDraft => {
  const safeDraft = hydrateDraft(draft);
  const parsedRole = parseRoleHeuristics(
    safeDraft.targetRole.roleName,
    safeDraft.targetRole.jobDescription,
  );
  const resumeSections = createEmptyResumeSections();
  const firstEducation = safeDraft.education[0];
  const schoolLabel = firstEducation?.school || "校园背景";
  const majorLabel = firstEducation?.major || "相关专业";
  const keywordFocus = parsedRole.keywords.slice(0, 3);

  const summary = `${schoolLabel}${majorLabel ? `${FIELD_SEPARATOR}${majorLabel}` : ""}。正在申请${
    safeDraft.targetRole.roleName || "校招岗位"
  }。${
    keywordFocus.length > 0
      ? `能将课程训练与校园实践整理为清晰的简历表达，重点突出${joinWithAnd(
          keywordFocus,
        )}。`
      : "能将课程训练与校园实践整理为清晰的简历表达。"
  }`;

  resumeSections.summary = {
    title: "个人概述",
    content: summary,
  };

  resumeSections.education = safeDraft.education
    .filter((item) => item.school || item.major || item.degree)
    .map((item) => ({
      id: item.id,
      school: item.school || "教育经历",
      degreeLine: [item.degree, item.major].filter(Boolean).join(FIELD_SEPARATOR),
      detailLine: [item.graduationYear, item.gpa].filter(Boolean).join(FIELD_SEPARATOR),
    }));

  const skillGroups: { title: string; items: string[] }[] = [];

  if (safeDraft.skills.skillTags.length > 0) {
    skillGroups.push({ title: "技能", items: safeDraft.skills.skillTags });
  }

  const certItems: string[] = [];
  if (safeDraft.skills.certificates.trim()) {
    certItems.push(safeDraft.skills.certificates.trim());
  }
  if (safeDraft.skills.languages.trim()) {
    certItems.push(safeDraft.skills.languages.trim());
  }
  if (certItems.length > 0) {
    skillGroups.push({ title: "证书", items: certItems });
  }

  if (safeDraft.skills.extraNotes.trim()) {
    skillGroups.push({ title: "补充备注", items: [safeDraft.skills.extraNotes.trim()] });
  }

  resumeSections.skills = { groups: skillGroups };

  return {
    ...safeDraft,
    summary,
    roleKeywords: parsedRole.keywords,
    resumeSections,
  };
};

export const buildChatAssistHeuristics = (
  request: ChatAssistRequest,
): ChatAssistResponse => {
  const role = request.currentDraft.targetRole.roleName || "目标岗位";
  const fallbackMaterial = hasFilledCurrentFields(request)
    ? buildMaterialFromCurrentFields(request)
    : "";
  const requestForParsing =
    !looksLikeMaterial(request) && fallbackMaterial
      ? {
          ...request,
          question: fallbackMaterial,
          inputKind: "material" as const,
        }
      : request;
  const materialMode = looksLikeMaterial(requestForParsing);

  if (materialMode) {
    const cards =
      requestForParsing.stepId === "target"
        ? parseTargetCards(requestForParsing)
        : requestForParsing.stepId === "education"
          ? parseEducationCards(requestForParsing)
          : requestForParsing.stepId === "experience" || requestForParsing.stepId === "campus"
            ? parseExperienceCards(requestForParsing)
            : parseSkillsCards(requestForParsing);

    return {
      mode: "material_parse",
      reply:
        cards.length > 0
          ? "已识别为当前步骤的原始材料，下面是可一键应用的建议卡片。"
          : "我识别到你贴的是原始材料，但其中可直接回填到当前步骤的字段还不够明确。",
      cards,
    };
  }

  if (request.stepId === "target") {
    return {
      mode: "qa",
      reply: `先把目标岗位写具体。如果你有 JD，可以直接贴进来，我会先帮你提炼适合 ${role} 的建议卡片。`,
      cards: [],
    };
  }

  if (request.stepId === "education") {
    return {
      mode: "qa",
      reply: "教育经历先保留真实、简洁、可核验的信息。把学校、专业、学历、毕业时间或 GPA 贴给我，我会帮你拆成可回填卡片。",
      cards: [],
    };
  }

  if (request.stepId === "experience" || request.stepId === "campus") {
    return {
      mode: "qa",
      reply: `把原始描述贴进来，我会按当前经历卡生成适合 ${role} 的回填建议。尽量拆成"做了什么、用了什么、结果如何"。`,
      cards: [],
    };
  }

  return {
    mode: "qa",
    reply: "把技能清单、证书、语言能力或补充说明贴进来，我会整理成当前步骤可直接应用的建议卡片。",
    cards: [],
  };
};

export const rewriteBlockHeuristics = ({
  original,
  intent,
  targetRole,
}: ResumeRewriteRequest): ResumeRewriteResponse => {
  const role = targetRole.roleName || "目标岗位";
  const cleaned = stripTrailingPunctuation(original);
  const intentHint = intent
    ? `，并按照「${intent}」的方向调整`
    : "，并进一步补强事实证明、压缩表述冗余";

  return {
    content: `${cleaned}${intentHint}，使内容与${role}的匹配度更高。`,
  };
};
