import base64
import logging
import re
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from app.services.siliconflow_client import (
    SiliconFlowClient,
    create_resume_layout_client,
    extract_json_object,
)

logger = logging.getLogger(__name__)

CANONICAL_BLOCKS: List[Dict[str, str]] = [
    {"key": "header", "name": "基本信息"},
    {"key": "education", "name": "教育背景"},
    {"key": "campus_experience", "name": "校园/社团经历"},
    {"key": "practical_experience", "name": "实习/工作经历"},
    {"key": "projects", "name": "项目经历"},
    {"key": "skills", "name": "技能"},
    {"key": "certificates", "name": "证书/奖项"},
    {"key": "self_evaluation", "name": "自我评价"},
    {"key": "additional_content", "name": "其他信息"},
]

SECTION_ALIAS_MAP: Dict[str, List[str]] = {
    "header": ["基本信息", "个人信息", "联系方式", "联系信息", "抬头"],
    "education": ["教育背景", "教育经历", "教育", "学历背景", "课程经历", "院校信息"],
    "campus_experience": ["校园经历", "校园/社团经历", "社团经历", "学生工作", "校园实践", "志愿经历"],
    "practical_experience": ["实习经历", "工作经历", "工作/实习经历", "实习", "工作", "运营经历"],
    "projects": ["项目经历", "项目经验", "科研项目", "项目", "作品经历", "项目与运营经历"],
    "skills": ["技能", "专业技能", "技术栈", "技能清单", "技能标签", "工具技能"],
    "certificates": ["证书", "证书/奖项", "奖项", "获奖", "荣誉", "资格证", "荣誉奖励"],
    "self_evaluation": ["自我评价", "个人总结", "个人优势", "个人简介", "个人陈述"],
    "additional_content": ["其他信息", "附加信息", "补充信息", "其他"],
}

HEADER_KEYWORDS = ["电话", "手机", "邮箱", "微信", "github", "linkedin", "求职意向", "地址"]
CAMPUS_KEYWORDS = ["学生会", "社团", "校园", "班长", "团支书", "志愿者", "宣传部", "组织部"]
PRACTICAL_KEYWORDS = ["实习", "工作", "公司", "任职", "就职", "运营", "专员", "经理", "负责店铺", "负责账号"]
PROJECT_KEYWORDS = ["项目", "系统", "平台", "课题", "毕设", "毕业设计", "作品", "开发", "上线", "负责人", "主负责人"]
SKILL_KEYWORDS = ["技能", "熟悉", "掌握", "精通", "了解", "vue", "react", "typescript", "javascript", "python", "java", "sql", "excel", "erp"]
CERTIFICATE_KEYWORDS = ["证书", "奖项", "获奖", "荣誉", "奖学金", "资格", "一等奖", "二等奖", "三等奖", "cet", "四级", "六级"]
SUMMARY_KEYWORDS = ["自我评价", "总结", "优势", "性格", "简介"]
EDUCATION_KEYWORDS = ["大学", "学院", "本科", "硕士", "博士", "gpa", "主修课程", "院校"]
SKILL_LINE_PREFIXES = ["技能", "专业技能", "工具", "办公", "软件", "平台", "语言能力", "语言", "外贸"]


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join((page.get_text("text") or "") for page in doc).strip()


def truncate_for_llm(text: str, max_chars: int = 12000) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3) :]
    return f"{head}\n...\n{tail}"


