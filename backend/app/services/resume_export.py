import base64
import html
import math
import os
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import fitz


RESUME_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "modern",
        "name": "现代求职单栏版",
        "scene": "campus",
        "tone": "clean",
        "accent": "#1D4ED8",
        "layout": "cn-campus-single",
        "styleVariant": "modern",
    },
    {
        "id": "executive",
        "name": "经典正式单栏版",
        "scene": "general",
        "tone": "classic",
        "accent": "#334155",
        "layout": "cn-campus-single",
        "styleVariant": "executive",
    },
    {
        "id": "compact",
        "name": "高密度单栏版",
        "scene": "technical",
        "tone": "professional",
        "accent": "#0F766E",
        "layout": "cn-campus-single",
        "styleVariant": "compact",
    },
    {
        "id": "academic",
        "name": "学术研究单栏版",
        "scene": "research",
        "tone": "academic",
        "accent": "#6D28D9",
        "layout": "cn-campus-single",
        "styleVariant": "academic",
    },
    {
        "id": "studio",
        "name": "品牌表达单栏版",
        "scene": "design",
        "tone": "creative",
        "accent": "#C2410C",
        "layout": "cn-campus-single",
        "styleVariant": "studio",
    },
    {
        "id": "chinese",
        "name": "中文左窄右宽双栏版",
        "scene": "campus",
        "tone": "confident",
        "accent": "#9A3412",
        "layout": "cn-campus-double",
        "styleVariant": "chinese",
    },
]

TEMPLATE_INDEX: Dict[str, Dict[str, Any]] = {item["id"]: item for item in RESUME_TEMPLATES}
LEGACY_TEMPLATE_ALIASES = {
    "campus-clean": "modern",
    "tech-intern": "compact",
    "product-ops": "executive",
}

SECTION_LABELS = {
    "summary": "个人简介",
    "education": "教育背景",
    "experiences": "实习经历",
    "projects": "核心项目与研发经历",
    "skills": "技能证书",
    "certificates": "证书奖项",
    "selfEvaluation": "补充说明",
}


def list_resume_templates() -> List[Dict[str, Any]]:
    return [dict(item) for item in RESUME_TEMPLATES]


def get_template(template_id: str) -> Dict[str, Any]:
    canonical_id = LEGACY_TEMPLATE_ALIASES.get(str(template_id or "").strip(), str(template_id or "").strip())
    template = TEMPLATE_INDEX.get(canonical_id)
    if not template:
        raise ValueError(f"未知简历模板 ID: {template_id}")
    return dict(template)


