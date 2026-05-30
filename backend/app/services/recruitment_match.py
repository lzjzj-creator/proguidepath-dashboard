import re
from typing import Any, Dict, List, Tuple

from app.services.resume_ocr import truncate_for_llm
from app.services.siliconflow_client import SiliconFlowClient, extract_json_object


TECH_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "vue",
    "react",
    "node",
    "fastapi",
    "django",
    "flask",
    "spring",
    "mysql",
    "postgresql",
    "redis",
    "docker",
    "kubernetes",
    "linux",
    "git",
    "ai",
    "llm",
    "nlp",
    "机器学习",
    "深度学习",
    "数据分析",
    "数据看板",
    "后端",
    "前端",
    "全栈",
}

EDUCATION_KEYWORDS = ["博士", "硕士", "研究生", "本科", "学士", "大专", "985", "211"]


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_safe_text(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(f"{k}: {_safe_text(v)}" for k, v in value.items())
    return "" if value is None else str(value)


def _collect_job_terms(job_profile: dict[str, Any]) -> List[str]:
    terms: List[str] = []
    for key in ["title", "responsibilities", "experience_years"]:
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}|[\u4e00-\u9fff]{2,}", _safe_text(job_profile.get(key))))
    for key in ["must_haves", "nice_to_haves", "keywords"]:
        for item in job_profile.get(key) or []:
            terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}|[\u4e00-\u9fff]{2,}", _safe_text(item)))

    seen = set()
    normalized: List[str] = []
    for term in terms:
        value = term.strip()
        lookup = value.lower()
        if len(value) < 2 or lookup in seen:
            continue
        seen.add(lookup)
        normalized.append(value)
    return normalized


def _find_evidence(text: str, term: str, radius: int = 48) -> str:
    lower = text.lower()
    index = lower.find(term.lower())
    if index < 0:
        return ""
    start = max(0, index - radius)
    end = min(len(text), index + len(term) + radius)
    return text[start:end].replace("\n", " ").strip()