def fallback_extract_sections(resume_text: str) -> List[Dict[str, str]]:
    text = (resume_text or "").strip()
    if not text:
        return [{"name": "其他信息", "content": "未能从 PDF 中提取到足够文本，请检查文件是否为图片扫描件。"}]

    sections: List[Dict[str, str]] = []
    pending_heading_keys: List[str] = []
    current_key: Optional[str] = None
    current_lines: List[str] = []
    previous_line = ""

    def flush_current() -> None:
        nonlocal current_key, current_lines
        content = "\n".join(item for item in current_lines if item).strip()
        if content:
            sections.append({"name": _canonical_name(current_key or "additional_content"), "content": content})
        current_key = None
        current_lines = []

    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line or _looks_like_resume_banner(line):
            continue

        detected_key = _match_canonical_key(line)
        if detected_key and _looks_like_section_heading(line, detected_key):
            flush_current()
            pending_heading_keys.append(detected_key)
            previous_line = line
            continue

        guessed_key = _guess_key_from_content(line)
        guessed_key = _refine_guessed_key(line, guessed_key, current_key, previous_line)
        if pending_heading_keys:
            flush_current()
            current_key = _select_pending_heading_key(pending_heading_keys, guessed_key)
            current_lines = [line]
            pending_heading_keys = []
            previous_line = line
            continue

        if current_key is None:
            current_key = "header" if _looks_like_header(line) else guessed_key
            current_lines = [line]
            previous_line = line
            continue

        if _should_start_new_section(current_key, guessed_key, line, previous_line):
            flush_current()
            current_key = guessed_key
            current_lines = [line]
        else:
            current_lines.append(line)
        previous_line = line

    flush_current()
    cleaned = _remove_heading_only_sections(
        _merge_adjacent_sections([item for item in sections if item.get("content", "").strip()])
    )
    return cleaned or [{"name": "其他信息", "content": truncate_for_llm(text, max_chars=4000)}]


def llm_extract_sections(client: SiliconFlowClient, resume_text: str) -> Any:
    truncated = truncate_for_llm(resume_text)
    system = (
        "你是中文简历解析助手。"
        "请把简历文本拆成模块，严格输出 JSON，不要输出 JSON 以外的解释。"
    )
    user = f"""
请阅读下面的简历文本，识别主要板块并尽量保留原文：

输出 JSON：
{{
  "sections": [
    {{
      "name": "模块名称",
      "content": "对应原文内容"
    }}
  ],
  "notes": "不确定信息"
}}

简历文本：
```text
{truncated}
```
"""
    content = client.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1800,
    )
    parsed = extract_json_object(content)
    if isinstance(parsed, dict) and isinstance(parsed.get("sections"), list):
        return parsed["sections"]
    return parsed


def render_first_page_data_url(pdf_bytes: bytes, zoom: float = 1.6) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("PDF has no pages")
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    encoded = base64.b64encode(pix.tobytes("png")).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def analyze_resume_layout(pdf_bytes: bytes, resume_text: str) -> Optional[Dict[str, Any]]:
    try:
        client = create_resume_layout_client(timeout_seconds=18, allow_model_fallback=False)
        image_url = render_first_page_data_url(pdf_bytes)
    except Exception:
        logger.exception("resume_layout_prepare_failed")
        return None

    canonical_text = "、".join(item["name"] for item in CANONICAL_BLOCKS)
    user_text = truncate_for_llm(resume_text, max_chars=5000)
    system = "你是中文简历版式识别助手。根据截图和文本把内容归入固定板块，严格输出 JSON。"
    user_content: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"请根据简历截图和文本，把内容归入以下板块：{canonical_text}。"
                "如果不确定，请归入最接近板块；完全无法归类时归入其他信息。"
                "返回 JSON："
                '{"recognitionMode":"vision-layout","layoutConfidence":0.0,"layoutWarnings":[],"blocks":[{"key":"education","name":"教育背景","content":"..."}]}'
                f"\n\n简历文本参考：\n{user_text}"
            ),
        },
        {"type": "image_url", "image_url": {"url": image_url}},
    ]
    try:
        content = client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=1800,
        )
    except Exception as exc:
        logger.warning("resume_layout_analysis_failed error=%s", str(exc)[:300])
        return None

    parsed = extract_json_object(content)
    return parsed if isinstance(parsed, dict) else None


