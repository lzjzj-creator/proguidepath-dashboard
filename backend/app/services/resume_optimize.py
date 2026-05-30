import json
import re
from typing import Any, Dict, List, Tuple

from app.services.resume_ocr import truncate_for_llm
from app.services.siliconflow_client import SiliconFlowClient, extract_json_object


MAX_SECTION_CHARS = 480
MAX_RESUME_PREVIEW_CHARS = 900
MAX_RESUME_CONTEXT_CHARS = 5200


def extract_job_requirements(client: SiliconFlowClient, job_description: str) -> Dict[str, Any]:
    system = (
        "你是招聘需求分析师。你只能从岗位描述原文提取要求，不能扩写或杜撰。"
        "输出必须是 JSON，不要输出任何 JSON 之外的文字。"
    )
    user = f"""
请从岗位描述中提取结构化招聘要求。
要求：
- must_haves：硬性要求，来自学历、年限、技能、经验、证书、行业等明确要求。
- nice_to_haves：加分项，来自“优先/加分/熟悉/有经验更佳”等表达。
- keywords：可用于简历匹配和前端自动填充的关键词，去重后返回。
- responsibilities：岗位职责摘要，保留原文事实。
- risk_flags：岗位描述中不清晰、过宽或需要 HR 二次确认的点。
- evidence：每条要求尽量引用岗位描述中的原文证据。

输出 JSON 格式：
{{
  "title": "岗位名称，无法识别则为空字符串",
  "responsibilities": "岗位职责摘要",
  "must_haves": [
    {{"requirement": "硬性要求", "evidence": "岗位描述原文证据"}}
  ],
  "nice_to_haves": [
    {{"requirement": "加分项", "evidence": "岗位描述原文证据"}}
  ],
  "keywords": ["关键词"],
  "experience_years": "年限要求，无法识别则为空字符串",
  "risk_flags": ["需要 HR 复核的点"]
}}

岗位描述：```text
{truncate_for_llm(job_description, max_chars=10000)}
```
"""
    content = client.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=2200,
    )
    parsed = extract_json_object(content)
    if not isinstance(parsed, dict):
        raise ValueError("岗位要求提取结果不是 JSON 对象")
    return parsed


def fallback_extract_job_requirements(job_description: str) -> Dict[str, Any]:
    text = (job_description or "").strip()
    sentences = _split_job_sentences(text)
    title = _guess_job_title(sentences)
    must_haves: List[str] = []
    nice_to_haves: List[str] = []
    risk_flags: List[str] = []

    for sentence in sentences:
        normalized = _strip_section_label(sentence)
        if not normalized or _is_section_header(normalized) or normalized == title:
            continue
        if _contains_any(normalized, ["优先", "加分", "更佳", "有经验", "熟悉", "欢迎"]) and not _contains_any(
            normalized, ["不会", "不要", "不适合"]
        ):
            nice_to_haves.append(normalized)
        elif _contains_any(normalized, ["不需要", "不要", "不适合", "自行离开", "夸张"]):
            risk_flags.append(normalized)
        else:
            must_haves.append(normalized)

    if not must_haves:
        must_haves = [
            item
            for item in (_strip_section_label(sentence) for sentence in sentences)
            if item and not _is_section_header(item)
        ][:8]

    return {
        "title": title,
        "responsibilities": "；".join(must_haves[:4]) or text[:300],
        "must_haves": _requirements_with_evidence(_dedupe(must_haves)[:10]),
        "nice_to_haves": _requirements_with_evidence(_dedupe(nice_to_haves)[:6]),
        "keywords": _extract_job_keywords(text, sentences)[:16],
        "experience_years": _extract_experience_years(text),
        "risk_flags": _dedupe(risk_flags)[:6],
    }


def optimize_resume_for_job(
    client: SiliconFlowClient,
    resume_text: str,
    sections: Any,
    job_requirements: Dict[str, Any],
    timeout_seconds: int | None = None,
    max_retries: int = 0,
) -> Dict[str, Any]:
    baseline_sections = _section_items(sections, resume_text)
    baseline_structure = _build_structured_resume_skeleton(resume_text, baseline_sections, job_requirements)
    resume_context = _compact_resume_context(resume_text, baseline_sections, baseline_structure)
    job_context = _compact_json(job_requirements)
    system = (
        "你是严谨的中文简历优化顾问。你只能基于原简历已有事实优化表达。"
        "严禁虚构经历、学历、公司、项目、年限、技能、证书、成果或数字。"
        "如果岗位要求在原简历中没有事实证据，必须写入未匹配说明或风险提示，不能写进优化结果。"
        "输出必须是 JSON，不要输出任何 JSON 之外的文字。"
    )
    user = f"""
请根据原始简历和目标岗位要求，生成覆盖全部已识别模块的岗位定制简历优化结果。

硬性约束：
- 只能重写表达、调整顺序、突出已有事实，不能新增原简历没有的事实。
- 必须覆盖全部已识别模块，不要只挑 3-5 个模块。
- 如果某个模块不适合改写，也要返回该模块，并说明 skip_reason。
- 没有原简历证据的岗位要求，只能写入 matched_requirements 的“未匹配/部分匹配”或 risk_warnings。
- optimized_structure 必须仍然是可继续排版的结构化简历骨架。

输出 JSON 格式：
{{
  "summary": "本次优化的整体摘要",
  "optimized_resume": {{
    "target_title": "目标岗位",
    "summary": "适合放进排版简历的简短摘要",
    "sections": [
      {{
        "name": "模块名称",
        "module_type": "basics/education/projects/experiences/skills/certificates/summary/custom",
        "before": "原模块内容",
        "after": "优化后的模块内容；若不改写可与 before 一致",
        "reason": "为什么这样调整",
        "matched_requirements": ["命中的岗位要求"],
        "risk_warnings": ["仅当该模块存在风险时填写"],
        "evidence": ["引用原简历中的事实证据"],
        "skip_reason": "仅当不改写该模块时填写"
      }}
    ]
  }},
  "optimized_structure": {{
    "basics": {{
      "name": "姓名",
      "phone": "电话/微信",
      "email": "邮箱",
      "website": "个人网站",
      "summary": "个人摘要",
      "objective": "求职意向"
    }},
    "targetRole": "目标岗位",
    "education": [],
    "experiences": [],
    "projects": [],
    "skills": [],
    "certificates": [],
    "customSections": []
  }},
  "coverage": {{
    "totalModules": 0,
    "optimizedModules": 0,
    "skippedModules": 0
  }},
  "skipped_modules": [
    {{
      "name": "模块名称",
      "module_type": "模块类型",
      "reason": "跳过原因"
    }}
  ],
  "keywords_to_add": [
    {{
      "keyword": "关键词",
      "supporting_evidence": "原简历中的真实证据",
      "usage": "建议出现在哪个模块"
    }}
  ],
  "matched_requirements": [
    {{
      "requirement": "岗位要求",
      "status": "已匹配/部分匹配/未匹配",
      "resume_evidence": "原简历证据或未找到证据"
    }}
  ],
  "unmet_requirements": [
    {{
      "requirement": "未满足的岗位要求",
      "status": "部分匹配/未匹配",
      "resume_evidence": "原因"
    }}
  ],
  "risk_warnings": [
    {{
      "risk": "风险提示",
      "reason": "原因"
    }}
  ],
  "suggested_experiences": [
    "只能基于真实经历补充的表达建议"
  ],
  "non_fabrication_statement": "本次优化仅基于原简历已有事实，未新增任何虚构内容。",
  "final_resume_text": "完整中文简历成稿，纯文本，不要 Markdown，不要解释。",
  "final_resume_sections": [
    {{"title": "抬头", "content": "姓名、联系方式、GitHub/LinkedIn 等"}},
    {{"title": "教育背景", "content": "分节纯文本内容"}}
  ]
}}

岗位要求：```json
{job_context}
```

简历上下文：```json
{_compact_json(resume_context)}
```
"""
    content = client.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.15,
        max_tokens=3000,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    parsed = extract_json_object(content)
    if not isinstance(parsed, dict):
        raise ValueError("简历优化结果不是 JSON 对象")
    return _normalize_optimization_result(parsed, resume_text, baseline_sections, job_requirements)