def _candidate_name(sections: Any, resume_text: str) -> str:
    text = _safe_text(sections) + "\n" + resume_text[:500]
    patterns = [
        r"(?:姓名|Name)[:：\s]*([\u4e00-\u9fff]{2,4}|[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)",
        r"^([\u4e00-\u9fff]{2,4})\s*(?:\n|$)",
        r"^([\u4e00-\u9fff]{2,4})\s+",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return "未知候选人"


def _extract_years(text: str) -> int:
    values = [int(item) for item in re.findall(r"(\d{1,2})\s*(?:年|years?)", text, re.IGNORECASE)]
    return max(values) if values else 0


def _expected_years(job_profile: dict[str, Any]) -> int:
    text = _safe_text(job_profile.get("experience_years"))
    values = [int(item) for item in re.findall(r"\d{1,2}", text)]
    return min(values) if values else 0


def _education_score(resume_text: str) -> Tuple[int, List[str]]:
    hits = [word for word in EDUCATION_KEYWORDS if word.lower() in resume_text.lower()]
    if any(word in hits for word in ["博士", "硕士", "研究生"]):
        return 90, hits
    if any(word in hits for word in ["本科", "学士", "985", "211"]):
        return 78, hits
    if hits:
        return 65, hits
    return 50, []


def rule_match_resume_to_job(
    resume_text: str,
    sections: Any,
    job_profile: dict[str, Any],
) -> Dict[str, Any]:
    full_text = f"{_safe_text(sections)}\n{resume_text}"
    explicit_profile = {
        "must_haves": job_profile.get("must_haves") or [],
        "nice_to_haves": job_profile.get("nice_to_haves") or [],
        "keywords": job_profile.get("keywords") or [],
    }
    terms = _collect_job_terms(explicit_profile) or _collect_job_terms(job_profile)
    must_haves = [_safe_text(item) for item in job_profile.get("must_haves") or [] if _safe_text(item).strip()]
    keywords = terms or sorted(TECH_KEYWORDS)

    matched_terms = [term for term in keywords if term.lower() in full_text.lower()]
    missing_terms = [term for term in keywords if term.lower() not in full_text.lower()]
    skill_denominator = max(1, min(len(keywords), 12))
    skill_score = min(100, round(len(matched_terms[:12]) / skill_denominator * 100))

    years = _extract_years(full_text)
    expected = _expected_years(job_profile)
    if expected <= 0:
        experience_score = 70 if years == 0 else min(95, 65 + years * 6)
    else:
        experience_score = min(100, round(years / expected * 100)) if years else 45

    education_score, education_hits = _education_score(full_text)

    must_have_hits = []
    must_hit_count = 0
    for requirement in must_haves:
        req_terms = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}|[\u4e00-\u9fff]{2,}", requirement)
        req_matches = [term for term in req_terms if term.lower() in full_text.lower()]
        status = "命中" if req_terms and len(req_matches) == len(req_terms) else "部分命中" if req_matches else "未命中"
        if status == "命中":
            must_hit_count += 1
        evidence = ""
        for term in req_matches:
            evidence = _find_evidence(full_text, term)
            if evidence:
                break
        must_have_hits.append(
            {
                "requirement": requirement,
                "status": status,
                "matched_keywords": req_matches,
                "evidence": evidence or "未在简历中找到直接证据",
            }
        )

    must_ratio = must_hit_count / len(must_haves) if must_haves else 0.75
    total_score = round(skill_score * 0.4 + experience_score * 0.3 + education_score * 0.2 + must_ratio * 10)
    total_score = max(0, min(100, total_score))
    recommendation = "强烈推荐" if total_score >= 85 else "推荐面试" if total_score >= 75 else "备选" if total_score >= 55 else "不匹配"

    resume_evidence = []
    for term in matched_terms[:8]:
        evidence = _find_evidence(full_text, term)
        if evidence:
            resume_evidence.append({"keyword": term, "evidence": evidence})

    strengths = [
        f"命中岗位关键词：{', '.join(matched_terms[:6])}" if matched_terms else "简历与岗位关键词重合较少，需人工复核潜力项",
        f"可识别经验年限约 {years} 年" if years else "简历未明确年限，可通过项目经历进一步确认经验深度",
    ]
    if education_hits:
        strengths.append(f"教育背景出现相关信号：{', '.join(education_hits[:4])}")

    gaps = []
    if missing_terms:
        gaps.append(f"岗位关键词缺口：{', '.join(missing_terms[:6])}")
    if expected and years < expected:
        gaps.append(f"经验年限低于岗位要求：识别到 {years or '未明确'} 年，要求 {expected}+ 年")
    if not education_hits:
        gaps.append("教育背景证据不足，建议面试前复核学历信息")

    return {
        "candidate_name": _candidate_name(sections, resume_text),
        "total_score": total_score,
        "match_score": total_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "recommendation_level": recommendation,
        "recommendation": recommendation,
        "strengths": strengths[:5],
        "gaps": gaps[:5],
        "scoring_basis": [
            {
                "dimension": "技能匹配",
                "score": skill_score,
                "basis": f"命中 {len(matched_terms)} 个岗位相关关键词",
                "evidence": matched_terms[:10],
            },
            {
                "dimension": "经验匹配",
                "score": experience_score,
                "basis": f"简历识别经验 {years or '未明确'} 年；岗位要求 {expected or '未设置'}",
                "evidence": [item["evidence"] for item in resume_evidence[:3]],
            },
            {
                "dimension": "教育匹配",
                "score": education_score,
                "basis": f"教育关键词：{', '.join(education_hits) if education_hits else '未识别到明确学历关键词'}",
                "evidence": education_hits,
            },
        ],
        "resume_evidence": resume_evidence,
        "must_have_hits": must_have_hits,
        "interview_questions": [
            {"question": "请介绍一个最能体现岗位关键技能的项目，并说明你的具体贡献。", "category": "项目真实性", "difficulty": "中"},
            {"question": f"岗位要求中仍需确认 {', '.join(missing_terms[:3]) or '核心能力'}，你有哪些相关经验？", "category": "能力缺口", "difficulty": "中"},
            {"question": "如果入职后需要在两周内交付一个可用版本，你会如何拆解任务和控制风险？", "category": "岗位胜任力", "difficulty": "难"},
        ],
        "next_step": "建议 HR 先复核关键证据，再围绕缺口进行 20-30 分钟结构化面试。",
        "algorithm": "keyword_rule_ai_hybrid",
    }