def normalize_optimize_sections(
    resume_text: str,
    sections: Any,
    layout_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_sections = _ensure_section_list(sections, resume_text)
    grouped: Dict[str, List[str]] = {item["key"]: [] for item in CANONICAL_BLOCKS}

    for section in raw_sections:
        content = str(section.get("content") or "").strip()
        if not content:
            continue
        section_name = str(section.get("name") or "")
        key = _match_canonical_key(section_name) or _guess_key_from_content(content)
        grouped[key].append(content)

    if isinstance(layout_analysis, dict):
        for block in layout_analysis.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            key = str(block.get("key") or "").strip()
            content = str(block.get("content") or "").strip()
            if key in grouped and content:
                grouped[key] = _merge_contents(grouped[key], [content])

    normalized_blocks: List[Dict[str, Any]] = []
    normalized_sections: List[Dict[str, str]] = []
    for block in CANONICAL_BLOCKS:
        content = "\n".join(item for item in grouped[block["key"]] if item).strip()
        if not content:
            continue
        normalized_blocks.append(
            {
                "key": block["key"],
                "name": block["name"],
                "content": content,
                "items": _content_items(content),
            }
        )
        normalized_sections.append({"name": block["name"], "content": content})

    if not normalized_sections:
        normalized_sections = fallback_extract_sections(resume_text)
        normalized_blocks = [
            {
                "key": _match_canonical_key(item["name"]) or "additional_content",
                "name": item["name"],
                "content": item["content"],
                "items": _content_items(item["content"]),
            }
            for item in normalized_sections
        ]

    warnings: List[str] = []
    confidence = 0.62
    recognition_mode = "text-first"
    if isinstance(layout_analysis, dict):
        recognition_mode = str(layout_analysis.get("recognitionMode") or "hybrid")
        confidence = float(layout_analysis.get("layoutConfidence") or 0.78)
        warnings = [str(item).strip() for item in layout_analysis.get("layoutWarnings") or [] if str(item).strip()]

    return {
        "sections": normalized_sections,
        "normalizedBlocks": normalized_blocks,
        "recognitionMode": recognition_mode,
        "layoutConfidence": confidence,
        "layoutWarnings": warnings,
    }


def _ensure_section_list(sections: Any, resume_text: str) -> List[Dict[str, str]]:
    if isinstance(sections, list):
        items: List[Dict[str, str]] = []
        for index, section in enumerate(sections):
            if isinstance(section, dict):
                name = str(section.get("name") or section.get("title") or f"模块 {index + 1}").strip()
                content = str(section.get("content") or section.get("text") or "").strip()
            else:
                name = f"模块 {index + 1}"
                content = str(section or "").strip()
            if content:
                items.append({"name": name, "content": content})
        if items:
            return items
    return fallback_extract_sections(resume_text)


def _canonical_name(key: str) -> str:
    for block in CANONICAL_BLOCKS:
        if block["key"] == key:
            return block["name"]
    return "其他信息"


def _match_canonical_key(name: str) -> Optional[str]:
    normalized = _normalize_heading_text(name)
    if not normalized:
        return None
    for key, aliases in SECTION_ALIAS_MAP.items():
        for alias in aliases:
            alias_normalized = _normalize_heading_text(alias)
            if alias_normalized and alias_normalized in normalized:
                return key
    return None


def _looks_like_section_heading(line: str, key: str) -> bool:
    normalized = _normalize_heading_text(line)
    if not normalized or len(normalized) > 20:
        return False
    aliases = SECTION_ALIAS_MAP.get(key) or []
    return normalized in {_normalize_heading_text(alias) for alias in aliases if alias}


def _guess_key_from_content(content: str) -> str:
    text = (content or "").strip()
    if not text:
        return "additional_content"
    if _contains_any(text, SUMMARY_KEYWORDS) or _looks_like_self_evaluation_line(text):
        return "self_evaluation"
    if _looks_like_skill_line(text) and not _contains_any(text, CERTIFICATE_KEYWORDS):
        return "skills"
    if _contains_any(text, CERTIFICATE_KEYWORDS):
        return "certificates"
    if _contains_any(text, SKILL_KEYWORDS) and not _contains_any(text, PRACTICAL_KEYWORDS):
        return "skills"
    if _contains_any(text, CAMPUS_KEYWORDS):
        return "campus_experience"
    if _contains_any(text, EDUCATION_KEYWORDS) and not _contains_any(text, PROJECT_KEYWORDS):
        return "education"
    if _contains_any(text, PRACTICAL_KEYWORDS):
        return "practical_experience"
    if _contains_any(text, PROJECT_KEYWORDS):
        return "projects"
    if _looks_like_header(text):
        return "header"
    return "additional_content"


def _refine_guessed_key(line: str, guessed_key: str, current_key: Optional[str], previous_line: str) -> str:
    if _looks_like_profile_line(line):
        return "header"
    if _looks_like_self_evaluation_line(line):
        return "self_evaluation"
    if guessed_key != "additional_content":
        return guessed_key
    if _looks_like_award_line(line):
        return "certificates"
    if _looks_like_education_line(line):
        return "education"
    if _looks_like_project_start(line):
        return "projects"
    if _looks_like_experience_start(line, previous_line):
        return "practical_experience"
    if current_key == "self_evaluation" and re.search(r"\d{4}[./年]\d{1,2}", line):
        return "practical_experience"
    return guessed_key


def _normalize_heading_text(value: str) -> str:
    return re.sub(r"[\s:：|·•—\-_/]+", "", value or "").lower()


def _contains_any(text: str, keywords: List[str]) -> bool:
    lowered = (text or "").lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _looks_like_header(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if _contains_any(compact, CAMPUS_KEYWORDS + PRACTICAL_KEYWORDS + PROJECT_KEYWORDS + CERTIFICATE_KEYWORDS):
        return False
    return any(
        [
            any(keyword in compact.lower() for keyword in HEADER_KEYWORDS),
            bool(re.search(r"1[3-9]\d{9}", compact)),
            "@" in compact,
            bool(re.fullmatch(r"[\u4e00-\u9fa5]{2,6}", compact[:6])),
        ]
    )


def _looks_like_profile_line(line: str) -> bool:
    compact = re.sub(r"\s+", "", line or "")
    return any(
        [
            compact.startswith("求职意向"),
            compact.startswith("电话"),
            compact.startswith("手机"),
            compact.startswith("邮箱"),
            compact.startswith("微信"),
            compact.startswith("地址"),
            compact.startswith("专业："),
            compact.startswith("专业:"),
        ]
    )


def _looks_like_self_evaluation_line(line: str) -> bool:
    compact = re.sub(r"\s+", "", line or "")
    return any(
        [
            compact.startswith("项目领导潜力"),
            compact.startswith("快速学习与适应"),
            compact.startswith("数据驱动决策"),
            compact.startswith("个人优势"),
            compact.startswith("个人总结"),
            compact.startswith("自我评价"),
            bool(re.search(r"(毕业|应届).{0,10}(具备|拥有|能够|希望)", compact)),
            "对行业充满热情" in compact,
            "可快速适应岗位" in compact,
            "主动学习提升" in compact,
            compact.endswith("创造价值。"),
        ]
    )


def _looks_like_skill_line(line: str) -> bool:
    compact = re.sub(r"\s+", "", line or "")
    if any(compact.startswith(f"{prefix}：") or compact.startswith(f"{prefix}:") for prefix in SKILL_LINE_PREFIXES):
        return True
    return False


def _merge_contents(existing: List[str], incoming: List[str]) -> List[str]:
    merged = [item for item in existing if item]
    for item in incoming:
        if item and item not in merged:
            merged.append(item)
    return merged


def _content_items(content: str) -> List[Dict[str, str]]:
    lines = [line.strip("•·- \t") for line in re.split(r"[\r\n]+", content or "") if line.strip("•·- \t")]
    items: List[Dict[str, str]] = []
    for line in lines[:8]:
        title, detail = _split_title_and_detail(line)
        items.append({"title": title, "content": detail})
    return items


def _split_title_and_detail(line: str) -> tuple[str, str]:
    for sep in ["：", ":", "|", "·", "-", "—"]:
        if sep in line:
            left, right = line.split(sep, 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                return left[:40], right
    return line[:40], line


def _select_pending_heading_key(pending_heading_keys: List[str], guessed_key: str) -> str:
    if guessed_key in pending_heading_keys:
        return guessed_key
    return pending_heading_keys[-1] if pending_heading_keys else guessed_key


def _should_start_new_section(current_key: str, guessed_key: str, line: str, previous_line: str) -> bool:
    if guessed_key == current_key or guessed_key == "additional_content":
        return False
    if guessed_key == "header" and _looks_like_profile_line(line):
        return True
    if current_key in {"header", "self_evaluation", "additional_content"} and _looks_like_strong_block_start(line, guessed_key):
        return True
    if guessed_key == "self_evaluation" and current_key != "self_evaluation" and _looks_like_self_evaluation_line(line):
        return True
    if current_key in {"education", "certificates"} and guessed_key in {"practical_experience", "projects"} and _looks_like_strong_block_start(line, guessed_key):
        return True
    if guessed_key == "skills" and current_key != "skills" and _looks_like_strong_block_start(line, guessed_key):
        return True
    if guessed_key in {"education", "certificates"} and _looks_like_strong_block_start(line, guessed_key):
        return True
    if current_key == "projects" and guessed_key == "practical_experience" and _looks_like_experience_start(line, previous_line):
        return True
    if current_key == "practical_experience" and guessed_key == "projects" and _looks_like_project_start(line):
        return True
    if current_key == "campus_experience" and guessed_key in {"practical_experience", "projects"} and _looks_like_strong_block_start(line, guessed_key):
        return True
    return False


def _looks_like_strong_block_start(line: str, guessed_key: str) -> bool:
    if guessed_key == "education":
        return _looks_like_education_line(line)
    if guessed_key == "certificates":
        return _looks_like_award_line(line)
    if guessed_key == "practical_experience":
        return _looks_like_experience_start(line, "")
    if guessed_key == "projects":
        return _looks_like_project_start(line)
    if guessed_key == "campus_experience":
        return _contains_any(line, CAMPUS_KEYWORDS)
    if guessed_key == "skills":
        return _looks_like_skill_line(line) or _contains_any(line, SKILL_KEYWORDS)
    return False


def _looks_like_education_line(line: str) -> bool:
    return _contains_any(line, EDUCATION_KEYWORDS) or bool(
        re.search(r"\d{4}[./年]\d{1,2}.*(大学|学院|本科|硕士|博士)", line)
    )


def _looks_like_award_line(line: str) -> bool:
    return _contains_any(line, CERTIFICATE_KEYWORDS)


def _looks_like_project_start(line: str) -> bool:
    return _contains_any(line, PROJECT_KEYWORDS) or bool(re.search(r"(项目|系统|平台|作品|课题).{0,12}(负责人|主理|组长)", line))


def _looks_like_experience_start(line: str, previous_line: str) -> bool:
    if _contains_any(line, ["实习", "工作", "公司", "任职", "就职", "实习生", "专员", "经理"]):
        return True
    if bool(re.search(r"\d{4}[./年]\d{1,2}.*(\d{4}[./年]\d{1,2}|至今|现在)", line)):
        return True
    if re.search(r"(公司|有限公司|科技|传媒|运营|实习生|专员|经理)$", line):
        return True
    return bool(previous_line and re.search(r"\d{4}[./年]\d{1,2}.*(\d{4}[./年]\d{1,2}|至今|现在)", previous_line))


def _looks_like_resume_banner(line: str) -> bool:
    compact = re.sub(r"\s+", "", line or "").lower()
    return compact in {"个人简历", "personalresume", "resume", "curriculumvitae", "cv"}


def _merge_adjacent_sections(sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    for section in sections:
        name = str(section.get("name") or "").strip()
        content = str(section.get("content") or "").strip()
        if not name or not content:
            continue
        if merged and merged[-1]["name"] == name:
            merged[-1]["content"] = f"{merged[-1]['content']}\n{content}".strip()
        else:
            merged.append({"name": name, "content": content})
    return merged


def _remove_heading_only_sections(sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    for section in sections:
        content = str(section.get("content") or "").strip()
        normalized = _normalize_heading_text(content)
        if normalized and len(normalized) <= 20 and any(
            normalized == _normalize_heading_text(alias)
            for aliases in SECTION_ALIAS_MAP.values()
            for alias in aliases
        ):
            continue
        cleaned.append(section)
    return cleaned