def estimate_optimize_prompt_input(
    resume_text: str,
    sections: Any,
    job_requirements: Dict[str, Any],
) -> Dict[str, int]:
    baseline_sections = _section_items(sections, resume_text)
    baseline_structure = _build_structured_resume_skeleton(resume_text, baseline_sections, job_requirements)
    resume_context_json = _compact_json(_compact_resume_context(resume_text, baseline_sections, baseline_structure))
    job_context_json = _compact_json(job_requirements)
    return {
        "resume_text_chars": len(resume_text or ""),
        "resume_context_chars": len(resume_context_json),
        "job_requirements_chars": len(job_context_json),
        "estimated_input_chars": len(resume_context_json) + len(job_context_json),
    }


def fallback_optimize_resume_for_job(
    resume_text: str,
    sections: Any,
    job_requirements: Dict[str, Any],
    error: str = "",
) -> Dict[str, Any]:
    baseline_sections = _section_items(sections, resume_text)
    baseline_structure = _build_structured_resume_skeleton(resume_text, baseline_sections, job_requirements)
    target_title = str(job_requirements.get("title") or "目标岗位")
    fallback_reason = error[:300] or "AI 调用失败，已返回保守兜底结果。"
    modules = []
    skipped_modules = []
    for item in baseline_sections:
        module_type = _module_type_from_name(item["name"])
        reason = "当前使用兜底模式，保留原始事实骨架，避免在证据不足时过度改写。"
        modules.append(
            {
                "name": item["name"],
                "module_type": module_type,
                "before": item["content"],
                "after": item["content"],
                "reason": reason,
                "reasons": [reason],
                "matched_requirements": [],
                "risk_warnings": ["当前模块未做 AI 深度改写，请人工确认表达顺序。"] if item["content"] else [],
                "evidence": [item["content"][:180]] if item["content"] else [],
                "skip_reason": fallback_reason,
                "optimized": False,
                "status": "skipped",
            }
        )
        skipped_modules.append({"name": item["name"], "module_type": module_type, "reason": fallback_reason})

    result = {
        "summary": f"AI 优化暂不可用，已返回覆盖全部模块的保守排版骨架，目标岗位为{target_title}。",
        "optimized_resume": {
            "target_title": target_title,
            "summary": _build_summary_text(baseline_sections, target_title),
            "sections": modules,
        },
        "optimized_structure": baseline_structure,
        "coverage": {
            "totalModules": len(modules),
            "optimizedModules": 0,
            "skippedModules": len(modules),
            "optimizedModuleNames": [],
            "skippedModuleNames": [item["name"] for item in modules],
        },
        "skipped_modules": skipped_modules,
        "keywords_to_add": [
            {
                "keyword": keyword,
                "supporting_evidence": "请基于原简历已有事实核实后再补强表达。",
                "usage": "技能摘要、项目经历或个人总结",
            }
            for keyword in _suggest_keywords(resume_text, job_requirements)[:10]
        ],
        "matched_requirements": _build_requirement_matches([], baseline_sections, job_requirements, resume_text),
        "risk_warnings": [
            {"risk": "当前无法生成完整 AI 改写结果", "reason": fallback_reason},
            {"risk": "不要补写原简历没有的经历", "reason": "兜底结果仅保留排版骨架和保守建议，不能据此虚构事实。"},
        ],
        "fallback_status": "resume_optimize_full_skeleton_fallback",
        "retryable": True,
        "non_fabrication_statement": "本次兜底结果仅保留原始事实骨架并给出保守建议，未新增任何简历事实。",
        "template_ready": _is_template_ready(baseline_structure),
    }
    return _normalize_optimization_result(result, resume_text, baseline_sections, job_requirements)


def normalize_requirements(raw: Dict[str, Any]) -> Dict[str, Any]:
    def _list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    return {
        "title": str(raw.get("title") or ""),
        "responsibilities": str(raw.get("responsibilities") or ""),
        "must_haves": _list(raw.get("must_haves")),
        "nice_to_haves": _list(raw.get("nice_to_haves")),
        "keywords": _list(raw.get("keywords")),
        "experience_years": str(raw.get("experience_years") or ""),
        "risk_flags": _list(raw.get("risk_flags")),
    }