def structure_resume_data(source: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("resume source must be an object")

    baseline = _structured_from_source(source)
    optimized = _structured_from_optimized_result(source)
    structured = _merge_structured_resumes(baseline, optimized)
    structured = _normalize_structured_resume(structured)

    metadata = dict(source.get("metadata") or {}) if isinstance(source.get("metadata"), dict) else {}
    metadata["generatedAt"] = datetime.now().isoformat(timespec="seconds")
    metadata["source"] = _detect_structured_source(source)
    metadata["nonFabricationReminder"] = str(
        source.get("nonFabricationReminder")
        or source.get("non_fabrication_statement")
        or metadata.get("nonFabricationReminder")
        or "仅基于原始简历已有事实做结构化整理，不新增任何虚构经历、学历、公司、项目、技能或成果。"
    )
    metadata["fallbackStatus"] = str(source.get("fallback_status") or metadata.get("fallbackStatus") or "none")
    metadata["riskWarnings"] = _normalize_risk_warnings(
        source.get("risk_warnings") or source.get("riskWarnings") or metadata.get("riskWarnings")
    )
    metadata["missingFields"] = _collect_missing_fields(structured)
    metadata["warnings"] = _collect_structure_warnings(structured, metadata)
    metadata["completeness"] = "complete" if not metadata["missingFields"] else "partial"
    structured["metadata"] = metadata
    return structured


def render_resume_pdf(template_id: str, structured_resume: Dict[str, Any]) -> Dict[str, str]:
    template = get_template(template_id)
    data = _normalize_structured_resume(structured_resume)
    html_text = render_resume_html(template["id"], data)

    output_dir = tempfile.gettempdir()
    safe_name = _safe_filename(data["basics"].get("name") or "resume")
    filename = f"{safe_name}_{template['id']}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf"
    output_path = os.path.join(output_dir, filename)

    try:
        _render_pdf_with_playwright(html_text, output_path)
        engine = "playwright"
    except Exception:
        _render_pdf_with_pymupdf(data, template, output_path)
        engine = "pymupdf"

    return {"path": output_path, "filename": filename, "engine": engine}


def render_resume_html(template_id: str, data: Dict[str, Any]) -> str:
    template = get_template(template_id)
    normalized = _normalize_structured_resume(data)
    sections = _build_resume_sections(normalized, template)
    basics = normalized["basics"]
    body_html = (
        _render_double_layout_html(template, normalized, sections)
        if template["layout"] == "cn-campus-double"
        else _render_single_layout_html(template, normalized, sections)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    {_base_resume_css(template)}
  </style>
</head>
<body class="layout-{_e(template['layout'])} variant-{_e(template['styleVariant'])}">
  {body_html}
</body>
</html>"""


def _render_pdf_with_playwright(html_text: str, output_path: str) -> None:
    import asyncio
    from playwright.async_api import async_playwright

    async def _run() -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html_text, wait_until="networkidle")
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                margin={"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"},
            )
            await browser.close()

    asyncio.run(_run())


def _render_pdf_with_pymupdf(data: Dict[str, Any], template: Dict[str, Any], output_path: str) -> None:
    doc = fitz.open()
    fontfile = _find_chinese_font()
    state = _create_pdf_state(doc, fontfile, template)
    sections = _build_resume_sections(data, template)
    if template["layout"] == "cn-campus-double":
        _render_double_layout_pdf(state, data, sections)
    else:
        _render_single_layout_pdf(state, data, sections)
    doc.save(output_path)
    doc.close()


def _empty_structured_resume() -> Dict[str, Any]:
    return {
        "basics": {
            "name": "",
            "title": "",
            "phone": "",
            "email": "",
            "location": "",
            "summary": "",
            "website": "",
            "github": "",
            "media": "",
            "photo": "",
            "objective": "",
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


def _structured_from_source(source: Dict[str, Any]) -> Dict[str, Any]:
    if _looks_structured(source):
        return _normalize_structured_resume(source)

    structured = _empty_structured_resume()
    for section in _extract_resume_sections(source):
        _merge_section(
            structured,
            str(section.get("name") or section.get("title") or "").strip(),
            str(section.get("content") or section.get("text") or section.get("value") or "").strip(),
        )

    raw_resume_text = _extract_raw_resume_text(source)
    if raw_resume_text and _structured_is_empty(structured):
        structured["projects"].append(_generic_entry(raw_resume_text, title="原始简历摘要"))

    structured["targetRole"] = str(
        source.get("targetRole")
        or source.get("target_role")
        or _safe_get(source.get("jobRequirementsUsed"), "title")
        or structured["targetRole"]
        or ""
    )
    if not structured["basics"]["summary"]:
        structured["basics"]["summary"] = str(source.get("summary") or "")
    return _normalize_structured_resume(structured)


def _structured_from_optimized_result(source: Dict[str, Any]) -> Dict[str, Any]:
    optimized_structure = source.get("optimizedStructure")
    if isinstance(optimized_structure, dict):
        return _normalize_structured_resume(optimized_structure)

    structured_resume = source.get("structuredResume")
    if isinstance(structured_resume, dict):
        return _normalize_structured_resume(structured_resume)

    optimized_resume = source.get("optimized_resume") or source.get("optimizedResume") or {}
    if not isinstance(optimized_resume, dict):
        return _empty_structured_resume()

    structured = _empty_structured_resume()
    structured["targetRole"] = str(
        optimized_resume.get("target_title")
        or optimized_resume.get("targetRole")
        or source.get("targetRole")
        or _safe_get(source.get("jobRequirementsUsed"), "title")
        or ""
    )
    structured["basics"]["summary"] = str(optimized_resume.get("summary") or source.get("summary") or "")

    sections = optimized_resume.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            name = str(section.get("name") or section.get("title") or "").strip()
            content = str(section.get("after") or section.get("content") or section.get("before") or "").strip()
            _merge_section(structured, name, content)

    modules = source.get("modules")
    if isinstance(modules, list):
        for module in modules:
            if not isinstance(module, dict):
                continue
            name = str(module.get("moduleName") or "").strip()
            content = str(module.get("optimizedContent") or module.get("originalContent") or "").strip()
            _merge_section(structured, name, content)

    return _normalize_structured_resume(structured)


def _normalize_structured_resume(source: Dict[str, Any]) -> Dict[str, Any]:
    data = _empty_structured_resume()
    basics = source.get("basics") if isinstance(source.get("basics"), dict) else {}
    basics_aliases = {
        "name": ["name", "fullName"],
        "title": ["title", "headline"],
        "phone": ["phone", "mobile", "wechat", "phoneWechat"],
        "email": ["email"],
        "location": ["location", "city"],
        "summary": ["summary", "profile", "bio"],
        "website": ["website", "portfolio", "homepage"],
        "github": ["github", "gitHub"],
        "media": ["media", "selfMedia", "socialMedia"],
        "photo": ["photo", "avatar", "image", "headshot"],
        "objective": ["objective", "targetRole", "desiredRole"],
    }
    for key, aliases in basics_aliases.items():
        data["basics"][key] = str(_coalesce_from_dict(basics, aliases) or "")

    links = basics.get("links")
    if isinstance(links, list):
        data["basics"]["links"] = [str(item).strip() for item in links if str(item).strip()]
    else:
        data["basics"]["links"] = _dedupe_texts(
            [
                data["basics"]["website"],
                data["basics"]["github"],
                data["basics"]["media"],
            ]
        )

    data["targetRole"] = str(
        source.get("targetRole")
        or source.get("target_role")
        or data["basics"]["objective"]
        or data["basics"]["title"]
        or ""
    )
    data["education"] = _normalize_entries(source.get("education"))
    data["experiences"] = _normalize_entries(source.get("experiences"))
    data["projects"] = _normalize_entries(source.get("projects"))
    data["skills"] = _normalize_skill_groups(source.get("skills"))
    data["certificates"] = _normalize_text_items(source.get("certificates"))
    data["awards"] = _normalize_text_items(source.get("awards"))
    data["selfEvaluation"] = str(source.get("selfEvaluation") or source.get("self_evaluation") or "")
    data["customSections"] = _normalize_custom_sections(source.get("customSections") or source.get("custom_sections"))
    data["metadata"] = dict(source.get("metadata") or {}) if isinstance(source.get("metadata"), dict) else {}
    return data


def _looks_structured(source: Dict[str, Any]) -> bool:
    return isinstance(source.get("basics"), dict) or any(
        key in source for key in ["education", "projects", "experiences", "skills", "customSections", "custom_sections"]
    )


def _merge_structured_resumes(baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
    base = _normalize_structured_resume(baseline)
    overlay = _normalize_structured_resume(optimized)
    merged = _empty_structured_resume()
    for key in [
        "name",
        "title",
        "phone",
        "email",
        "location",
        "summary",
        "website",
        "github",
        "media",
        "photo",
        "objective",
    ]:
        merged["basics"][key] = str(overlay["basics"].get(key) or base["basics"].get(key) or "")
    merged["basics"]["links"] = _merge_text_lists(overlay["basics"].get("links"), base["basics"].get("links"))
    merged["targetRole"] = str(overlay.get("targetRole") or base.get("targetRole") or merged["basics"]["objective"] or "")
    merged["education"] = _merge_entries(overlay.get("education"), base.get("education"))
    merged["experiences"] = _merge_entries(overlay.get("experiences"), base.get("experiences"))
    merged["projects"] = _merge_entries(overlay.get("projects"), base.get("projects"))
    merged["skills"] = _merge_skill_group_lists(overlay.get("skills"), base.get("skills"))
    merged["certificates"] = _merge_text_lists(overlay.get("certificates"), base.get("certificates"))
    merged["awards"] = _merge_text_lists(overlay.get("awards"), base.get("awards"))
    merged["selfEvaluation"] = str(overlay.get("selfEvaluation") or base.get("selfEvaluation") or "")
    merged["customSections"] = _merge_custom_sections(overlay.get("customSections"), base.get("customSections"))
    merged["metadata"] = dict(base.get("metadata") or {})
    merged["metadata"].update(dict(overlay.get("metadata") or {}))
    return merged


def _extract_resume_sections(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = [
        source.get("sections"),
        source.get("resumeSections"),
        source.get("sourceSections"),
        _safe_get(source.get("resumeContext"), "sections"),
        _safe_get(source.get("resume_context"), "sections"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            result = []
            for item in candidate:
                if isinstance(item, dict):
                    result.append(item)
                else:
                    text = str(item or "").strip()
                    if text:
                        result.append({"name": "简历内容", "content": text})
            return result
    return []


def _extract_raw_resume_text(source: Dict[str, Any]) -> str:
    candidates = [
        source.get("rawResumeText"),
        source.get("resumeText"),
        source.get("raw_resume_text"),
        _safe_get(source.get("resumeContext"), "rawResumeText"),
        _safe_get(source.get("resume_context"), "rawResumeText"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _collect_missing_fields(structured: Dict[str, Any]) -> List[str]:
    data = _normalize_structured_resume(structured)
    missing = []
    if not data["basics"]["name"]:
        missing.append("basics.name")
    if not data["education"]:
        missing.append("education")
    if not data["experiences"] and not data["projects"]:
        missing.append("experiences_or_projects")
    if not data["skills"]:
        missing.append("skills")
    return missing


def _collect_structure_warnings(structured: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
    data = _normalize_structured_resume(structured)
    warnings = list(_normalize_text_items(metadata.get("warnings")))
    if metadata.get("fallbackStatus") and metadata.get("fallbackStatus") != "none":
        warnings.append("当前结构化结果包含兜底生成内容，建议在导出前人工复核。")
    if metadata.get("missingFields"):
        warnings.append("当前结构化简历仍有缺失字段，模板预览和导出可继续，但完整度有限。")
    if not data["basics"]["summary"]:
        warnings.append("缺少个人简介，将按精简模式渲染。")
    if not data["education"]:
        warnings.append("缺少教育背景，校园求职模板的信息完整度会受到影响。")
    return _dedupe_texts(warnings)


def _detect_structured_source(source: Dict[str, Any]) -> str:
    if source.get("optimizedStructure"):
        return "optimized_structure"
    if source.get("structuredResume"):
        return "structured_resume_response"
    if source.get("optimized_resume") or source.get("optimizedResume"):
        return "resume_optimize_result"
    if _looks_structured(source):
        return "structured_resume"
    if _extract_resume_sections(source):
        return "resume_sections"
    if _extract_raw_resume_text(source):
        return "raw_resume_text"
    return "unknown"


def _merge_section(data: Dict[str, Any], name: str, content: str) -> None:
    if not content:
        return
    lowered = name.lower()
    if any(token in name for token in ["基本", "个人", "联系", "求职意向"]) or "basic" in lowered:
        _merge_basics(data, content)
    elif "教育" in name:
        data["education"].extend(_education_entries_from_content(content, name))
    elif "项目" in name:
        data["projects"].extend(_entries_from_content(content))
    elif any(token in name for token in ["实习", "工作", "实践", "经历"]) or "experience" in lowered:
        data["experiences"].extend(_entries_from_content(content))
    elif any(token in name for token in ["技能", "技术"]) or "skill" in lowered:
        data["skills"].append({"category": "技能", "items": _split_items(content)})
    elif "证书" in name:
        data["certificates"].extend(_split_items(content))
    elif "奖" in name:
        data["awards"].extend(_split_items(content))
    elif any(token in name for token in ["评价", "总结"]) or "summary" in lowered:
        data["selfEvaluation"] = content
    else:
        data["customSections"].append({"title": name or "其他信息", "items": _split_items(content) or [content]})


def _merge_basics(data: Dict[str, Any], content: str) -> None:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if lines and not data["basics"]["name"]:
        data["basics"]["name"] = re.sub(r"^(姓名|Name)[:：\s]*", "", lines[0]).strip()
    email = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", content)
    phone = re.search(r"(?:\+?86[-\s]?)?1[3-9]\d{9}", content)
    if email:
        data["basics"]["email"] = email.group(0)
    if phone:
        data["basics"]["phone"] = phone.group(0)
    website_match = re.search(r"https?://[^\s)）]+", content)
    if website_match and not data["basics"]["website"]:
        data["basics"]["website"] = website_match.group(0)
    if "github" in content.lower() and not data["basics"]["github"]:
        github_match = re.search(r"github[:：]?\s*([^\s|]+)", content, flags=re.IGNORECASE)
        if github_match:
            data["basics"]["github"] = github_match.group(1).strip()
    if not data["targetRole"]:
        match = re.search(r"(?:求职意向|意向岗位|目标岗位)[:：\s]*([^\n|]+)", content)
        if match:
            data["targetRole"] = match.group(1).strip()
    if not data["basics"]["summary"] and len(lines) > 1:
        data["basics"]["summary"] = "；".join(lines[1:3])[:180]


def _entries_from_content(content: str) -> List[Dict[str, Any]]:
    blocks = [block.strip() for block in re.split(r"\n{2,}", content) if block.strip()]
    if blocks:
        return [_generic_entry(block) for block in blocks]
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) >= 3:
        chunks: List[List[str]] = []
        current: List[str] = []
        for line in lines:
            if current and _looks_like_new_entry(line):
                chunks.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            chunks.append(current)
        return [_generic_entry("\n".join(chunk)) for chunk in chunks]
    return [_generic_entry(content)]


def _education_entries_from_content(content: str, fallback_title: str) -> List[Dict[str, Any]]:
    entries = _entries_from_content(content)
    if not entries:
        return []
    normalized = []
    for entry in entries:
        current = dict(entry)
        if not current.get("title"):
            current["title"] = fallback_title
        current.setdefault("coursework", [])
        normalized.append(current)
    return normalized


def _generic_entry(content: str, title: str = "") -> Dict[str, Any]:
    lines = [line.strip(" -\t•·") for line in content.splitlines() if line.strip()]
    first = title or (lines[0] if lines else "")
    period_match = re.search(r"\d{4}[./-]\d{1,2}\s*[-~至到]+\s*(?:\d{4}[./-]\d{1,2}|至今|现在)", content)
    period = period_match.group(0) if period_match else ""
    bullets = lines[1:] if len(lines) > 1 else ([content.strip()] if content.strip() else [])
    return {
        "title": first,
        "organization": "",
        "role": "",
        "period": period,
        "location": "",
        "bullets": bullets,
        "coursework": [],
    }


def _looks_like_new_entry(line: str) -> bool:
    return bool(re.search(r"\d{4}[./-]\d{1,2}", line)) or len(line) <= 30


def _split_items(content: str) -> List[str]:
    parts = re.split(r"[\n,，;；、/]+", content)
    return [part.strip(" -\t•·") for part in parts if part.strip(" -\t•·")]


def _normalize_entries(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized = [_normalize_entry(item) for item in value]
    return [item for item in normalized if item["title"] or item["organization"] or item["bullets"]]


def _normalize_entry(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return _generic_entry(str(value or ""))
    period = str(
        value.get("period")
        or _join_nonempty([value.get("startDate"), value.get("endDate")], " - ")
        or value.get("duration")
        or ""
    )
    bullets_source: List[Any] = []
    for key in ["bullets", "highlights", "achievements", "descriptions"]:
        if isinstance(value.get(key), list):
            bullets_source.extend(value.get(key) or [])
    if not bullets_source and isinstance(value.get("description"), str):
        bullets_source = _split_items(value["description"])
    coursework_source = value.get("coursework")
    if not isinstance(coursework_source, list):
        coursework_source = _split_items(str(value.get("coreCourses") or value.get("courses") or ""))
    return {
        "title": str(value.get("title") or value.get("name") or value.get("school") or value.get("projectName") or ""),
        "organization": str(value.get("organization") or value.get("company") or ""),
        "role": str(value.get("role") or value.get("position") or value.get("degree") or value.get("major") or ""),
        "period": period,
        "location": str(value.get("location") or value.get("city") or ""),
        "bullets": [str(item).strip() for item in bullets_source if str(item).strip()],
        "coursework": [str(item).strip() for item in coursework_source if str(item).strip()],
    }


def _normalize_skill_groups(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    groups = []
    for item in value:
        if isinstance(item, dict):
            category = str(item.get("category") or item.get("label") or "技能")
            raw_items = item.get("items") if isinstance(item.get("items"), list) else item.get("values")
            if not isinstance(raw_items, list):
                raw_items = _split_items(str(item.get("text") or ""))
            groups.append({"category": category, "items": [str(skill).strip() for skill in raw_items if str(skill).strip()]})
        else:
            skills = _split_items(str(item or ""))
            if skills:
                groups.append({"category": "技能", "items": skills})
    return [group for group in groups if group["items"]]


def _normalize_text_items(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_risk_warnings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    warnings = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("risk") or item.get("reason") or item.get("message") or "").strip()
        else:
            text = str(item).strip()
        if text:
            warnings.append(text)
    return warnings


def _normalize_custom_sections(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    sections = []
    for item in value:
        if isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or item.get("label") or "").strip()
            raw_items = item.get("items")
            if isinstance(raw_items, list):
                entries = [str(entry).strip() for entry in raw_items if str(entry).strip()]
            else:
                entries = _split_items(str(item.get("content") or item.get("text") or ""))
            if title and entries:
                sections.append({"title": title, "items": entries})
        else:
            text = str(item or "").strip()
            if text:
                sections.append({"title": "其他信息", "items": [text]})
    return sections


def _merge_entries(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for source in [primary or [], secondary or []]:
        if not isinstance(source, list):
            continue
        for item in source:
            entry = _normalize_entry(item)
            signature = (
                entry["title"].strip().lower(),
                entry["organization"].strip().lower(),
                entry["role"].strip().lower(),
                entry["period"].strip().lower(),
            )
            if signature in seen and any(signature):
                continue
            seen.add(signature)
            merged.append(entry)
    return merged


def _merge_skill_group_lists(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    merged: Dict[str, List[str]] = {}
    for source in [primary or [], secondary or []]:
        if not isinstance(source, list):
            continue
        for item in _normalize_skill_groups(source):
            bucket = merged.setdefault(item["category"] or "技能", [])
            for skill in item["items"]:
                if skill not in bucket:
                    bucket.append(skill)
    return [{"category": category, "items": items} for category, items in merged.items()]


def _merge_custom_sections(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    merged: Dict[str, List[str]] = {}
    for source in [primary or [], secondary or []]:
        if not isinstance(source, list):
            continue
        for item in _normalize_custom_sections(source):
            bucket = merged.setdefault(item["title"], [])
            for text in item["items"]:
                if text not in bucket:
                    bucket.append(text)
    return [{"title": title, "items": items} for title, items in merged.items()]


def _merge_text_lists(primary: Any, secondary: Any) -> List[str]:
    return _dedupe_texts(_normalize_text_items(primary) + _normalize_text_items(secondary))


def _dedupe_texts(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _structured_is_empty(data: Dict[str, Any]) -> bool:
    normalized = _normalize_structured_resume(data)
    return not any(
        [
            normalized["basics"]["name"],
            normalized["basics"]["summary"],
            normalized["targetRole"],
            normalized["education"],
            normalized["experiences"],
            normalized["projects"],
            normalized["skills"],
            normalized["certificates"],
            normalized["awards"],
            normalized["selfEvaluation"],
            normalized["customSections"],
        ]
    )


def _build_resume_sections(data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    summary_text = data["basics"].get("summary") or data.get("selfEvaluation") or ""
    certificate_items = _dedupe_texts(data.get("certificates", []) + data.get("awards", []))
    custom_sections = [
        {"title": section["title"], "kind": "list", "items": section["items"]}
        for section in data.get("customSections", [])
        if section.get("title") and section.get("items")
    ]
    main: List[Dict[str, Any]] = []
    sidebar: List[Dict[str, Any]] = []

    if summary_text and template["layout"] == "cn-campus-double":
        sidebar.append({"title": SECTION_LABELS["summary"], "kind": "paragraph", "items": [summary_text]})
    elif summary_text:
        main.append({"title": SECTION_LABELS["summary"], "kind": "paragraph", "items": [summary_text]})

    if data["education"]:
        main.append({"title": SECTION_LABELS["education"], "kind": "entries", "items": data["education"]})
    if data["projects"]:
        main.append({"title": SECTION_LABELS["projects"], "kind": "entries", "items": data["projects"]})
    if data["experiences"]:
        main.append({"title": SECTION_LABELS["experiences"], "kind": "entries", "items": data["experiences"]})

    if data["skills"]:
        skill_block = {"title": SECTION_LABELS["skills"], "kind": "skills", "items": data["skills"]}
        if template["layout"] == "cn-campus-double":
            sidebar.append(skill_block)
        else:
            main.append(skill_block)

    if certificate_items:
        cert_block = {"title": SECTION_LABELS["certificates"], "kind": "list", "items": certificate_items}
        if template["layout"] == "cn-campus-double":
            sidebar.append(cert_block)
        else:
            main.append(cert_block)

    if data["selfEvaluation"] and data["selfEvaluation"] != summary_text:
        if template["layout"] == "cn-campus-double":
            sidebar.append({"title": SECTION_LABELS["selfEvaluation"], "kind": "paragraph", "items": [data["selfEvaluation"]]})
        else:
            main.append({"title": SECTION_LABELS["selfEvaluation"], "kind": "paragraph", "items": [data["selfEvaluation"]]})

    if custom_sections:
        if template["layout"] == "cn-campus-double":
            main.extend(custom_sections)
        else:
            main.extend(custom_sections)

    return {"main": main, "sidebar": sidebar}


def _base_resume_css(template: Dict[str, Any]) -> str:
    variant = template["styleVariant"]
    accent = template["accent"]
    accent_soft = _hex_to_rgba(accent, 0.10)
    accent_line = _hex_to_rgba(accent, 0.24)
    sidebar_bg = "#F8FAFC"
    left_col = "29%"
    if variant == "compact":
        heading_size = "27px"
        body_size = "13.4px"
        line_height = "1.55"
        section_gap = "16px"
    elif variant == "academic":
        heading_size = "28px"
        body_size = "13.8px"
        line_height = "1.72"
        section_gap = "18px"
    elif variant == "studio":
        heading_size = "30px"
        body_size = "13.8px"
        line_height = "1.62"
        section_gap = "18px"
    else:
        heading_size = "28px"
        body_size = "13.6px"
        line_height = "1.66"
        section_gap = "18px"
    if template["layout"] == "cn-campus-double":
        sidebar_bg = "#F5F1EC"
        left_col = "31%"
    return f"""
      @page {{ size: A4; margin: 10mm; }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; padding: 0; background: #eef2f6; }}
      body {{
        font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
        color: #111827;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      .resume-sheet {{
        width: 210mm;
        min-height: 297mm;
        margin: 0 auto;
        background: #fff;
        padding: 14mm 15mm 14mm;
      }}
      .resume-header {{
        position: relative;
        padding-bottom: 8px;
        margin-bottom: 14px;
      }}
      .header-name {{
        font-size: {heading_size};
        line-height: 1.15;
        font-weight: 800;
        text-align: center;
        letter-spacing: 0.08em;
      }}
      .header-role {{
        margin-top: 6px;
        text-align: center;
        color: {accent};
        font-size: 14px;
        font-weight: 700;
      }}
      .header-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 6px 18px;
        margin-top: 12px;
        padding-right: 110px;
      }}
      .header-grid.header-grid-no-photo {{
        padding-right: 0;
      }}
      .contact-item {{
        min-width: 0;
        color: #1f2937;
        font-size: 13px;
        line-height: 1.45;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .contact-label {{
        font-weight: 700;
        color: #111827;
      }}
      .header-photo {{
        position: absolute;
        right: 0;
        top: 0;
        width: 86px;
        height: 106px;
        border: 1px solid {accent_line};
        object-fit: cover;
        background: #f8fafc;
      }}
      .single-rule {{
        margin-top: 10px;
        height: 1.2px;
        background: linear-gradient(90deg, {accent}, {accent_line});
      }}
      .section {{
        margin-bottom: {section_gap};
        break-inside: avoid;
      }}
      .section-head {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
      }}
      .section-title {{
        margin: 0;
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: #111827;
      }}
      .section-line {{
        flex: 1;
        height: 1px;
        background: {accent_line};
      }}
      .entry {{
        margin-bottom: 10px;
        break-inside: avoid;
      }}
      .entry-head {{
        display: grid;
        grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) auto;
        gap: 8px;
        align-items: baseline;
      }}
      .entry-title {{
        font-size: {body_size};
        font-weight: 800;
        color: #111827;
      }}
      .entry-role {{
        font-size: {body_size};
        font-weight: 700;
        color: #1f2937;
      }}
      .entry-period {{
        font-size: 13px;
        color: #374151;
        font-weight: 700;
        text-align: right;
        white-space: nowrap;
      }}
      .entry-subtitle {{
        margin-top: 2px;
        font-size: 12.5px;
        color: #4b5563;
      }}
      .entry-list {{
        margin: 5px 0 0;
        padding: 0;
        list-style: none;
      }}
      .entry-list li {{
        position: relative;
        padding-left: 14px;
        margin: 3px 0;
        font-size: {body_size};
        line-height: {line_height};
        color: #1f2937;
      }}
      .entry-list li::before {{
        content: "➤";
        position: absolute;
        left: 0;
        top: 0;
        color: #111827;
        font-size: 11px;
      }}
      .coursework {{
        margin-top: 5px;
        font-size: 13px;
        line-height: 1.6;
        color: #374151;
      }}
      .paragraph {{
        margin: 0;
        white-space: pre-wrap;
        font-size: {body_size};
        line-height: {line_height};
        color: #1f2937;
      }}
      .skill-group {{
        margin-bottom: 7px;
        font-size: {body_size};
        line-height: {line_height};
      }}
      .skill-group strong {{
        color: #111827;
      }}
      .list-block {{
        margin: 0;
        padding-left: 18px;
      }}
      .list-block li {{
        margin: 4px 0;
        font-size: {body_size};
        line-height: {line_height};
        color: #1f2937;
      }}
      .double-shell {{
        display: grid;
        grid-template-columns: {left_col} 1fr;
        gap: 18px;
      }}
      .double-sidebar {{
        background: {sidebar_bg};
        padding: 14px 12px;
        border-right: 1px solid {accent_line};
      }}
      .double-main {{
        min-width: 0;
      }}
      .double-sidebar .section:first-child,
      .double-main .section:first-child {{
        margin-top: 0;
      }}
      .double-header {{
        border-bottom: 1.5px solid {accent};
        margin-bottom: 16px;
      }}
      .double-header .header-grid {{
        grid-template-columns: 1fr;
        padding-right: 0;
      }}
      .double-header .header-name,
      .double-header .header-role {{
        text-align: left;
        letter-spacing: 0.04em;
      }}
    """


def _render_single_layout_html(
    template: Dict[str, Any],
    data: Dict[str, Any],
    sections: Dict[str, List[Dict[str, Any]]],
) -> str:
    basics = data["basics"]
    header = _render_header_html(data, single=True)
    return f"""
    <div class="resume-sheet">
      {header}
      <main>
        {_render_sections_html(sections["main"])}
      </main>
    </div>
    """


def _render_double_layout_html(
    template: Dict[str, Any],
    data: Dict[str, Any],
    sections: Dict[str, List[Dict[str, Any]]],
) -> str:
    header = _render_header_html(data, single=False)
    return f"""
    <div class="resume-sheet">
      {header}
      <div class="double-shell">
        <aside class="double-sidebar">
          {_render_sections_html(sections["sidebar"])}
        </aside>
        <main class="double-main">
          {_render_sections_html(sections["main"])}
        </main>
      </div>
    </div>
    """


def _render_header_html(data: Dict[str, Any], single: bool) -> str:
    basics = data["basics"]
    contact_items = _build_contact_items(basics)
    photo = _photo_html(basics.get("photo", ""))
    grid_class = "header-grid" if photo else "header-grid header-grid-no-photo"
    target_role = data.get("targetRole") or basics.get("title") or basics.get("objective") or ""
    header_class = "resume-header" if single else "resume-header double-header"
    rule = '<div class="single-rule"></div>' if single else ""
    return f"""
      <header class="{header_class}">
        <div class="header-name">{_e(basics.get("name") or "姓名")}</div>
        {f'<div class="header-role">{_e(target_role)}</div>' if target_role else ''}
        <div class="{grid_class}">
          {''.join(contact_items)}
        </div>
        {photo}
        {rule}
      </header>
    """


def _build_contact_items(basics: Dict[str, Any]) -> List[str]:
    items = [
        ("电话/微信", basics.get("phone")),
        ("邮箱", basics.get("email")),
        ("地点", basics.get("location")),
        ("GitHub", basics.get("github")),
        ("个人网站", basics.get("website")),
        ("自媒体", basics.get("media")),
    ]
    rendered = []
    for label, value in items:
        text = str(value or "").strip()
        if not text:
            continue
        rendered.append(
            f'<div class="contact-item"><span class="contact-label">{_e(label)}：</span>{_e(text)}</div>'
        )
    for extra in basics.get("links", []):
        text = str(extra or "").strip()
        if text and text not in {str(v or "").strip() for _, v in items}:
            rendered.append(f'<div class="contact-item">{_e(text)}</div>')
    return rendered


def _photo_html(photo_value: str) -> str:
    photo_value = str(photo_value or "").strip()
    if not photo_value:
        return ""
    src = photo_value
    if os.path.exists(photo_value):
        src = "file://" + photo_value.replace("\\", "/")
    return f'<img class="header-photo" src="{_e(src)}" alt="resume photo" />'


def _render_sections_html(sections: List[Dict[str, Any]]) -> str:
    blocks = []
    for section in sections:
        body = _render_section_body_html(section)
        if not body:
            continue
        blocks.append(
            f'<section class="section"><div class="section-head"><h2 class="section-title">{_e(section["title"])}</h2><div class="section-line"></div></div>{body}</section>'
        )
    return "".join(blocks)


def _render_section_body_html(section: Dict[str, Any]) -> str:
    kind = section.get("kind")
    items = section.get("items") or []
    if kind == "entries":
        return "".join(_entry_html(item) for item in items)
    if kind == "skills":
        return _skills_html(items)
    if kind == "list":
        return _bullet_list_html(items)
    if kind == "paragraph":
        return "".join(_text_html(str(item)) for item in items if str(item).strip())
    return ""


def _entry_html(item: Dict[str, Any]) -> str:
    organization = str(item.get("organization") or "").strip()
    title = str(item.get("title") or "").strip()
    role = str(item.get("role") or "").strip()
    if organization and title and organization != title:
        head_title = title
        head_role = role or organization
    else:
        head_title = title or organization
        head_role = role
    bullets = "".join(f"<li>{_e(str(bullet))}</li>" for bullet in item.get("bullets", []) if str(bullet).strip())
    subtitle_parts = [str(item.get("location") or "").strip()]
    subtitle = " | ".join(part for part in subtitle_parts if part)
    coursework = item.get("coursework") if isinstance(item.get("coursework"), list) else []
    coursework_html = ""
    if coursework:
        coursework_html = f'<div class="coursework"><strong>核心课程：</strong>{_e("、".join(coursework))}</div>'
    subtitle_html = f'<div class="entry-subtitle">{_e(subtitle)}</div>' if subtitle else ""
    role_html = f'<div class="entry-role">{_e(head_role)}</div>' if head_role else '<div class="entry-role"></div>'
    bullet_html = f'<ul class="entry-list">{bullets}</ul>' if bullets else ""
    return (
        '<div class="entry">'
        f'<div class="entry-head"><div class="entry-title">{_e(head_title)}</div>{role_html}<div class="entry-period">{_e(item.get("period", ""))}</div></div>'
        f"{subtitle_html}"
        f"{coursework_html}"
        f"{bullet_html}"
        "</div>"
    )


def _skills_html(items: List[Dict[str, Any]]) -> str:
    blocks = []
    for item in items:
        category = str(item.get("category") or "技能").strip()
        values = [str(value).strip() for value in item.get("items", []) if str(value).strip()]
        if not values:
            continue
        blocks.append(f'<div class="skill-group"><strong>{_e(category)}：</strong>{_e("、".join(values))}</div>')
    return "".join(blocks)


def _bullet_list_html(items: List[Any]) -> str:
    if not items:
        return ""
    return '<ul class="list-block">' + "".join(f"<li>{_e(str(item))}</li>" for item in items if str(item).strip()) + "</ul>"


def _text_html(text: str) -> str:
    return f'<p class="paragraph">{_e(text)}</p>' if text else ""


def _create_pdf_state(doc: fitz.Document, fontfile: str, template: Dict[str, Any]) -> Dict[str, Any]:
    state = {
        "doc": doc,
        "fontfile": fontfile,
        "template": template,
        "accent": _hex_to_rgb(template["accent"]),
        "muted": (0.35, 0.39, 0.45),
        "text": (0.07, 0.09, 0.14),
        "page": None,
        "rect": fitz.Rect(42, 36, 553, 806),
        "y": 36.0,
    }
    _pdf_new_page(state)
    return state


def _pdf_new_page(state: Dict[str, Any]) -> None:
    state["page"] = state["doc"].new_page(width=595, height=842)
    state["y"] = state["rect"].y0


def _render_single_layout_pdf(state: Dict[str, Any], data: Dict[str, Any], sections: Dict[str, List[Dict[str, Any]]]) -> None:
    _pdf_draw_header(state, data, single=True)
    _pdf_render_sections(state, sections["main"])


def _render_double_layout_pdf(state: Dict[str, Any], data: Dict[str, Any], sections: Dict[str, List[Dict[str, Any]]]) -> None:
    _pdf_draw_header(state, data, single=False)
    y_start = state["y"]
    left_rect = fitz.Rect(42, y_start, 197, 806)
    right_rect = fitz.Rect(212, y_start, 553, 806)
    state["page"].draw_rect(left_rect, fill=(0.96, 0.94, 0.92), color=None)
    left_state = _pdf_branch_state(state, left_rect)
    right_state = _pdf_branch_state(state, right_rect)
    _pdf_render_sections(left_state, sections["sidebar"])
    _pdf_render_sections(right_state, sections["main"])


def _pdf_branch_state(root_state: Dict[str, Any], rect: fitz.Rect) -> Dict[str, Any]:
    return {
        "doc": root_state["doc"],
        "fontfile": root_state["fontfile"],
        "template": root_state["template"],
        "accent": root_state["accent"],
        "muted": root_state["muted"],
        "text": root_state["text"],
        "page": root_state["page"],
        "rect": rect,
        "y": rect.y0 + 10,
    }


def _pdf_draw_header(state: Dict[str, Any], data: Dict[str, Any], single: bool) -> None:
    basics = data["basics"]
    target_role = data.get("targetRole") or basics.get("title") or basics.get("objective") or ""
    contact_lines = _build_contact_text_lines(basics, max_columns=3 if single else 1)
    photo_rect = None
    if single and basics.get("photo"):
        photo_rect = fitz.Rect(461, state["y"], 541, state["y"] + 98)
        _pdf_draw_photo(state, basics.get("photo"), photo_rect)
    name_align = 1 if single else 0
    _pdf_write_text(state, basics.get("name") or "姓名", 22, state["text"], bold=True, align=name_align)
    if target_role:
        _pdf_write_text(state, target_role, 11.5, state["accent"], bold=True, align=name_align)

    header_rect = fitz.Rect(state["rect"].x0, state["y"], state["rect"].x1 if not photo_rect else photo_rect.x0 - 12, state["y"] + 60)
    y = state["y"] + 6
    for line in contact_lines:
        text_rect = fitz.Rect(header_rect.x0, y, header_rect.x1, y + 18)
        _pdf_insert_textbox(state, text_rect, line, 9.4, state["text"], align=0)
        y += 15
    state["y"] = max(y + 8, (photo_rect.y1 + 8) if photo_rect else y + 8)
    line_y = state["y"]
    if single:
        state["page"].draw_line((state["rect"].x0, line_y), (state["rect"].x1, line_y), color=state["accent"], width=1.0)
    else:
        state["page"].draw_line((state["rect"].x0, line_y), (state["rect"].x1, line_y), color=state["accent"], width=1.2)
    state["y"] = line_y + 12


def _pdf_draw_photo(state: Dict[str, Any], photo_value: str, rect: fitz.Rect) -> None:
    try:
        photo_value = str(photo_value or "").strip()
        if not photo_value:
            return
        stream = None
        filename = None
        if photo_value.startswith("data:image/"):
            _, encoded = photo_value.split(",", 1)
            stream = base64.b64decode(encoded)
        elif os.path.exists(photo_value):
            filename = photo_value
        else:
            return
        state["page"].draw_rect(rect, color=state["accent"], width=0.6)
        state["page"].insert_image(rect, stream=stream, filename=filename, keep_proportion=False)
    except Exception:
        state["page"].draw_rect(rect, color=state["accent"], width=0.6)


def _pdf_render_sections(state: Dict[str, Any], sections: List[Dict[str, Any]]) -> None:
    for section in sections:
        if not _section_has_content(section):
            continue
        _pdf_section_title(state, section["title"])
        kind = section.get("kind")
        if kind == "entries":
            for item in section.get("items", []):
                _pdf_entry(state, item)
        elif kind == "skills":
            for item in section.get("items", []):
                line = f"{item.get('category') or '技能'}：{'、'.join(str(v).strip() for v in item.get('items', []) if str(v).strip())}"
                _pdf_write_text(state, line, 9.4, state["text"])
        elif kind == "list":
            for item in section.get("items", []):
                _pdf_write_text(state, f"• {item}", 9.3, state["text"])
        elif kind == "paragraph":
            for item in section.get("items", []):
                _pdf_write_text(state, str(item), 9.4, state["text"])
        state["y"] += 4


def _pdf_section_title(state: Dict[str, Any], title: str) -> None:
    _pdf_ensure_space(state, 22)
    title_rect = fitz.Rect(state["rect"].x0, state["y"], state["rect"].x0 + 100, state["y"] + 16)
    _pdf_insert_textbox(state, title_rect, title, 10.8, state["text"], bold=True)
    line_y = state["y"] + 12
    state["page"].draw_line((state["rect"].x0, line_y), (state["rect"].x1, line_y), color=state["accent"], width=0.7)
    state["y"] += 18


def _pdf_entry(state: Dict[str, Any], item: Dict[str, Any]) -> None:
    _pdf_ensure_space(state, 40)
    title = str(item.get("title") or "").strip()
    organization = str(item.get("organization") or "").strip()
    role = str(item.get("role") or "").strip()
    if organization and title and organization != title:
        title_text = title
        role_text = role or organization
    else:
        title_text = title or organization
        role_text = role
    period = str(item.get("period") or "").strip()
    left_width = max(160, state["rect"].width - 90)
    head_rect = fitz.Rect(state["rect"].x0, state["y"], state["rect"].x0 + left_width, state["y"] + 16)
    _pdf_insert_textbox(state, head_rect, title_text, 9.7, state["text"], bold=True)
    if role_text:
        role_rect = fitz.Rect(state["rect"].x0 + 170, state["y"], state["rect"].x1 - 80, state["y"] + 16)
        _pdf_insert_textbox(state, role_rect, role_text, 9.5, state["text"], bold=True)
    if period:
        period_rect = fitz.Rect(state["rect"].x1 - 84, state["y"], state["rect"].x1, state["y"] + 16)
        _pdf_insert_textbox(state, period_rect, period, 9.2, state["muted"], bold=True, align=2)
    state["y"] += 14
    coursework = item.get("coursework") if isinstance(item.get("coursework"), list) else []
    if coursework:
        _pdf_write_text(state, f"核心课程：{'、'.join(str(v) for v in coursework if str(v).strip())}", 8.9, state["muted"])
    for bullet in item.get("bullets", []):
        _pdf_write_text(state, f"• {bullet}", 9.2, state["text"])
    state["y"] += 2


def _pdf_write_text(
    state: Dict[str, Any],
    text: str,
    size: float,
    color: Tuple[float, float, float],
    bold: bool = False,
    align: int = 0,
) -> None:
    text = str(text or "").strip()
    if not text:
        return
    height = _estimate_text_height(text, size, state["rect"].width)
    _pdf_ensure_space(state, height + 4)
    rect = fitz.Rect(state["rect"].x0, state["y"], state["rect"].x1, state["y"] + height + 2)
    _pdf_insert_textbox(state, rect, text, size, color, bold=bold, align=align)
    state["y"] += height + 2


def _pdf_insert_textbox(
    state: Dict[str, Any],
    rect: fitz.Rect,
    text: str,
    size: float,
    color: Tuple[float, float, float],
    bold: bool = False,
    align: int = 0,
) -> None:
    if state["fontfile"]:
        state["page"].insert_textbox(
            rect,
            text,
            fontsize=size,
            fontname="chinafont",
            fontfile=state["fontfile"],
            color=color,
            align=align,
            lineheight=1.4,
        )
        return
    fontname = "helvB" if bold else "helv"
    state["page"].insert_textbox(rect, text, fontsize=size, fontname=fontname, color=color, align=align, lineheight=1.4)


def _pdf_ensure_space(state: Dict[str, Any], height: float) -> None:
    if state["y"] + height <= state["rect"].y1:
        return
    _pdf_new_page(state)


def _section_has_content(section: Dict[str, Any]) -> bool:
    items = section.get("items") or []
    if section.get("kind") == "paragraph":
        return any(str(item).strip() for item in items)
    if section.get("kind") == "skills":
        return any(item.get("items") for item in items if isinstance(item, dict))
    return bool(items)


def _build_contact_text_lines(basics: Dict[str, Any], max_columns: int) -> List[str]:
    texts = []
    for label, value in [
        ("电话/微信", basics.get("phone")),
        ("邮箱", basics.get("email")),
        ("地点", basics.get("location")),
        ("GitHub", basics.get("github")),
        ("个人网站", basics.get("website")),
        ("自媒体", basics.get("media")),
    ]:
        text = str(value or "").strip()
        if text:
            texts.append(f"{label}: {text}")
    extras = [str(item).strip() for item in basics.get("links", []) if str(item).strip()]
    for item in extras:
        if item not in texts:
            texts.append(item)
    lines = []
    for index in range(0, len(texts), max_columns):
        lines.append("   |   ".join(texts[index:index + max_columns]))
    return lines


def _estimate_text_height(text: str, size: float, width: float) -> float:
    chars_per_line = max(10, int(width / max(5.2, size * 0.78)))
    lines = 0
    for raw_line in str(text).splitlines() or [""]:
        segment = raw_line or " "
        lines += max(1, math.ceil(len(segment) / chars_per_line))
    return max(size + 2, lines * (size * 1.36))


def _find_chinese_font() -> str:
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _safe_get(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return None


def _coalesce_from_dict(source: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return ""


def _join_nonempty(items: Iterable[Any], sep: str) -> str:
    return sep.join(str(item).strip() for item in items if str(item or "").strip())


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    return cleaned or "resume"


def _hex_to_rgb(value: str) -> Tuple[float, float, float]:
    raw = value.lstrip("#")
    if len(raw) != 6:
        return (0.15, 0.39, 0.92)
    return tuple(int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4))  # type: ignore[return-value]


def _hex_to_rgba(value: str, alpha: float) -> str:
    raw = value.lstrip("#")
    if len(raw) != 6:
        return f"rgba(37,99,235,{alpha})"
    red, green, blue = (int(raw[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)