def _merge_ai_explanation(rule_result: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(rule_result)
    for key in ["strengths", "gaps", "scoring_basis", "resume_evidence", "interview_questions", "next_step"]:
        value = ai_result.get(key)
        if value:
            merged[key] = value
    if ai_result.get("candidate_name"):
        merged["candidate_name"] = ai_result["candidate_name"]
    return merged


def llm_match_resume_to_job(
    client: SiliconFlowClient,
    resume_text: str,
    sections: Any,
    job_profile: dict[str, Any],
) -> Any:
    rule_result = rule_match_resume_to_job(resume_text, sections, job_profile)
    truncated_resume = truncate_for_llm(resume_text, max_chars=14000)

    system = (
        "你是资深招聘官和岗位匹配分析师，正在帮助企业 HR 做第一轮简历筛选。"
        "后端已经用关键词和规则完成初步评分，你负责补充可解释性，不要随意改分。"
        "输出必须是 JSON，不要输出任何 JSON 之外的文字。"
    )

    user = f"""
请基于后端规则评分、岗位信息和简历证据，输出结构化 JSON 匹配报告。

要求：
- 保留规则评分中的 total_score、skill_score、experience_score、education_score 和 recommendation_level。
- candidate_name：候选人姓名，无法识别则返回“未知候选人”。
- strengths：3-5 条优势，每条要包含简历证据。
- gaps：2-5 条缺口，每条说明影响招聘决策的原因。
- scoring_basis：必须覆盖“技能匹配”“经验匹配”“教育匹配”，每项包含 dimension、score、basis、evidence。
- resume_evidence：关键证据数组，每项包含 keyword、evidence。
- interview_questions：4-6 个问题，每项包含 question、category、difficulty；category 可用“技能深挖/项目真实性/能力缺口/文化协作/岗位胜任力”，difficulty 可用“易/中/难”。
- 不要编造简历中没有的事实。证据不足时明确写“未找到直接证据”。

输出 JSON 格式如下：
{{
  "candidate_name": "候选人姓名",
  "total_score": 82,
  "match_score": 82,
  "skill_score": 86,
  "experience_score": 78,
  "education_score": 80,
  "recommendation_level": "推荐面试",
  "recommendation": "推荐面试",
  "strengths": ["..."],
  "gaps": ["..."],
  "scoring_basis": [
    {{"dimension": "技能匹配", "score": 86, "basis": "...", "evidence": ["..."]}}
  ],
  "resume_evidence": [
    {{"keyword": "Python", "evidence": "简历中的证据片段"}}
  ],
  "interview_questions": [
    {{"question": "...", "category": "技能深挖", "difficulty": "中"}}
  ],
  "next_step": "..."
}}

后端规则评分：
```json
{rule_result}
```

岗位信息：
```json
{job_profile}
```

已解析简历模块：
```json
{sections}
```

简历全文：
```text
{truncated_resume}
```
"""

    content = client.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=2600,
    )
    parsed = extract_json_object(content)
    if not isinstance(parsed, dict):
        raise ValueError("岗位匹配结果不是 JSON 对象")
    return _merge_ai_explanation(rule_result, parsed)