def _normalize_optimization_result(
    raw_result: Dict[str, Any],
    resume_text: str,
    baseline_sections: List[Dict[str, str]],
    job_requirements: Dict[str, Any],
) -> Dict[str, Any]:
    baseline_structure = _build_structured_resume_skeleton(resume_text, baseline_sections, job_requirements)
    result = dict(raw_result or {})
    optimized_resume = result.get("optimized_resume")
    if not isinstance(optimized_resume, dict):
        optimized_resume = {}

    target_title = str(
        optimized_resume.get("target_title")
        or result.get("target_title")
        or job_requirements.get("title")
        or baseline_structure.get("targetRole")
        or "目标岗位"
    )
    summary_text = str(
        result.get("summary")
        or optimized_resume.get("summary")
        or baseline_structure.get("basics", {}).get("summary")
        or _build_summary_text(baseline_sections, target_title)
    ).strip()
    optimized_resume["target_title"] = target_title
    optimized_resume["summary"] = summary_text
    full_sections, skipped_modules = _normalize_module_sections(optimized_resume.get("sections"), baseline_sections, job_requirements)
    optimized_resume["sections"] = full_sections
    result["optimized_resume"] = optimized_resume
    result["summary"] = summary_text

    coverage = _build_coverage(full_sections, result.get("coverage"))
    result["coverage"] = coverage
    result["skipped_modules"] = _normalize_skipped_modules(result.get("skipped_modules"), skipped_modules)
    result["skippedModules"] = result["skipped_modules"]

    keywords_to_add = _normalize_keywords_to_add(result.get("keywords_to_add"), resume_text, job_requirements)
    result["keywords_to_add"] = keywords_to_add
    result["keywordsToAdd"] = keywords_to_add

    matched_requirements = _build_requirement_matches(
        result.get("matched_requirements"),
        full_sections,
        job_requirements,
        resume_text,
    )
    result["matched_requirements"] = matched_requirements
    result["unmet_requirements"] = [
        item for item in matched_requirements if str(item.get("status") or "").strip() in {"未匹配", "部分匹配"}
    ]

    risk_warnings = _normalize_risk_warnings(result.get("risk_warnings"), result["unmet_requirements"], job_requirements)
    result["risk_warnings"] = risk_warnings
    result["suggested_experiences"] = _normalize_suggested_experiences(
        result.get("suggested_experiences"),
        result["unmet_requirements"],
    )
    result["non_fabrication_statement"] = str(
        result.get("non_fabrication_statement")
        or "本次优化仅基于原简历已有事实，未新增经历、学历、公司、项目、年限、技能、证书或成果。"
    )

    llm_structure = result.get("optimized_structure")
    optimized_structure = _normalize_structure_payload(llm_structure)
    if not optimized_structure:
        optimized_structure = _structure_from_module_sections(full_sections, target_title, summary_text)
    optimized_structure = _merge_structures(baseline_structure, optimized_structure)
    optimized_structure["targetRole"] = str(optimized_structure.get("targetRole") or target_title)
    optimized_structure["basics"] = optimized_structure.get("basics") if isinstance(optimized_structure.get("basics"), dict) else {}
    optimized_structure["basics"]["summary"] = str(
        optimized_structure["basics"].get("summary") or summary_text or baseline_structure.get("basics", {}).get("summary") or ""
    )
    optimized_structure["basics"]["objective"] = str(
        optimized_structure["basics"].get("objective") or target_title or baseline_structure.get("basics", {}).get("objective") or ""
    )
    result["optimized_structure"] = optimized_structure
    result["optimizedStructure"] = optimized_structure
    final_resume_sections = _normalize_final_resume_sections(
        result.get("final_resume_sections") or result.get("finalResumeSections")
    )
    final_resume_text = _normalize_final_resume_text(
        result.get("final_resume_text") or result.get("finalResumeText"),
        final_resume_sections,
        optimized_structure,
        full_sections,
        target_title,
    )
    if not final_resume_sections:
        final_resume_sections = _sections_from_final_resume_text(final_resume_text)
    result["final_resume_text"] = final_resume_text
    result["finalResumeText"] = final_resume_text
    result["final_resume_sections"] = final_resume_sections
    result["finalResumeSections"] = final_resume_sections

    template_ready = _is_template_ready(optimized_structure)
    result["template_ready"] = template_ready
    result["templateReady"] = template_ready
    _normalize_lightweight_sections(result)
    return result


def _normalize_module_sections(
    sections: Any,
    baseline_sections: List[Dict[str, str]],
    job_requirements: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    raw_sections = sections if isinstance(sections, list) else []
    prepared = []
    used_indexes: set[int] = set()

    for item in baseline_sections:
        matched_index, matched = _find_matching_section(item, raw_sections, used_indexes)
        if matched_index is not None:
            used_indexes.add(matched_index)
        prepared_section = _normalize_module_section(item, matched, job_requirements)
        prepared.append(prepared_section)

    for index, extra in enumerate(raw_sections):
        if index in used_indexes or not isinstance(extra, dict):
            continue
        name = str(extra.get("name") or extra.get("title") or "").strip()
        if not name:
            continue
        baseline = {"name": name, "content": str(extra.get("before") or extra.get("after") or extra.get("content") or "").strip()}
        prepared.append(_normalize_module_section(baseline, extra, job_requirements))

    skipped = [
        {
            "name": section["name"],
            "module_type": section["module_type"],
            "reason": section["skip_reason"],
        }
        for section in prepared
        if section["status"] == "skipped"
    ]
    return prepared, skipped


def _find_matching_section(
    baseline: Dict[str, str],
    raw_sections: List[Any],
    used_indexes: set[int],
) -> Tuple[int | None, Dict[str, Any] | None]:
    baseline_name = _slug(baseline["name"])
    baseline_type = _module_type_from_name(baseline["name"])
    fallback_match: Tuple[int | None, Dict[str, Any] | None] = (None, None)
    for index, raw in enumerate(raw_sections):
        if index in used_indexes or not isinstance(raw, dict):
            continue
        raw_name = str(raw.get("name") or raw.get("title") or "").strip()
        if raw_name and _slug(raw_name) == baseline_name:
            return index, raw
        if fallback_match[0] is None and _module_type_from_name(raw_name) == baseline_type:
            fallback_match = (index, raw)
    return fallback_match


def _normalize_module_section(
    baseline: Dict[str, str],
    raw: Dict[str, Any] | None,
    job_requirements: Dict[str, Any],
) -> Dict[str, Any]:
    name = str(baseline.get("name") or "模块").strip()
    before = str(baseline.get("content") or "").strip()
    module_type = _module_type_from_name(name)
    candidate = raw if isinstance(raw, dict) else {}
    after = str(candidate.get("after") or candidate.get("content") or "").strip()
    if not after:
        after = before
    reason = str(candidate.get("reason") or "").strip()
    if not reason:
        reason = "保留原始事实基础上优化表达与呈现顺序。"
    skip_reason = str(candidate.get("skip_reason") or "").strip()
    optimized = bool(after and after != before and not skip_reason)
    if not optimized and not skip_reason:
        skip_reason = "模型未返回该模块的可靠改写，已保留原文骨架。"
    status = "optimized" if optimized else "skipped"
    matched_names = _normalize_requirement_names(candidate.get("matched_requirements"))
    risk_texts = _normalize_string_list(candidate.get("risk_warnings"))
    evidence = _normalize_string_list(candidate.get("evidence"))
    if not evidence and before:
        evidence = [before[:220]]
    if not matched_names:
        matched_names = _match_requirement_names_from_text(after or before, job_requirements)
    return {
        "name": name,
        "module_type": module_type,
        "before": before,
        "after": after,
        "reason": reason,
        "reasons": _normalize_string_list(candidate.get("reasons")) or [reason],
        "matched_requirements": matched_names,
        "risk_warnings": risk_texts,
        "evidence": evidence,
        "skip_reason": skip_reason,
        "optimized": optimized,
        "status": status,
    }


def _build_coverage(sections: List[Dict[str, Any]], raw_coverage: Any) -> Dict[str, Any]:
    optimized_names = [item["name"] for item in sections if item.get("status") == "optimized"]
    skipped_names = [item["name"] for item in sections if item.get("status") == "skipped"]
    coverage = dict(raw_coverage or {}) if isinstance(raw_coverage, dict) else {}
    coverage["totalModules"] = len(sections)
    coverage["optimizedModules"] = len(optimized_names)
    coverage["skippedModules"] = len(skipped_names)
    coverage["optimizedModuleNames"] = optimized_names
    coverage["skippedModuleNames"] = skipped_names
    return coverage


def _normalize_skipped_modules(raw: Any, default_items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    items = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            items.append(
                {
                    "name": name,
                    "module_type": str(item.get("module_type") or _module_type_from_name(name)),
                    "reason": str(item.get("reason") or "模型未返回该模块的可靠改写，已保留原文骨架。"),
                }
            )
    if items:
        return items
    return default_items


def _normalize_keywords_to_add(raw: Any, resume_text: str, job_requirements: Dict[str, Any]) -> List[Dict[str, str]]:
    items = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                keyword = str(item.get("keyword") or "").strip()
                supporting_evidence = str(item.get("supporting_evidence") or "").strip()
                usage = str(item.get("usage") or "").strip()
            else:
                keyword = str(item or "").strip()
                supporting_evidence = ""
                usage = ""
            if keyword:
                items.append(
                    {
                        "keyword": keyword,
                        "supporting_evidence": supporting_evidence or "请确认原简历中已有对应事实后再补强表达。",
                        "usage": usage or "技能、项目或摘要模块",
                    }
                )
    if items:
        return items
    return [
        {
            "keyword": keyword,
            "supporting_evidence": "请确认原简历中已有对应事实后再补强表达。",
            "usage": "技能、项目或摘要模块",
        }
        for keyword in _suggest_keywords(resume_text, job_requirements)[:10]
    ]


def _build_requirement_matches(
    raw_matches: Any,
    sections: List[Dict[str, Any]],
    job_requirements: Dict[str, Any],
    resume_text: str,
) -> List[Dict[str, str]]:
    matches_by_name: Dict[str, Dict[str, str]] = {}
    if isinstance(raw_matches, list):
        for item in raw_matches:
            if not isinstance(item, dict):
                continue
            requirement = str(item.get("requirement") or item.get("name") or "").strip()
            if not requirement:
                continue
            matches_by_name[requirement] = {
                "requirement": requirement,
                "status": str(item.get("status") or "").strip() or "待核实",
                "resume_evidence": str(item.get("resume_evidence") or item.get("evidence") or "").strip(),
            }

    normalized = []
    for requirement in _requirement_texts(job_requirements):
        existing = matches_by_name.get(requirement)
        if existing and existing["resume_evidence"]:
            normalized.append(existing)
            continue
        status, evidence = _match_requirement_with_resume(requirement, sections, resume_text)
        normalized.append(
            {
                "requirement": requirement,
                "status": existing["status"] if existing and existing["status"] != "待核实" else status,
                "resume_evidence": existing["resume_evidence"] if existing and existing["resume_evidence"] else evidence,
            }
        )

    if normalized:
        return normalized

    # 没有岗位要求时保留空列表，避免伪造匹配关系。
    return []


def _match_requirement_with_resume(requirement: str, sections: List[Dict[str, Any]], resume_text: str) -> Tuple[str, str]:
    req = requirement.strip()
    if not req:
        return "未匹配", "未提供岗位要求文本。"

    tokens = _extract_requirement_tokens(req)
    best_section = ""
    best_score = 0
    best_evidence = ""

    for section in sections:
        haystack = f"{section.get('name', '')}\n{section.get('before', '')}\n{section.get('after', '')}"
        score = _requirement_overlap_score(req, tokens, haystack)
        if score > best_score:
            best_score = score
            best_section = str(section.get("name") or "")
            best_evidence = truncate_for_llm(haystack, max_chars=240)

    if req and req.lower() in (resume_text or "").lower():
        return "已匹配", truncate_for_llm(req, max_chars=120)
    if best_score >= 2:
        return "已匹配", f"{best_section}：{best_evidence}" if best_section else best_evidence
    if best_score == 1:
        return "部分匹配", f"{best_section}：{best_evidence}" if best_section else "找到部分相关描述，但证据不够直接。"
    return "未匹配", "原简历中未找到直接证据，建议仅在真实做过的前提下补强表达。"


def _normalize_risk_warnings(raw: Any, unmet_requirements: List[Dict[str, str]], job_requirements: Dict[str, Any]) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                risk = str(item.get("risk") or item.get("title") or "").strip()
                reason = str(item.get("reason") or item.get("detail") or "").strip()
            else:
                risk = str(item or "").strip()
                reason = ""
            if risk:
                warnings.append({"risk": risk, "reason": reason or "请基于原简历事实谨慎表述。"})

    for item in unmet_requirements[:6]:
        requirement = str(item.get("requirement") or "").strip()
        status = str(item.get("status") or "").strip()
        evidence = str(item.get("resume_evidence") or "").strip()
        if requirement:
            warnings.append(
                {
                    "risk": f"{requirement} 当前{status}",
                    "reason": evidence or "原简历中缺少直接证据，不能在优化结果中写成已具备。",
                }
            )

    for item in job_requirements.get("risk_flags") or []:
        text = item.get("requirement") if isinstance(item, dict) else item
        normalized = str(text or "").strip()
        if normalized:
            warnings.append({"risk": normalized, "reason": "岗位描述本身存在需要二次确认的信息。"})

    return _dedupe_warning_dicts(warnings)[:10]


def _normalize_suggested_experiences(raw: Any, unmet_requirements: List[Dict[str, str]]) -> List[str]:
    suggestions = _normalize_string_list(raw)
    if suggestions:
        return suggestions

    generated = []
    for item in unmet_requirements[:4]:
        requirement = str(item.get("requirement") or "").strip()
        if requirement:
            generated.append(f"如果你真实做过与“{requirement}”相关的课程、项目或实践，可补充更具体的动作、工具和结果。")
    if generated:
        return generated
    return [
        "优先把与目标岗位最相关的真实课程、项目和实践写成结果导向表达。",
        "如果已有可量化成果或作品链接，可在对应模块补充，但不要新增原简历没有的事实。",
    ]


def _normalize_structure_payload(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized = {
        "basics": value.get("basics") if isinstance(value.get("basics"), dict) else {},
        "targetRole": str(value.get("targetRole") or value.get("target_role") or ""),
        "education": value.get("education") if isinstance(value.get("education"), list) else [],
        "experiences": value.get("experiences") if isinstance(value.get("experiences"), list) else [],
        "projects": value.get("projects") if isinstance(value.get("projects"), list) else [],
        "skills": value.get("skills") if isinstance(value.get("skills"), list) else [],
        "certificates": value.get("certificates") if isinstance(value.get("certificates"), list) else [],
        "awards": value.get("awards") if isinstance(value.get("awards"), list) else [],
        "selfEvaluation": str(value.get("selfEvaluation") or value.get("self_evaluation") or ""),
        "customSections": value.get("customSections") if isinstance(value.get("customSections"), list) else [],
        "metadata": value.get("metadata") if isinstance(value.get("metadata"), dict) else {},
    }
    return normalized


def _compact_resume_context(
    resume_text: str,
    section_items: List[Dict[str, str]],
    baseline_structure: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "source": "sections" if section_items else "rawText",
        "sections": section_items,
        "rawTextPreview": truncate_for_llm(resume_text or "", max_chars=MAX_RESUME_PREVIEW_CHARS),
        "structuredSkeleton": baseline_structure,
        "coverageHint": {
            "moduleCount": len(section_items),
            "moduleNames": [item["name"] for item in section_items],
        },
    }


def _build_structured_resume_skeleton(
    resume_text: str,
    section_items: List[Dict[str, str]],
    job_requirements: Dict[str, Any],
) -> Dict[str, Any]:
    structure = _empty_structure()
    basics = structure["basics"]
    basics.update(_extract_basics(resume_text, section_items))
    target_title = str(job_requirements.get("title") or basics.get("objective") or "")
    structure["targetRole"] = target_title
    basics["objective"] = str(basics.get("objective") or target_title)
    basics["summary"] = str(basics.get("summary") or _build_summary_text(section_items, target_title))

    for item in section_items:
        module_type = _module_type_from_name(item["name"])
        content = item["content"]
        if module_type == "education":
            structure["education"].extend(_entries_from_content(content, item["name"]))
        elif module_type == "projects":
            structure["projects"].extend(_entries_from_content(content, item["name"]))
        elif module_type == "experiences":
            structure["experiences"].extend(_entries_from_content(content, item["name"]))
        elif module_type == "campus":
            structure["customSections"].append({"title": item["name"], "items": _split_paragraphs(content)})
        elif module_type == "skills":
            structure["skills"].extend(_skill_groups_from_content(content))
        elif module_type == "certificates":
            structure["certificates"].extend(_split_items(content))
        elif module_type == "summary":
            if not structure["selfEvaluation"]:
                structure["selfEvaluation"] = content
        elif module_type == "custom":
            structure["customSections"].append({"title": item["name"], "items": _split_paragraphs(content)})
        elif module_type == "basics" and not basics["summary"]:
            basics["summary"] = content

    if not section_items and resume_text.strip():
        structure["customSections"].append({"title": "原始简历摘要", "items": _split_paragraphs(resume_text)})
    return structure


def _structure_from_module_sections(
    sections: List[Dict[str, Any]],
    target_title: str,
    summary_text: str,
) -> Dict[str, Any]:
    structure = _empty_structure()
    structure["targetRole"] = target_title
    structure["basics"]["objective"] = target_title
    structure["basics"]["summary"] = summary_text
    for item in sections:
        content = str(item.get("after") or item.get("before") or "").strip()
        if not content:
            continue
        module_type = str(item.get("module_type") or _module_type_from_name(str(item.get("name") or "")))
        if module_type == "education":
            structure["education"].extend(_entries_from_content(content, str(item.get("name") or "教育经历")))
        elif module_type == "projects":
            structure["projects"].extend(_entries_from_content(content, str(item.get("name") or "项目经历")))
        elif module_type == "experiences":
            structure["experiences"].extend(_entries_from_content(content, str(item.get("name") or "实践经历")))
        elif module_type == "campus":
            structure["customSections"].append({"title": str(item.get("name") or "校园/社团经历"), "items": _split_paragraphs(content)})
        elif module_type == "skills":
            structure["skills"].extend(_skill_groups_from_content(content))
        elif module_type == "certificates":
            structure["certificates"].extend(_split_items(content))
        elif module_type == "summary":
            structure["selfEvaluation"] = content
        elif module_type == "custom":
            structure["customSections"].append({"title": str(item.get("name") or "补充模块"), "items": _split_paragraphs(content)})
    return structure


def _merge_structures(baseline: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    base = _normalize_structure_payload(baseline)
    top = _normalize_structure_payload(overlay)
    merged = _empty_structure()

    for key in ["name", "title", "phone", "email", "location", "summary", "website", "objective", "github", "media", "photo"]:
        merged["basics"][key] = str(top["basics"].get(key) or base["basics"].get(key) or "")

    merged["basics"]["links"] = _merge_unique_list(base["basics"].get("links"), top["basics"].get("links"))
    merged["targetRole"] = str(top.get("targetRole") or base.get("targetRole") or merged["basics"].get("objective") or "")
    merged["education"] = _merge_entry_lists(base.get("education"), top.get("education"))
    merged["experiences"] = _merge_entry_lists(base.get("experiences"), top.get("experiences"))
    merged["projects"] = _merge_entry_lists(base.get("projects"), top.get("projects"))
    merged["skills"] = _merge_skill_groups(base.get("skills"), top.get("skills"))
    merged["certificates"] = _merge_unique_list(base.get("certificates"), top.get("certificates"))
    merged["awards"] = _merge_unique_list(base.get("awards"), top.get("awards"))
    merged["selfEvaluation"] = str(top.get("selfEvaluation") or base.get("selfEvaluation") or "")
    merged["customSections"] = _merge_custom_sections(base.get("customSections"), top.get("customSections"))
    merged["metadata"] = dict(base.get("metadata") or {})
    merged["metadata"].update(dict(top.get("metadata") or {}))
    return merged


def _empty_structure() -> Dict[str, Any]:
    return {
        "basics": {
            "name": "",
            "title": "",
            "phone": "",
            "email": "",
            "location": "",
            "summary": "",
            "website": "",
            "objective": "",
            "github": "",
            "media": "",
            "photo": "",
            "links": [],
        },
        "targetRole": "",
        "education": [],
        "experiences": [],
        "projects": [],
        "skills": [],
        "certificates": [],
        "awards": [],
        "selfEvaluation": "",
        "customSections": [],
        "metadata": {},
    }


def _extract_basics(resume_text: str, section_items: List[Dict[str, str]]) -> Dict[str, Any]:
    raw_lines = [line.strip() for line in (resume_text or "").replace("\r\n", "\n").split("\n") if line.strip()]
    basics_lines = []
    for item in section_items:
        if _module_type_from_name(item["name"]) == "basics":
            basics_lines.extend(_split_paragraphs(item["content"]))
    source_lines = basics_lines or raw_lines[:12]
    joined = "\n".join(source_lines)

    name = ""
    for line in source_lines[:4]:
        compact = re.sub(r"\s+", "", line)
        if re.fullmatch(r"[\u4e00-\u9fa5·]{2,8}", compact):
            name = compact
            break

    phone = _first_regex(joined, r"(1[3-9]\d{9})")
    email = _first_regex(joined, r"([A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+)")
    website = _first_regex(joined, r"(https?://[^\s)]+)")
    github = _first_regex(joined, r"(github\.com/[^\s)]+)")
    media = ""
    for keyword in ["小红书", "抖音", "B站", "公众号", "自媒体"]:
        if keyword in joined:
            media = keyword
            break

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "website": website or github,
        "github": github,
        "media": media,
        "summary": "",
        "links": [item for item in [website, github] if item],
    }


def _build_summary_text(section_items: List[Dict[str, str]], target_title: str) -> str:
    parts = []
    for key in ["education", "projects", "experiences", "skills"]:
        count = sum(1 for item in section_items if _module_type_from_name(item["name"]) == key)
        if count:
            parts.append(f"{count}个{_module_type_label(key)}")
    campus_count = sum(1 for item in section_items if _module_type_from_name(item["name"]) == "campus")
    if campus_count:
        parts.append(f"{campus_count}个校园模块")
    scope = "、".join(parts) if parts else "原始简历内容"
    if target_title:
        return f"基于原简历已有事实，围绕{target_title}梳理{scope}中的相关证据。"
    return f"基于原简历已有事实，梳理{scope}中的重点信息并优化表达。"


def _module_type_label(module_type: str) -> str:
    mapping = {
        "education": "教育模块",
        "projects": "项目模块",
        "experiences": "实践模块",
        "campus": "校园模块",
        "skills": "技能模块",
        "certificates": "证书模块",
    }
    return mapping.get(module_type, "模块")


def _is_template_ready(structure: Dict[str, Any]) -> bool:
    return any(
        [
            structure.get("education"),
            structure.get("experiences"),
            structure.get("projects"),
            structure.get("skills"),
            structure.get("customSections"),
        ]
    )


def _normalize_lightweight_sections(result: Dict[str, Any]) -> None:
    optimized = result.get("optimized_resume")
    if not isinstance(optimized, dict):
        return
    sections = optimized.get("sections")
    if not isinstance(sections, list):
        return
    for section in sections:
        if not isinstance(section, dict):
            continue
        reason = section.get("reason")
        if reason and not isinstance(section.get("reasons"), list):
            section["reasons"] = [str(reason)]


def _normalize_final_resume_sections(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        content = str(item.get("content") or item.get("text") or "").strip()
        if title and content:
            result.append({"title": title, "content": content})
    return result


def _normalize_final_resume_text(
    explicit_text: Any,
    explicit_sections: List[Dict[str, str]],
    optimized_structure: Dict[str, Any],
    module_sections: List[Dict[str, Any]],
    target_title: str,
) -> str:
    text = str(explicit_text or "").strip()
    if text:
        return text
    if explicit_sections:
        return _render_final_resume_sections(explicit_sections)
    return _render_final_resume_sections(
        _build_final_resume_sections(optimized_structure, module_sections, target_title)
    )


def _build_final_resume_sections(
    optimized_structure: Dict[str, Any],
    module_sections: List[Dict[str, Any]],
    target_title: str,
) -> List[Dict[str, str]]:
    basics = optimized_structure.get("basics") if isinstance(optimized_structure.get("basics"), dict) else {}
    header_lines = [str(basics.get("name") or "").strip() or "【待补】"]
    contact_bits = [
        str(basics.get("phone") or "").strip(),
        str(basics.get("email") or "").strip(),
        str(basics.get("website") or "").strip(),
        str(basics.get("github") or "").strip(),
        target_title.strip(),
    ]
    header_lines.append(" / ".join([item for item in contact_bits if item]) or "联系方式【待补】")

    return [
        {"title": "抬头", "content": "\n".join([line for line in header_lines if line])},
        {"title": "教育背景", "content": _render_entries(optimized_structure.get("education"), fallback="【待补】")},
        {"title": "专业技能", "content": _render_skills(optimized_structure.get("skills"), fallback="【待补】")},
        {
            "title": "校园/社团经历",
            "content": _render_custom_section(
                _pick_custom_section(optimized_structure, "校园"),
                fallback=_fallback_module_content(module_sections, "campus"),
            ),
        },
        {
            "title": "工作/实习经历",
            "content": _render_entries(
                optimized_structure.get("experiences"),
                fallback=_fallback_module_content(module_sections, "experiences"),
            ),
        },
        {
            "title": "项目经历",
            "content": _render_entries(
                optimized_structure.get("projects"),
                fallback=_fallback_module_content(module_sections, "projects"),
            ),
        },
        {
            "title": "证书/奖项",
            "content": _render_certificates(
                optimized_structure,
                fallback=_fallback_module_content(module_sections, "certificates"),
            ),
        },
        {
            "title": "自我评价",
            "content": str(optimized_structure.get("selfEvaluation") or "").strip() or "【待补】",
        },
    ]


def _render_final_resume_sections(sections: List[Dict[str, str]]) -> str:
    blocks = []
    for item in sections:
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip() or "【待补】"
        if title:
            blocks.append(f"{title}\n{content}")
    return "\n\n".join(blocks).strip()


def _sections_from_final_resume_text(text: str) -> List[Dict[str, str]]:
    pattern = re.compile(r"^(抬头|教育背景|专业技能|校园/社团经历|工作/实习经历|项目经历|证书/奖项|自我评价)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text or ""))
    if not matches:
        return [{"title": "完整成稿", "content": (text or "").strip()}] if str(text or "").strip() else []

    result: List[Dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append(
            {
                "title": match.group(1),
                "content": text[start:end].strip() or "【待补】",
            }
        )
    return result


def _render_entries(value: Any, fallback: str = "【待补】") -> str:
    if not isinstance(value, list) or not value:
        return fallback or "【待补】"
    rendered: List[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("organization") or item.get("role") or "").strip() or "【待补】"
        meta_parts = [
            str(item.get("organization") or "").strip(),
            str(item.get("role") or "").strip(),
            str(item.get("period") or "").strip(),
        ]
        meta = " | ".join([part for part in meta_parts if part and part != title])
        bullets = item.get("bullets") if isinstance(item.get("bullets"), list) else []
        bullet_lines = [f"• {str(bullet).strip()}" for bullet in bullets if str(bullet).strip()]
        lines = [title]
        if meta:
            lines.append(meta)
        lines.extend(bullet_lines)
        rendered.append("\n".join(lines).strip())
    return "\n\n".join([item for item in rendered if item]).strip() or fallback or "【待补】"


def _render_skills(value: Any, fallback: str = "【待补】") -> str:
    if not isinstance(value, list) or not value:
        return fallback or "【待补】"
    lines = []
    for item in value:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "技能").strip()
        skill_items = item.get("items") if isinstance(item.get("items"), list) else []
        cleaned_items = [str(skill).strip() for skill in skill_items if str(skill).strip()]
        if cleaned_items:
            lines.append(f"{category}：{'、'.join(cleaned_items)}")
    return "\n".join(lines).strip() or fallback or "【待补】"


def _render_certificates(optimized_structure: Dict[str, Any], fallback: str = "【待补】") -> str:
    lines = _normalize_string_list(optimized_structure.get("certificates")) + _normalize_string_list(
        optimized_structure.get("awards")
    )
    if lines:
        return "\n".join([f"• {line}" for line in lines])
    return fallback or "【待补】"


def _pick_custom_section(optimized_structure: Dict[str, Any], keyword: str) -> List[str]:
    sections = optimized_structure.get("customSections") if isinstance(optimized_structure.get("customSections"), list) else []
    for item in sections:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if keyword in title:
            values = item.get("items") if isinstance(item.get("items"), list) else _split_paragraphs(str(item.get("content") or ""))
            return [str(value).strip() for value in values if str(value).strip()]
    return []


def _render_custom_section(items: List[str], fallback: str = "【待补】") -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if cleaned:
        return "\n".join([f"• {item}" for item in cleaned])
    return fallback or "【待补】"


def _fallback_module_content(module_sections: List[Dict[str, Any]], module_type: str) -> str:
    chunks = []
    for section in module_sections:
        if str(section.get("module_type") or "") != module_type:
            continue
        value = str(section.get("after") or section.get("before") or "").strip()
        if value:
            chunks.append(value)
    return "\n\n".join(chunks).strip() or "【待补】"


def _section_items(sections: Any, resume_text: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    if isinstance(sections, list):
        for index, section in enumerate(sections):
            if isinstance(section, dict):
                name = str(section.get("name") or section.get("title") or f"模块 {index + 1}")
                content = str(section.get("content") or section.get("text") or section.get("value") or "")
            else:
                name = f"模块 {index + 1}"
                content = str(section or "")
            content = content.strip()
            if content:
                items.append({"name": name[:40], "content": truncate_for_llm(content, max_chars=MAX_SECTION_CHARS)})

    if not items and resume_text.strip():
        items.append({"name": "原始简历摘要", "content": truncate_for_llm(resume_text, max_chars=MAX_RESUME_CONTEXT_CHARS)})
    return items


def _entries_from_content(content: str, fallback_title: str) -> List[Dict[str, Any]]:
    paragraphs = _split_paragraphs(content)
    if not paragraphs:
        return []
    entries = []
    current_title = paragraphs[0][:40] if paragraphs else fallback_title
    bullets = paragraphs[1:] if len(paragraphs) > 1 else []
    entries.append(
        {
            "title": current_title or fallback_title,
            "organization": "",
            "role": "",
            "period": _extract_period(content),
            "location": "",
            "bullets": bullets or [paragraphs[0]],
        }
    )
    return entries


def _skill_groups_from_content(content: str) -> List[Dict[str, Any]]:
    groups = []
    for line in _split_paragraphs(content):
        if "：" in line:
            category, value = line.split("：", 1)
        elif ":" in line:
            category, value = line.split(":", 1)
        else:
            category, value = "技能", line
        items = _split_items(value)
        if items:
            groups.append({"category": category.strip() or "技能", "items": items})
    if groups:
        return groups
    items = _split_items(content)
    return [{"category": "技能", "items": items}] if items else []


def _split_paragraphs(content: str) -> List[str]:
    return [line.strip(" -•·\t") for line in re.split(r"[\r\n]+", content or "") if line.strip(" -•·\t")]


def _split_items(content: str) -> List[str]:
    parts = re.split(r"[、,，/；;|\n]+", content or "")
    return _dedupe([part.strip(" -•·\t") for part in parts if part.strip(" -•·\t")])


def _merge_entry_lists(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    result = []
    seen = set()
    for source in [secondary or [], primary or []]:
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            bullets = [str(b).strip() for b in item.get("bullets", []) if str(b).strip()] if isinstance(item.get("bullets"), list) else []
            if not title and not bullets:
                continue
            key = _slug(title or " ".join(bullets[:2]))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def _merge_skill_groups(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    merged: Dict[str, List[str]] = {}
    for source in [primary or [], secondary or []]:
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category") or "技能").strip() or "技能"
            bucket = merged.setdefault(category, [])
            raw_items = item.get("items") if isinstance(item.get("items"), list) else []
            for skill in raw_items:
                value = str(skill).strip()
                if value and value not in bucket:
                    bucket.append(value)
    return [{"category": key, "items": value} for key, value in merged.items() if value]


def _merge_custom_sections(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    result = []
    seen = set()
    for source in [primary or [], secondary or []]:
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            items = item.get("items") if isinstance(item.get("items"), list) else _split_paragraphs(str(item.get("content") or ""))
            result.append({"title": title, "items": [str(value).strip() for value in items if str(value).strip()]})
    return result


def _merge_unique_list(primary: Any, secondary: Any) -> List[str]:
    items = []
    seen = set()
    for source in [secondary or [], primary or []]:
        if not isinstance(source, list):
            continue
        for item in source:
            value = str(item).strip()
            if value and value not in seen:
                seen.add(value)
                items.append(value)
    return items


def _module_type_from_name(name: str) -> str:
    lowered = name.lower()
    if any(token in name for token in ["教育", "课程"]):
        return "education"
    if any(token in name for token in ["校园", "社团", "学生工作", "学生会", "志愿"]):
        return "campus"
    if any(token in name for token in ["项目", "研发"]):
        return "projects"
    if any(token in name for token in ["技能", "技术"]) or "skill" in lowered:
        return "skills"
    if any(token in name for token in ["证书", "获奖", "奖项"]) or "certificate" in lowered:
        return "certificates"
    if any(token in name for token in ["实习", "工作", "实践", "运营", "经历"]) or "experience" in lowered:
        return "experiences"
    if any(token in name for token in ["评价", "总结", "简介", "概况"]) or "summary" in lowered:
        return "summary"
    if any(token in name for token in ["基本", "信息", "联系"]):
        return "basics"
    return "custom"


def _normalize_requirement_names(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return _dedupe([str(item).strip() for item in value if str(item).strip()])


def _normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _match_requirement_names_from_text(text: str, job_requirements: Dict[str, Any]) -> List[str]:
    result = []
    lowered = (text or "").lower()
    for requirement in _requirement_texts(job_requirements):
        if not requirement:
            continue
        tokens = _extract_requirement_tokens(requirement)
        if requirement.lower() in lowered:
            result.append(requirement)
            continue
        overlap = sum(1 for token in tokens if token.lower() in lowered)
        if overlap >= 2:
            result.append(requirement)
    return _dedupe(result)[:6]


def _extract_requirement_tokens(text: str) -> List[str]:
    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,24}", text)
    chinese_tokens = [token for token in re.findall(r"[\u4e00-\u9fa5]{2,8}", text) if token not in {"负责", "相关", "具备", "熟悉", "优先"}]
    return _dedupe(ascii_tokens + chinese_tokens)


def _requirement_overlap_score(requirement: str, tokens: List[str], haystack: str) -> int:
    lowered = haystack.lower()
    if requirement.lower() in lowered:
        return 3
    return min(2, sum(1 for token in tokens if token.lower() in lowered))


def _extract_period(text: str) -> str:
    match = re.search(r"((?:19|20)\d{2}[./-]?\d{0,2}\s*[—\-~至到]\s*(?:至今|现在|今|(?:19|20)\d{2}[./-]?\d{0,2}))", text)
    if match:
        return match.group(1).replace(" ", "")
    single = re.search(r"((?:19|20)\d{2}[./-]?\d{0,2})", text)
    return single.group(1).replace(" ", "") if single else ""


def _first_regex(text: str, pattern: str) -> str:
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fa5]+", "", (text or "").strip().lower())


def _split_job_sentences(text: str) -> List[str]:
    compact = re.sub(r"[ \t]+", " ", text)
    parts = re.split(r"[\n\r。；;，,]+", compact)
    return [part.strip(" ：:。；;、[]【】()（）") for part in parts if part.strip(" ：:。；;、[]【】()（）")]


def _strip_section_label(sentence: str) -> str:
    return re.sub(
        r"^(工作内容|岗位职责|职位职责|任职要求|岗位要求|职位要求|加分项|优先条件)[：:\s]*",
        "",
        sentence,
    ).strip()


def _is_section_header(sentence: str) -> bool:
    return sentence.strip("【】[]：: ") in {
        "工作内容",
        "岗位职责",
        "职位职责",
        "任职要求",
        "岗位要求",
        "职位要求",
        "加分项",
        "优先条件",
    }


def _guess_job_title(sentences: List[str]) -> str:
    title_words = ["运营", "销售", "客服", "开发", "工程师", "产品", "设计", "人事", "HR", "财务", "主播", "剪辑", "文案"]
    for sentence in sentences[:4]:
        cleaned = _strip_section_label(sentence)
        if 2 <= len(cleaned) <= 30 and _contains_any(cleaned, title_words):
            return cleaned
    return ""


def _extract_experience_years(text: str) -> str:
    match = re.search(r"(\d+\s*[-~至到]\s*\d+\s*年|\d+\s*年(?:以上|及以上)?经验)", text)
    return match.group(1).replace(" ", "") if match else ""


def _extract_job_keywords(text: str, sentences: List[str]) -> List[str]:
    preferred = [
        "私域流量",
        "私域流量运营",
        "在线运营",
        "运营",
        "卖课",
        "卖服务",
        "卖系统",
        "课程销售",
        "销售",
        "客服",
        "服务",
        "系统",
        "赛道",
        "归零心态",
        "执行力",
        "学习能力",
        "沟通",
        "流量",
        "Vue",
        "React",
        "TypeScript",
        "JavaScript",
        "Python",
        "FastAPI",
    ]
    keywords = [word for word in preferred if word in text]
    keywords.extend(re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,24}", text))
    for sentence in sentences:
        for token in re.findall(r"[\u4e00-\u9fa5]{2,8}", sentence):
            if any(marker in token for marker in ["岗位", "工作", "内容", "要求", "我们", "加入"]):
                continue
            keywords.append(token)
    return _dedupe(keywords)


def _suggest_keywords(resume_text: str, job_requirements: Dict[str, Any]) -> List[str]:
    candidates = [str(item) for item in job_requirements.get("keywords") or []]
    candidates.extend(_requirement_texts(job_requirements))
    text = resume_text.lower()
    result = []
    for item in _dedupe(candidates):
        lowered = item.lower()
        if lowered and (lowered in text or len(item) <= 24):
            result.append(item)
    return result


def _requirement_texts(job_requirements: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    for key in ["must_haves", "nice_to_haves"]:
        for item in job_requirements.get(key) or []:
            if isinstance(item, dict):
                result.append(str(item.get("requirement") or item.get("name") or ""))
            else:
                result.append(str(item or ""))
    return _dedupe(result)


def _contains_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


def _requirements_with_evidence(items: List[str]) -> List[Dict[str, str]]:
    return [{"requirement": item, "evidence": ""} for item in items if item]


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        cleaned = str(item).strip(" ：:。；;、")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _dedupe_warning_dicts(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    result = []
    for item in items:
        risk = str(item.get("risk") or "").strip()
        reason = str(item.get("reason") or "").strip()
        key = (risk, reason)
        if risk and key not in seen:
            seen.add(key)
            result.append({"risk": risk, "reason": reason})
    return result


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
