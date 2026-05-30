import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.db.repo import ResumeRepo
from app.services.career_flow import (
    fallback_career_plan,
    generate_application_strategy,
    generate_career_plan,
    generate_interview_prepare,
    normalize_student_profile,
)
from app.services.recruitment_match import llm_match_resume_to_job, rule_match_resume_to_job
from app.services.public_research import attach_sources
from app.services.resume_optimize import (
    estimate_optimize_prompt_input,
    extract_job_requirements,
    fallback_optimize_resume_for_job,
    fallback_extract_job_requirements,
    normalize_requirements,
    optimize_resume_for_job,
)
from app.services.resume_export import (
    get_template,
    list_resume_templates,
    render_resume_pdf,
    structure_resume_data,
)
from app.services.resume_ocr import (
    analyze_resume_layout,
    extract_text_from_pdf_bytes,
    fallback_extract_sections,
    llm_extract_sections,
    normalize_optimize_sections,
)
from app.services.siliconflow_client import SiliconFlowClient
from app.services.suggestions import llm_generate_suggestions


router = APIRouter()
logger = logging.getLogger(__name__)


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        logger.warning("invalid_integer_env name=%s value=%s default=%s", name, raw, default)
        return default


OCR_LLM_TIMEOUT_SECONDS = 12
MATCH_LLM_TIMEOUT_SECONDS = 15
CAREER_PLAN_LLM_TIMEOUT_SECONDS = 12
RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS = _env_int("RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS", 75, minimum=15)
RESUME_OPTIMIZE_LLM_RETRIES = _env_int("RESUME_OPTIMIZE_LLM_RETRIES", 0, minimum=0)
OCR_ROUTE_TIMEOUT_SECONDS = _env_int("OCR_ROUTE_TIMEOUT_SECONDS", 45, minimum=OCR_LLM_TIMEOUT_SECONDS + 5)
MATCH_ROUTE_TIMEOUT_SECONDS = 22
CAREER_PLAN_ROUTE_TIMEOUT_SECONDS = 18
RESUME_OPTIMIZE_ROUTE_TIMEOUT_SECONDS = _env_int(
    "RESUME_OPTIMIZE_ROUTE_TIMEOUT_SECONDS",
    max(110, RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS + 30),
    minimum=RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS + 5,
)
RESUME_OPTIMIZE_FAST_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
ALLOWED_CAREER_GRADES = {"大一", "大二"}


@dataclass
class RequestContext:
    user_id: str
    user_role: str


def _request_context(
    x_user_id: Optional[str],
    x_user_role: Optional[str],
) -> RequestContext:
    user_id = (x_user_id or "demo-student").strip() or "demo-student"
    normalized_role = (x_user_role or "student").strip().lower()
    if normalized_role not in {"student", "admin", "operator"}:
        normalized_role = "student"
    return RequestContext(user_id=user_id, user_role=normalized_role)


def _ensure_admin_access(context: RequestContext) -> None:
    if context.user_role not in {"admin", "operator"}:
        _raise_api_error(
            403,
            "admin_access_required",
            "当前页面仅支持老师、运营或管理员查看",
            {"userRole": context.user_role},
            retryable=False,
        )


def _log_ai_call(
    repo: ResumeRepo,
    *,
    feature: str,
    endpoint: str,
    status: str,
    started_at: float,
    context: RequestContext,
    error_message: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        repo.log_ai_call(
            feature=feature,
            endpoint=endpoint,
            status=status,
            duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            error_message=error_message[:500],
            user_id=context.user_id,
            user_role=context.user_role,
            metadata=metadata,
        )
    except Exception:
        logger.exception("ai_call_log_failed feature=%s endpoint=%s", feature, endpoint)


class ResumeIdRequest(BaseModel):
    resumeId: int


class JobProfile(BaseModel):
    title: str = Field(..., description="Job title")
    responsibilities: str = Field(..., description="Job description")
    must_haves: List[str] = Field(default_factory=list, description="Required qualifications")
    nice_to_haves: List[str] = Field(default_factory=list, description="Preferred qualifications")
    experience_years: str = Field(default="", description="Experience requirement")
    keywords: List[str] = Field(default_factory=list, description="Job keywords")


class MatchRequest(BaseModel):
    resumeId: int
    jobProfile: JobProfile


class BatchMatchRequest(BaseModel):
    resumeIds: List[int]
    jobProfile: JobProfile
    timeoutSeconds: int = Field(default=90, ge=10, le=300, description="Batch timeout seconds")


class JobExtractRequirementsRequest(BaseModel):
    jobDescription: str = Field(..., description="Raw job description")


class ResumeOptimizeRequest(BaseModel):
    resumeId: Optional[int] = Field(default=None, description="Parsed resume ID")
    rawResumeText: str = Field(default="", description="Raw resume text")
    sections: Any = Field(default=None, description="Resume sections")
    jobDescription: str = Field(default="", description="Target job description")
    jobRequirements: Dict[str, Any] = Field(default_factory=dict, description="Extracted job requirements")
    model: str = Field(default="", description="Optional model name")


class CareerPlanRequest(BaseModel):
    major: str = Field(default="", description="Major")
    grade: str = Field(default="", description="Grade")
    skills: List[str] = Field(default_factory=list, description="Skills")
    experience: str = Field(default="", description="Experience")
    targetCity: str = Field(default="", description="Target city")
    interests: List[str] = Field(default_factory=list, description="Interests")


class ApplicationStrategyRequest(BaseModel):
    studentProfile: Dict[str, Any] = Field(default_factory=dict, description="Student profile")
    jobDescription: str = Field(default="", description="Raw job description")
    jobRequirements: Dict[str, Any] = Field(default_factory=dict, description="Extracted job requirements")
    matchResult: Dict[str, Any] = Field(default_factory=dict, description="Match result")
    resumeId: Optional[int] = Field(default=None, description="Optional resume ID")
    rawResumeText: str = Field(default="", description="Optional optimized resume text")
    sections: Any = Field(default=None, description="Optional optimized resume sections")
    structuredResume: Dict[str, Any] = Field(default_factory=dict, description="Optional optimized structured resume")


class InterviewPrepareRequest(BaseModel):
    studentProfile: Dict[str, Any] = Field(default_factory=dict, description="Student profile")
    jobDescription: str = Field(default="", description="Raw job description")
    jobRequirements: Dict[str, Any] = Field(default_factory=dict, description="Extracted job requirements")
    matchResult: Dict[str, Any] = Field(default_factory=dict, description="Match result")
    resumeId: Optional[int] = Field(default=None, description="Optional resume ID")
    rawResumeText: str = Field(default="", description="Raw resume text")
    sections: Any = Field(default=None, description="Resume sections")
    structuredResume: Dict[str, Any] = Field(default_factory=dict, description="Optional optimized structured resume")


class ResumeStructureRequest(BaseModel):
    resumeData: Dict[str, Any] = Field(default_factory=dict, description="Resume data")


class ResumeExportPdfRequest(BaseModel):
    templateId: str = Field(..., description="Template ID")
    structuredResume: Dict[str, Any] = Field(default_factory=dict, description="Structured resume")
    resumeData: Dict[str, Any] = Field(default_factory=dict, description="Resume data")
    filename: str = Field(default="", description="Download filename")


class OcrResponse(BaseModel):
    resumeId: int
    extractedTextPreview: str
    sections: Any
    recognitionMode: str = "text-first"
    layoutConfidence: float = 0.0
    layoutWarnings: List[str] = Field(default_factory=list)
    normalizedBlocks: List[Dict[str, Any]] = Field(default_factory=list)


class SuggestionsResponse(BaseModel):
    resumeId: int
    overall_summary: str
    items: List[Dict[str, Any]]


class MatchResponse(BaseModel):
    resumeId: int
    jobProfileId: int
    matchResultId: int
    match_score: int
    recommendation: str
    result: Dict[str, Any]


def _error_payload(stage: str, message: str, detail: Any, retryable: bool = True) -> Dict[str, Any]:
    return {"stage": stage, "message": message, "detail": detail, "retryable": retryable}


def _raise_api_error(status_code: int, stage: str, message: str, detail: Any, retryable: bool = True) -> None:
    raise HTTPException(status_code=status_code, detail=_error_payload(stage, message, detail, retryable))


def _log_stage(route: str, stage: str, started_at: float, **fields: Any) -> None:
    extra = " ".join(f"{key}={fields[key]}" for key in sorted(fields) if fields[key] is not None)
    logger.info(
        "%s stage=%s elapsed_ms=%s%s",
        route,
        stage,
        int((time.monotonic() - started_at) * 1000),
        f" {extra}" if extra else "",
    )


def _preview(text: str, max_len: int = 800) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...\n（省略部分内容）"


def _normalize_status(recommendation: Any, score: int) -> str:
    value = str(recommendation or "").strip()
    if value in {"强烈推荐", "推荐面试", "备选", "不匹配"}:
        return value
    if score >= 85:
        return "强烈推荐"
    if score >= 75:
        return "推荐面试"
    if score >= 55:
        return "备选"
    return "不匹配"


def _normalize_match_result(result: Dict[str, Any]) -> Dict[str, Any]:
    try:
        score = int(result.get("total_score", result.get("match_score", 0)))
    except Exception:
        score = 0
    score = max(0, min(100, score))
    result["total_score"] = score
    result["match_score"] = score
    result["recommendation_level"] = _normalize_status(result.get("recommendation_level") or result.get("recommendation"), score)
    result["recommendation"] = result["recommendation_level"]

    for key in ["skill_score", "experience_score", "education_score"]:
        try:
            result[key] = max(0, min(100, int(result.get(key, 0))))
        except Exception:
            result[key] = 0

    for key in [
        "must_have_hits",
        "strengths",
        "gaps",
        "scoring_basis",
        "resume_evidence",
        "interview_questions",
    ]:
        if not isinstance(result.get(key), list):
            result[key] = []
    if "evidence" not in result:
        result["evidence"] = result["resume_evidence"]
    if not isinstance(result.get("candidate_name"), str):
        result["candidate_name"] = "未知候选人"
    if not isinstance(result.get("next_step"), str):
        result["next_step"] = ""
    return result


def _validate_job_profile(job_profile: JobProfile) -> Dict[str, Any]:
    job_data = job_profile.model_dump() if hasattr(job_profile, "model_dump") else job_profile.dict()
    has_description = any(
        [
            str(job_data.get("title") or "").strip(),
            str(job_data.get("responsibilities") or "").strip(),
            job_data.get("must_haves"),
            job_data.get("keywords"),
        ]
    )
    if not has_description:
        raise HTTPException(status_code=400, detail="岗位描述为空，请至少填写岗位名称、职责、硬性要求或关键词")
    return job_data


def _load_resume_input(repo: ResumeRepo, req: ResumeOptimizeRequest) -> Dict[str, Any]:
    if req.resumeId is not None:
        record = repo.get_record(req.resumeId)
        if record is None:
            raise HTTPException(status_code=404, detail=f"未找到 resumeId={req.resumeId} 的简历记录")
        if not record.extracted_text or not record.sections_json:
            raise HTTPException(status_code=400, detail="请先调用 /api/ocr 完成简历解析")
        sections = repo.get_sections(req.resumeId)
        if sections is None:
            raise HTTPException(status_code=400, detail="简历模块数据缺失")
        return {"resume_text": record.extracted_text, "sections": sections}

    resume_text = req.rawResumeText.strip()
    if not resume_text:
        raise HTTPException(status_code=400, detail="原始简历为空，请传入 resumeId 或 rawResumeText")
    return {"resume_text": resume_text, "sections": req.sections or []}


def _load_resume_input_for_optimize(repo: ResumeRepo, req: ResumeOptimizeRequest) -> Dict[str, Any]:
    if req.resumeId is not None:
        record = repo.get_record(req.resumeId)
        if record is None:
            _raise_api_error(
                404,
                "resume_optimize_resume_not_found",
                "未找到对应简历记录",
                {"resumeId": req.resumeId},
                retryable=False,
            )
        if not record.extracted_text or not record.sections_json:
            _raise_api_error(
                400,
                "resume_optimize_resume_not_ready",
                "请先完成简历解析",
                {"resumeId": req.resumeId},
            )
        sections = repo.get_sections(req.resumeId)
        if sections is None:
            _raise_api_error(
                400,
                "resume_optimize_sections_missing",
                "简历结构化结果缺失",
                {"resumeId": req.resumeId},
            )
        return {"resume_text": record.extracted_text, "sections": sections}

    resume_text = req.rawResumeText.strip()
    if not resume_text:
        _raise_api_error(
            400,
            "resume_optimize_resume_missing",
            "缺少已解析 resumeId 或原始简历文本",
            {"resumeId": req.resumeId},
        )
    return {"resume_text": resume_text, "sections": req.sections or []}


def _serialize_requirement_items(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []

    items: List[Dict[str, str]] = []
    for raw in value:
        if isinstance(raw, dict):
            requirement = str(raw.get("requirement") or raw.get("name") or "").strip()
            evidence = str(raw.get("evidence") or "").strip()
        else:
            requirement = str(raw or "").strip()
            evidence = ""
        if requirement:
            items.append({"requirement": requirement, "evidence": evidence})
    return items


def _normalize_job_extract_response(result: Dict[str, Any], status: str, source_preview: str, fallback_reason: str = "") -> Dict[str, Any]:
    payload = normalize_requirements(result)
    payload["must_haves"] = _serialize_requirement_items(payload.get("must_haves"))
    payload["nice_to_haves"] = _serialize_requirement_items(payload.get("nice_to_haves"))
    payload["source_text_preview"] = source_preview
    payload["extraction_status"] = status
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    return payload


def _load_resume_context(
    repo: ResumeRepo,
    resume_id: Optional[int],
    raw_resume_text: str = "",
    sections: Any = None,
    structured_resume: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context: Dict[str, Any]
    if resume_id is not None:
        record = repo.get_record(resume_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"未找到 resumeId={resume_id} 的简历记录")
        context = {
            "resumeId": resume_id,
            "rawResumeText": record.extracted_text or "",
            "sections": repo.get_sections(resume_id) or [],
        }
    else:
        context = {"rawResumeText": "", "sections": []}

    inline_text = raw_resume_text.strip()
    if inline_text:
        context["rawResumeText"] = inline_text
    if sections:
        context["sections"] = sections
    if isinstance(structured_resume, dict) and structured_resume:
        context["structuredResume"] = structured_resume
    return context


def _ensure_job_requirements(job_description: str, job_requirements: Dict[str, Any]) -> Dict[str, Any]:
    if job_requirements:
        return normalize_requirements(job_requirements)
    if not job_description.strip():
        return normalize_requirements({})
    try:
        client = SiliconFlowClient(timeout_seconds=MATCH_LLM_TIMEOUT_SECONDS)
        result = normalize_requirements(extract_job_requirements(client, job_description.strip()))
        if _requirements_need_fallback(result, job_description):
            raise ValueError("job requirements extraction returned sparse result")
        return result
    except Exception:
        return normalize_requirements(fallback_extract_job_requirements(job_description.strip()))


def _enrich_resume_optimize_result(
    result: Dict[str, Any],
    job_requirements: Dict[str, Any],
    resume_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    optimized_resume = result.get("optimized_resume") if isinstance(result.get("optimized_resume"), dict) else {}
    comparisons = optimized_resume.get("sections") if isinstance(optimized_resume.get("sections"), list) else []
    matched_requirements = result.get("matched_requirements") if isinstance(result.get("matched_requirements"), list) else []
    if isinstance(result.get("unmet_requirements"), list):
        unmet_requirements = result["unmet_requirements"]
    else:
        unmet_requirements = [
            item
            for item in matched_requirements
            if str(item.get("status", "")).strip() in {"未匹配", "部分匹配", "未满足", "部分满足"}
        ]

    suggested_experiences = result.get("suggested_experiences")
    if not isinstance(suggested_experiences, list):
        suggested_experiences = [
            "补充真实课程项目或个人项目的背景、职责、技术方案和结果",
            "为已有项目增加可演示链接、截图或部署说明",
            "把未满足岗位要求转化为后续学习和实践计划，避免写成已经掌握",
        ]

    result["interface_name"] = "岗位定制简历优化"
    result["optimizedResume"] = optimized_resume
    result["beforeAfterComparison"] = comparisons
    result["modificationReasons"] = [
        {"section": item.get("name", ""), "reasons": item.get("reasons", [])}
        for item in comparisons
        if isinstance(item, dict)
    ]
    result["matchedJobRequirements"] = matched_requirements
    result["unmetRequirements"] = unmet_requirements
    result["nonFabricationReminder"] = result.get(
        "non_fabrication_statement",
        "本次优化仅基于原简历已有事实，未新增经历、学历、公司、项目、年限或技能。",
    )
    result["suggestedExperiencesToAdd"] = suggested_experiences
    result["jobRequirementsUsed"] = job_requirements
    if isinstance(result.get("coverage"), dict):
        result["coverage"] = result["coverage"]
    skipped_modules = result.get("skipped_modules") if isinstance(result.get("skipped_modules"), list) else []
    if not skipped_modules and isinstance(result.get("skippedModules"), list):
        skipped_modules = result["skippedModules"]
    result["skippedModules"] = skipped_modules
    result["skipped_modules"] = skipped_modules
    optimized_structure = None
    if isinstance(result.get("optimizedStructure"), dict):
        optimized_structure = result["optimizedStructure"]
    elif isinstance(result.get("optimized_structure"), dict):
        optimized_structure = result["optimized_structure"]
    if resume_input:
        result["sourceSections"] = resume_input.get("sections") if isinstance(resume_input.get("sections"), list) else []
        result["rawResumeText"] = str(resume_input.get("resume_text") or "")
        result["resumeContext"] = {
            "sections": result["sourceSections"],
            "rawResumeText": result["rawResumeText"],
        }
        result["recognitionMode"] = str(resume_input.get("recognitionMode") or "text-first")
        result["layoutConfidence"] = float(resume_input.get("layoutConfidence") or 0.0)
        result["layoutWarnings"] = (
            resume_input.get("layoutWarnings") if isinstance(resume_input.get("layoutWarnings"), list) else []
        )
        result["normalizedBlocks"] = (
            resume_input.get("normalizedBlocks") if isinstance(resume_input.get("normalizedBlocks"), list) else []
        )
    structured_source = dict(result)
    if isinstance(optimized_structure, dict):
        for key in [
            "basics",
            "targetRole",
            "education",
            "experiences",
            "projects",
            "skills",
            "certificates",
            "awards",
            "selfEvaluation",
            "customSections",
        ]:
            if key in optimized_structure:
                structured_source[key] = optimized_structure.get(key)
        merged_metadata = dict(structured_source.get("metadata") or {}) if isinstance(structured_source.get("metadata"), dict) else {}
        if isinstance(optimized_structure.get("metadata"), dict):
            merged_metadata.update(optimized_structure["metadata"])
        structured_source["metadata"] = merged_metadata
    result["structuredResume"] = structure_resume_data(structured_source)
    metadata = result["structuredResume"].get("metadata") if isinstance(result["structuredResume"], dict) else {}
    result["structuredResumeWarnings"] = metadata.get("warnings", []) if isinstance(metadata, dict) else []
    result["structuredResumeMissingFields"] = metadata.get("missingFields", []) if isinstance(metadata, dict) else []
    result["structuredResumeCompleteness"] = metadata.get("completeness", "partial") if isinstance(metadata, dict) else "partial"
    result["templateReady"] = bool(result.get("templateReady", result.get("template_ready", False)) or result["structuredResume"])
    result["template_ready"] = result["templateReady"]
    return result


def _requirements_need_fallback(result: Dict[str, Any], job_description: str) -> bool:
    if not job_description.strip():
        return False

    must_haves = result.get("must_haves")
    nice_to_haves = result.get("nice_to_haves")
    keywords = result.get("keywords")
    responsibilities = str(result.get("responsibilities") or "").strip()
    title = str(result.get("title") or "").strip()

    must_count = len(must_haves) if isinstance(must_haves, list) else 0
    nice_count = len(nice_to_haves) if isinstance(nice_to_haves, list) else 0
    keyword_count = len(keywords) if isinstance(keywords, list) else 0

    if must_count or nice_count:
        return False
    if responsibilities and len(responsibilities) >= 12:
        return False
    if title and len(title) >= 2 and keyword_count >= 2:
        return False
    return True


def _run_match(repo: ResumeRepo, resume_id: int, job_profile: JobProfile) -> MatchResponse:
    record = repo.get_record(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"未找到 resumeId={resume_id} 的简历记录")
    if not record.extracted_text or not record.sections_json:
        raise HTTPException(status_code=400, detail="请先调用 /api/ocr 完成简历解析")

    sections = repo.get_sections(resume_id)
    if sections is None:
        raise HTTPException(status_code=400, detail="简历模块数据缺失")

    job_data = _validate_job_profile(job_profile)
    result = _normalize_match_result(rule_match_resume_to_job(record.extracted_text, sections, job_data))
    result["ai_explanation_status"] = "not_attempted"
    try:
        client = SiliconFlowClient(timeout_seconds=6)
        result = llm_match_resume_to_job(client, record.extracted_text, sections, job_data)
        result = _normalize_match_result(result)
        result["ai_explanation_status"] = "success"
    except Exception as e:
        result["ai_explanation_status"] = "failed"
        result["ai_error"] = str(e)[:500]

    job_profile_id = repo.create_job_profile(job_data)
    match_result_id = repo.set_match_result(
        resume_id=resume_id,
        job_profile_id=job_profile_id,
        status=result["recommendation"],
        match_score=result["match_score"],
        result=result,
    )

    return MatchResponse(
        resumeId=resume_id,
        jobProfileId=job_profile_id,
        matchResultId=match_result_id,
        match_score=result["match_score"],
        recommendation=result["recommendation"],
        result=result,
    )


def _run_match_with_logging(repo: ResumeRepo, resume_id: int, job_profile: JobProfile) -> MatchResponse:
    started_at = time.monotonic()
    _log_stage("/api/match", "started", started_at, resume_id=resume_id)

    record = repo.get_record(resume_id)
    if record is None:
        _raise_api_error(404, "match_resume_not_found", "未找到对应简历记录", {"resumeId": resume_id})
    if not record.extracted_text or not record.sections_json:
        _raise_api_error(400, "match_resume_not_ready", "请先完成简历解析", {"resumeId": resume_id})

    _log_stage("/api/match", "resume_loaded", started_at, extracted_text_len=len(record.extracted_text or ""))
    sections = repo.get_sections(resume_id)
    if sections is None:
        _raise_api_error(400, "match_sections_missing", "简历结构化结果缺失", {"resumeId": resume_id})

    job_data = _validate_job_profile(job_profile)
    _log_stage(
        "/api/match",
        "job_profile_validated",
        started_at,
        title=str(job_data.get("title") or "")[:60],
        must_haves=len(job_data.get("must_haves") or []),
        keywords=len(job_data.get("keywords") or []),
    )

    result = _normalize_match_result(rule_match_resume_to_job(record.extracted_text, sections, job_data))
    result["ai_explanation_status"] = "not_attempted"
    result["fallback_status"] = "rule_first"
    _log_stage("/api/match", "rule_finished", started_at, match_score=result.get("match_score"))

    try:
        client = SiliconFlowClient(timeout_seconds=6)
        _log_stage("/api/match", "llm_started", started_at)
        result = llm_match_resume_to_job(client, record.extracted_text, sections, job_data)
        result = _normalize_match_result(result)
        result["ai_explanation_status"] = "success"
        result["fallback_status"] = "none"
        _log_stage("/api/match", "llm_finished", started_at, match_score=result.get("match_score"))
    except Exception as e:
        logger.exception("/api/match llm_failed resume_id=%s", resume_id)
        result["ai_explanation_status"] = "failed"
        result["ai_error"] = str(e)[:500]
        result["fallback_status"] = "rule_success"
        _log_stage("/api/match", "llm_failed_rule_returned", started_at, error=str(e)[:200])

    try:
        _log_stage("/api/match", "db_write_started", started_at)
        job_profile_id = repo.create_job_profile(job_data)
        match_result_id = repo.set_match_result(
            resume_id=resume_id,
            job_profile_id=job_profile_id,
            status=result["recommendation"],
            match_score=result["match_score"],
            result=result,
        )
        _log_stage("/api/match", "db_write_finished", started_at, job_profile_id=job_profile_id, match_result_id=match_result_id)
    except Exception as e:
        logger.exception("/api/match db_write_failed resume_id=%s", resume_id)
        _raise_api_error(
            500,
            "match_db_write_failed",
            "匹配结果已生成，但写入数据库失败",
            {"resumeId": resume_id, "error": str(e)},
        )

    _log_stage("/api/match", "finished", started_at, match_score=result["match_score"])
    return MatchResponse(
        resumeId=resume_id,
        jobProfileId=job_profile_id,
        matchResultId=match_result_id,
        match_score=result["match_score"],
        recommendation=result["recommendation"],
        result=result,
    )


def _run_ocr_pipeline(filename: str, pdf_bytes: bytes) -> OcrResponse:
    started_at = time.monotonic()
    _log_stage("/api/ocr", "started", started_at, filename=filename, bytes=len(pdf_bytes))

    repo = ResumeRepo()
    try:
        _log_stage("/api/ocr", "db_record_create_started", started_at)
        resume_id = repo.create_record(filename=filename)
        _log_stage("/api/ocr", "db_record_create_finished", started_at, resume_id=resume_id)
    except Exception as e:
        logger.exception("/api/ocr db_record_create_failed filename=%s", filename)
        _raise_api_error(500, "ocr_record_create_failed", "创建简历记录失败", {"filename": filename, "error": str(e)})

    try:
        _log_stage("/api/ocr", "pdf_extract_started", started_at, resume_id=resume_id)
        extracted_text = extract_text_from_pdf_bytes(pdf_bytes)
        _log_stage("/api/ocr", "pdf_extract_finished", started_at, resume_id=resume_id, extracted_text_len=len(extracted_text or ""))
    except Exception as e:
        logger.exception("/api/ocr extract_failed resume_id=%s", resume_id)
        try:
            repo.delete_record(resume_id)
            _log_stage("/api/ocr", "db_record_deleted", started_at, resume_id=resume_id)
        except Exception:
            logger.exception("/api/ocr db_record_delete_failed resume_id=%s", resume_id)
        _raise_api_error(422, "ocr_extract_failed", "无法读取 PDF 文本", {"resumeId": resume_id, "error": str(e)})

    if not extracted_text or len(extracted_text.strip()) < 30:
        extracted_text = ""

    try:
        _log_stage("/api/ocr", "llm_started", started_at, resume_id=resume_id)
        client = SiliconFlowClient(timeout_seconds=OCR_LLM_TIMEOUT_SECONDS)
        raw_sections = llm_extract_sections(
            client,
            extracted_text or "PDF 中未抽取到足够文本，请检查是否为扫描件。",
        )
        llm_status = "success"
        _log_stage("/api/ocr", "llm_finished", started_at, resume_id=resume_id, section_count=len(raw_sections) if isinstance(raw_sections, list) else None)
    except Exception as e:
        logger.exception("/api/ocr llm_failed resume_id=%s", resume_id)
        raw_sections = fallback_extract_sections(extracted_text)
        llm_status = "fallback"
        _log_stage("/api/ocr", "llm_failed", started_at, resume_id=resume_id, error=str(e)[:200], fallback_section_count=len(raw_sections))

    layout_analysis = None
    elapsed_seconds = time.monotonic() - started_at
    should_attempt_layout = (
        llm_status == "success"
        and bool(extracted_text.strip())
        and elapsed_seconds < max(5, OCR_ROUTE_TIMEOUT_SECONDS - 8)
    )
    if should_attempt_layout:
        layout_analysis = analyze_resume_layout(pdf_bytes, extracted_text or "")
    normalized_ocr = normalize_optimize_sections(extracted_text or "", raw_sections, layout_analysis=layout_analysis)
    sections = normalized_ocr["sections"]

    try:
        _log_stage("/api/ocr", "db_write_started", started_at, resume_id=resume_id, llm_status=llm_status)
        repo.set_ocr_result(resume_id, extracted_text, sections)
        _log_stage("/api/ocr", "db_write_finished", started_at, resume_id=resume_id)
    except Exception as e:
        logger.exception("/api/ocr db_write_failed resume_id=%s", resume_id)
        _raise_api_error(500, "ocr_db_write_failed", "简历解析完成，但写入数据库失败", {"resumeId": resume_id, "error": str(e)})

    _log_stage("/api/ocr", "finished", started_at, resume_id=resume_id, llm_status=llm_status)
    return OcrResponse(
        resumeId=resume_id,
        extractedTextPreview=_preview(extracted_text),
        sections=sections,
        recognitionMode=str(normalized_ocr.get("recognitionMode") or "text-first"),
        layoutConfidence=float(normalized_ocr.get("layoutConfidence") or 0.0),
        layoutWarnings=normalized_ocr.get("layoutWarnings") if isinstance(normalized_ocr.get("layoutWarnings"), list) else [],
        normalizedBlocks=normalized_ocr.get("normalizedBlocks") if isinstance(normalized_ocr.get("normalizedBlocks"), list) else [],
    )


def _run_career_plan_pipeline(profile: Dict[str, Any]) -> Dict[str, Any]:
    started_at = time.monotonic()
    _log_stage("/api/career/plan", "started", started_at)
    try:
        client = SiliconFlowClient(timeout_seconds=CAREER_PLAN_LLM_TIMEOUT_SECONDS)
        _log_stage("/api/career/plan", "llm_started", started_at, model=client.model)
        result = generate_career_plan(client, profile)
        result["fallback_status"] = "none"
        _log_stage("/api/career/plan", "llm_finished", started_at, model=client.model)
    except Exception as e:
        logger.exception("/api/career/plan llm_failed")
        result = fallback_career_plan(profile)
        result["fallback_status"] = "career_plan_simplified"
        result["ai_error"] = str(e)[:500]
        _log_stage("/api/career/plan", "llm_failed", started_at, error=str(e)[:200])

    result["studentProfile"] = profile
    result["valuePrinciples"] = ["真实优先", "岗位理解优先", "结果可解释", "行动计划可执行"]
    _log_stage("/api/career/plan", "finished", started_at, fallback_status=result.get("fallback_status"))
    return result


def _run_resume_optimize_pipeline(req: ResumeOptimizeRequest) -> Dict[str, Any]:
    started_at = time.monotonic()
    _log_stage("/api/resume/optimize", "started", started_at, resume_id=req.resumeId)
    repo = ResumeRepo()
    resume_input = _load_resume_input_for_optimize(repo, req)
    normalized_resume = normalize_optimize_sections(
        str(resume_input.get("resume_text") or ""),
        resume_input.get("sections"),
    )
    resume_input["sections"] = normalized_resume["sections"]
    resume_input["recognitionMode"] = normalized_resume.get("recognitionMode")
    resume_input["layoutConfidence"] = normalized_resume.get("layoutConfidence")
    resume_input["layoutWarnings"] = normalized_resume.get("layoutWarnings")
    resume_input["normalizedBlocks"] = normalized_resume.get("normalizedBlocks")
    _log_stage(
        "/api/resume/optimize",
        "resume_loaded",
        started_at,
        resume_text_len=len(resume_input.get("resume_text") or ""),
        sections_count=len(resume_input.get("sections") or []) if isinstance(resume_input.get("sections"), list) else None,
    )

    job_requirements = req.jobRequirements
    job_description = req.jobDescription.strip()
    if not job_requirements:
        if not job_description:
            _raise_api_error(400, "resume_optimize_missing_job", "缺少岗位 JD 或岗位要求", {"resumeId": req.resumeId})
        try:
            client = SiliconFlowClient(timeout_seconds=RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS, allow_model_fallback=False)
            _log_stage("/api/resume/optimize", "job_requirements_llm_started", started_at, model=client.model)
            job_requirements = normalize_requirements(extract_job_requirements(client, job_description))
            if _requirements_need_fallback(job_requirements, job_description):
                raise ValueError("job requirements extraction returned sparse result")
            _log_stage("/api/resume/optimize", "job_requirements_llm_finished", started_at, model=client.model)
        except Exception as e:
            logger.exception("/api/resume/optimize job_requirements_llm_failed")
            job_requirements = normalize_requirements(fallback_extract_job_requirements(job_description))
            _log_stage("/api/resume/optimize", "job_requirements_fallback", started_at, error=str(e)[:200])
    else:
        job_requirements = normalize_requirements(job_requirements)

    prompt_started_at = time.monotonic()
    prompt_stats = estimate_optimize_prompt_input(
        resume_input["resume_text"],
        resume_input["sections"],
        job_requirements,
    )
    _log_stage(
        "/api/resume/optimize",
        "prompt_constructed",
        started_at,
        prompt_ms=int((time.monotonic() - prompt_started_at) * 1000),
        **prompt_stats,
    )

    try:
        model_name = req.model.strip() or RESUME_OPTIMIZE_FAST_MODEL
        client = SiliconFlowClient(
            model=model_name,
            timeout_seconds=RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS,
            allow_model_fallback=False,
        )
        _log_stage("/api/resume/optimize", "llm_started", started_at, model=client.model)
        llm_result = optimize_resume_for_job(
            client,
            resume_input["resume_text"],
            resume_input["sections"],
            job_requirements,
            timeout_seconds=RESUME_OPTIMIZE_LLM_TIMEOUT_SECONDS,
            max_retries=RESUME_OPTIMIZE_LLM_RETRIES,
        )
    except Exception as e:
        logger.exception("/api/resume/optimize llm_failed")
        _log_stage("/api/resume/optimize", "llm_failed", started_at, error=str(e)[:200])
        fallback = fallback_optimize_resume_for_job(
            resume_input["resume_text"],
            resume_input["sections"],
            job_requirements,
            error=str(e),
        )
        fallback["ai_error"] = str(e)[:500]
        fallback["errorStage"] = "模型调用失败"
        fallback["safety_policy"] = "仅基于原简历已有事实优化表达，禁止虚构经历、学历、公司、项目、年限或技能。"
        enriched = _enrich_resume_optimize_result(fallback, job_requirements, resume_input=resume_input)
        _log_stage(
            "/api/resume/optimize",
            "fallback_finished",
            started_at,
            fallback_status=fallback.get("fallback_status"),
        )
        return enriched

    try:
        llm_result["safety_policy"] = "仅基于原简历已有事实优化表达，禁止虚构经历、学历、公司、项目、年限或技能。"
        llm_result["fallback_status"] = "none"
        enriched = _enrich_resume_optimize_result(llm_result, job_requirements, resume_input=resume_input)
        _log_stage("/api/resume/optimize", "llm_finished", started_at, model=client.model)
        _log_stage("/api/resume/optimize", "finished", started_at, fallback_status="none")
        return enriched
    except Exception as e:
        logger.exception("/api/resume/optimize postprocess_failed")
        _raise_api_error(
            500,
            "resume_optimize_postprocess_failed",
            "岗位定制简历已生成，但后处理失败",
            {"resumeId": req.resumeId, "error": str(e), "hasJobRequirements": bool(job_requirements)},
        )


def _resume_optimize_timeout_fallback(req: ResumeOptimizeRequest) -> Dict[str, Any]:
    repo = ResumeRepo()
    resume_input = _load_resume_input_for_optimize(repo, req)
    normalized_resume = normalize_optimize_sections(
        str(resume_input.get("resume_text") or ""),
        resume_input.get("sections"),
    )
    resume_input["sections"] = normalized_resume["sections"]
    resume_input["recognitionMode"] = normalized_resume.get("recognitionMode")
    resume_input["layoutConfidence"] = normalized_resume.get("layoutConfidence")
    resume_input["layoutWarnings"] = normalized_resume.get("layoutWarnings")
    resume_input["normalizedBlocks"] = normalized_resume.get("normalizedBlocks")
    if req.jobRequirements:
        job_requirements = normalize_requirements(req.jobRequirements)
    else:
        job_requirements = normalize_requirements(fallback_extract_job_requirements(req.jobDescription.strip()))

    fallback = fallback_optimize_resume_for_job(
        resume_input["resume_text"],
        resume_input["sections"],
        job_requirements,
        error=(
            f"岗位定制简历优化在 {RESUME_OPTIMIZE_ROUTE_TIMEOUT_SECONDS} 秒内未完成，"
            "已返回可继续排版的保守兜底建议。"
        ),
    )
    fallback["ai_error"] = (
        f"resume optimize route timeout after {RESUME_OPTIMIZE_ROUTE_TIMEOUT_SECONDS}s"
    )
    fallback["errorStage"] = "路由超时"
    fallback["fallback_status"] = "resume_optimize_timeout_fallback"
    fallback["safety_policy"] = "仅基于原简历已有事实优化表达，禁止虚构经历、学历、公司、项目、年限或技能。"
    return _enrich_resume_optimize_result(fallback, job_requirements, resume_input=resume_input)


@router.post("/ocr", response_model=OcrResponse)
async def ocr_resume(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> OcrResponse:
    context = _request_context(x_user_id, x_user_role)
    started_at = time.monotonic()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        _log_ai_call(
            ResumeRepo(),
            feature="resume_ocr",
            endpoint="/api/ocr",
            status="failed",
            started_at=started_at,
            context=context,
            error_message="invalid_file_type",
            metadata={"filename": file.filename},
        )
        _raise_api_error(415, "ocr_invalid_file_type", "当前仅支持 PDF 简历", {"filename": file.filename})

    pdf_bytes = await file.read()
    if not pdf_bytes:
        _log_ai_call(
            ResumeRepo(),
            feature="resume_ocr",
            endpoint="/api/ocr",
            status="failed",
            started_at=started_at,
            context=context,
            error_message="empty_file",
            metadata={"filename": file.filename},
        )
        _raise_api_error(400, "ocr_empty_file", "上传文件为空", {"filename": file.filename})
    if len(pdf_bytes) > 20 * 1024 * 1024:
        _log_ai_call(
            ResumeRepo(),
            feature="resume_ocr",
            endpoint="/api/ocr",
            status="failed",
            started_at=started_at,
            context=context,
            error_message="file_too_large",
            metadata={"filename": file.filename, "size": len(pdf_bytes)},
        )
        _raise_api_error(400, "ocr_file_too_large", "文件过大，建议不超过 20MB", {"filename": file.filename, "size": len(pdf_bytes)})

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_ocr_pipeline, file.filename, pdf_bytes),
            timeout=OCR_ROUTE_TIMEOUT_SECONDS,
        )
        record = ResumeRepo().get_record(result.resumeId)
        if record and (record.user_id != context.user_id or record.user_role != context.user_role):
            with ResumeRepo()._connect() as conn:
                ResumeRepo()._execute_write(
                    conn,
                    """
                    UPDATE resume_records
                    SET user_id = ?, user_role = ?
                    WHERE id = ?
                    """,
                    (context.user_id, context.user_role, result.resumeId),
                )
                conn.commit()
        _log_ai_call(
            ResumeRepo(),
            feature="resume_ocr",
            endpoint="/api/ocr",
            status="success",
            started_at=started_at,
            context=context,
            metadata={"resumeId": result.resumeId, "filename": file.filename},
        )
        return result
    except asyncio.TimeoutError:
        _log_ai_call(
            ResumeRepo(),
            feature="resume_ocr",
            endpoint="/api/ocr",
            status="failed",
            started_at=started_at,
            context=context,
            error_message="timeout",
            metadata={"filename": file.filename},
        )
        _raise_api_error(
            504,
            "ocr_timeout",
            "简历解析超时，请查看日志定位当前阶段",
            {"filename": file.filename, "timeoutSeconds": OCR_ROUTE_TIMEOUT_SECONDS},
        )


@router.post("/suggestions", response_model=SuggestionsResponse)
async def generate_suggestions(req: ResumeIdRequest) -> SuggestionsResponse:
    repo = ResumeRepo()
    record = repo.get_record(req.resumeId)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到该 resumeId 的记录")
    if not record.extracted_text or not record.sections_json:
        raise HTTPException(status_code=400, detail="请先调用 /api/ocr 完成简历解析")

    sections = repo.get_sections(req.resumeId)
    if sections is None:
        raise HTTPException(status_code=400, detail="简历模块数据缺失")

    try:
        client = SiliconFlowClient()
        suggestions = llm_generate_suggestions(client, record.extracted_text, sections)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"简历优化建议生成失败: {e}")

    repo.set_suggestions(req.resumeId, suggestions)

    return SuggestionsResponse(
        resumeId=req.resumeId,
        overall_summary=suggestions.get("overall_summary", ""),
        items=suggestions.get("items", []),
    )


@router.post("/match", response_model=MatchResponse)
async def match_resume(req: MatchRequest) -> MatchResponse:
    repo = ResumeRepo()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_run_match_with_logging, repo, req.resumeId, req.jobProfile),
            timeout=MATCH_ROUTE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        _raise_api_error(
            504,
            "match_timeout",
            "简历诊断超时，请查看日志定位当前阶段",
            {"resumeId": req.resumeId, "timeoutSeconds": MATCH_ROUTE_TIMEOUT_SECONDS},
        )


@router.post("/job/extract-requirements")
async def extract_requirements(req: JobExtractRequirementsRequest) -> Dict[str, Any]:
    job_description = req.jobDescription.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="岗位描述为空，无法提取招聘要求")
    try:
        client = SiliconFlowClient(timeout_seconds=MATCH_LLM_TIMEOUT_SECONDS)
        result = normalize_requirements(extract_job_requirements(client, job_description))
        if _requirements_need_fallback(result, job_description):
            raise ValueError("job requirements extraction returned sparse result")
        return _normalize_job_extract_response(result, "ai", _preview(job_description, max_len=500))
    except Exception as e:
        result = normalize_requirements(fallback_extract_job_requirements(job_description))
        return _normalize_job_extract_response(
            result,
            "fallback",
            _preview(job_description, max_len=500),
            fallback_reason=str(e)[:300],
        )


@router.post("/resume/optimize")
async def optimize_resume(req: ResumeOptimizeRequest) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_run_resume_optimize_pipeline, req),
            timeout=RESUME_OPTIMIZE_ROUTE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "/api/resume/optimize route_timeout resume_id=%s timeout_seconds=%s",
            req.resumeId,
            RESUME_OPTIMIZE_ROUTE_TIMEOUT_SECONDS,
        )
        return _resume_optimize_timeout_fallback(req)


@router.post("/resume/structure")
async def structure_resume(req: ResumeStructureRequest) -> Dict[str, Any]:
    if not req.resumeData:
        raise HTTPException(status_code=400, detail="resumeData 不能为空")
    try:
        structured = structure_resume_data(req.resumeData)
        metadata = structured.get("metadata") if isinstance(structured, dict) else {}
        return {
            "structuredResume": structured,
            "warnings": metadata.get("warnings", []) if isinstance(metadata, dict) else [],
            "missingFields": metadata.get("missingFields", []) if isinstance(metadata, dict) else [],
            "completeness": metadata.get("completeness", "partial") if isinstance(metadata, dict) else "partial",
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"结构化简历数据转换失败: {e}") from e


@router.get("/resume/templates")
async def resume_templates() -> List[Dict[str, Any]]:
    return list_resume_templates()


@router.post("/resume/export-pdf")
async def export_resume_pdf(req: ResumeExportPdfRequest) -> FileResponse:
    try:
        get_template(req.templateId)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    source_data = req.structuredResume or req.resumeData
    if not source_data:
        raise HTTPException(status_code=400, detail="structuredResume 或 resumeData 不能为空")

    try:
        structured = structure_resume_data(source_data)
        export = render_resume_pdf(req.templateId, structured)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 导出失败: {e}") from e

    filename = req.filename.strip() or export["filename"]
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    return FileResponse(
        export["path"],
        media_type="application/pdf",
        filename=filename,
        headers={"X-Resume-PDF-Engine": export["engine"]},
        background=BackgroundTask(_remove_export_file, export["path"]),
    )


def _remove_export_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        logger.warning("resume_pdf_cleanup_failed path=%s", path)


@router.post("/career/plan")
async def career_plan(
    req: CareerPlanRequest,
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    context = _request_context(x_user_id, x_user_role)
    started_at = time.monotonic()
    profile = normalize_student_profile(req.model_dump() if hasattr(req, "model_dump") else req.dict())
    try:
        if not any([profile["major"], profile["grade"], profile["skills"], profile["experience"], profile["interests"]]):
            _log_ai_call(
                ResumeRepo(),
                feature="career_plan",
                endpoint="/api/career/plan",
                status="failed",
                started_at=started_at,
                context=context,
                error_message="profile_missing",
            )
            _raise_api_error(400, "career_plan_profile_missing", "学生背景为空，请至少填写专业、年级、技能、经历或兴趣方向", {})
        if profile["grade"] and profile["grade"] not in ALLOWED_CAREER_GRADES:
            _log_ai_call(
                ResumeRepo(),
                feature="career_plan",
                endpoint="/api/career/plan",
                status="failed",
                started_at=started_at,
                context=context,
                error_message="grade_not_allowed",
                metadata={"grade": profile["grade"]},
            )
            _raise_api_error(
                403,
                "career_plan_grade_restricted",
                "职业规划当前只对大一、大二开放",
                {"grade": profile["grade"], "allowedGrades": sorted(ALLOWED_CAREER_GRADES)},
                retryable=False,
            )
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_career_plan_pipeline, profile),
            timeout=CAREER_PLAN_ROUTE_TIMEOUT_SECONDS,
        )
        _log_ai_call(
            ResumeRepo(),
            feature="career_plan",
            endpoint="/api/career/plan",
            status="success",
            started_at=started_at,
            context=context,
            metadata={"grade": profile["grade"]},
        )
        return result
    except asyncio.TimeoutError:
        fallback = fallback_career_plan(profile)
        fallback["studentProfile"] = profile
        fallback["valuePrinciples"] = ["真实优先", "岗位理解优先", "结果可解释", "行动计划可执行"]
        fallback["fallback_status"] = "career_plan_timeout"
        fallback["message"] = "职业规划生成超时，已返回简化建议"
        _log_ai_call(
            ResumeRepo(),
            feature="career_plan",
            endpoint="/api/career/plan",
            status="fallback",
            started_at=started_at,
            context=context,
            error_message="timeout",
            metadata={"grade": profile["grade"]},
        )
        return fallback


@router.post("/application/strategy")
def application_strategy(
    req: ApplicationStrategyRequest,
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    context = _request_context(x_user_id, x_user_role)
    started_at = time.monotonic()
    repo = ResumeRepo()
    student_profile = normalize_student_profile(req.studentProfile)
    job_requirements = _ensure_job_requirements(req.jobDescription, req.jobRequirements)
    resume_context = _load_resume_context(repo, req.resumeId, req.rawResumeText, req.sections, req.structuredResume)
    match_result = dict(req.matchResult or {})
    if not match_result:
        match_result = {
            "note": "未传入适配度诊断结果，以下投递策略主要基于学生背景、简历上下文和岗位要求生成。",
            "resumeContextAvailable": bool(resume_context.get("rawResumeText") or resume_context.get("sections")),
        }
    try:
        client = SiliconFlowClient()
        result = generate_application_strategy(client, student_profile, resume_context, job_requirements, match_result)
        result["jobRequirementsUsed"] = job_requirements
        result["resumeContext"] = resume_context
        result["nonFabricationReminder"] = "投递话术和简历版本建议只能基于真实经历，不建议虚构技能、项目或实习。"
        _log_ai_call(
            repo,
            feature="application_strategy",
            endpoint="/api/application/strategy",
            status="success",
            started_at=started_at,
            context=context,
            metadata={"resumeId": req.resumeId},
        )
        return result
    except Exception as e:
        _log_ai_call(
            repo,
            feature="application_strategy",
            endpoint="/api/application/strategy",
            status="failed",
            started_at=started_at,
            context=context,
            error_message=str(e),
            metadata={"resumeId": req.resumeId},
        )
        raise HTTPException(status_code=502, detail=f"AI 接口失败：投递策略生成失败，{e}") from e


@router.post("/interview/prepare")
def interview_prepare(
    req: InterviewPrepareRequest,
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    context = _request_context(x_user_id, x_user_role)
    started_at = time.monotonic()
    repo = ResumeRepo()
    student_profile = normalize_student_profile(req.studentProfile)
    job_requirements = _ensure_job_requirements(req.jobDescription, req.jobRequirements)
    resume_context = _load_resume_context(
        repo,
        req.resumeId,
        req.rawResumeText,
        req.sections,
        req.structuredResume,
    )
    try:
        client = SiliconFlowClient()
        result = generate_interview_prepare(
            client,
            student_profile,
            resume_context,
            job_requirements,
            dict(req.matchResult or {}),
        )
        result["jobRequirementsUsed"] = job_requirements
        result["resumeContext"] = resume_context
        result["nonFabricationReminder"] = "面试准备用于梳理真实经历和表达框架，不建议背诵虚构答案。"
        _log_ai_call(
            repo,
            feature="interview_prepare",
            endpoint="/api/interview/prepare",
            status="success",
            started_at=started_at,
            context=context,
            metadata={"resumeId": req.resumeId},
        )
        return result
    except Exception as e:
        _log_ai_call(
            repo,
            feature="interview_prepare",
            endpoint="/api/interview/prepare",
            status="failed",
            started_at=started_at,
            context=context,
            error_message=str(e),
            metadata={"resumeId": req.resumeId},
        )
        raise HTTPException(status_code=502, detail=f"AI 接口失败：面试准备生成失败，{e}") from e


@router.post("/batch-match", response_model=List[MatchResponse])
async def batch_match(req: BatchMatchRequest) -> List[MatchResponse]:
    if not req.resumeIds:
        raise HTTPException(status_code=400, detail="resumeIds 不能为空")
    _validate_job_profile(req.jobProfile)
    repo = ResumeRepo()
    started_at = time.monotonic()
    results = []
    for resume_id in req.resumeIds:
        if time.monotonic() - started_at > req.timeoutSeconds:
            raise HTTPException(
                status_code=504,
                detail=f"批量处理超时：已完成 {len(results)} 份，建议减少批量数量或调大 timeoutSeconds",
            )
        results.append(_run_match(repo, resume_id, req.jobProfile))
    return sorted(results, key=lambda item: item.match_score, reverse=True)


@router.get("/analytics/recruitment")
def recruitment_analytics(
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    context = _request_context(x_user_id, x_user_role)
    _ensure_admin_access(context)
    repo = ResumeRepo()
    try:
        screening_source_query = "recruiter resume screening time study average seconds"
        recruiting_source_query = "recruitment funnel benchmark report application interview offer conversion"
        source_distribution_query = "candidate source recruiting channel benchmark report"
        total_resumes = repo.count_resumes()
        total_users = repo.count_users()
        matches = repo.list_match_results()
        ai_summary = repo.summarize_ai_calls()
        ai_logs = repo.list_ai_call_logs(limit=100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"招聘数据读取失败: {e}") from e

    recommended = [item for item in matches if item["match_score"] >= 75 or item["status"] in {"强烈推荐", "推荐面试"}]
    average_score = round(sum(item["match_score"] for item in matches) / len(matches), 1) if matches else 0

    by_job: Dict[str, Dict[str, Any]] = {}
    for item in matches:
        bucket = by_job.setdefault(
            item["job_title"],
            {"jobTitle": item["job_title"], "screened": 0, "recommended": 0},
        )
        bucket["screened"] += 1
        if item in recommended:
            bucket["recommended"] += 1
    position_efficiency = []
    for bucket in by_job.values():
        screened = bucket["screened"]
        bucket["efficiencyRate"] = round(bucket["recommended"] / screened * 100, 1) if screened else 0
        position_efficiency.append(bucket)

    estimated_time_saved = round(len(matches) * 0.25 + len(recommended) * 0.5, 1)

    try:
        return {
            "dataMode": "sourced_public_research",
            "sourcePolicy": "核心指标来自本系统数据库；公开来源仅用于补充指标口径与估算依据。",
            "dashboardAudience": ["teacher", "operator", "admin"],
            "totalUsers": total_users,
            "totalResumes": attach_sources(
                total_resumes,
                recruiting_source_query,
                "公开招聘漏斗资料用于解释简历初筛口径，数值来自本系统数据库。",
            ),
            "recommendedCount": attach_sources(
                len(recommended),
                recruiting_source_query,
                "公开招聘漏斗资料用于解释推荐进入面试人数口径，数值来自本系统数据库。",
            ),
            "averageScore": attach_sources(
                average_score,
                recruiting_source_query,
                "公开招聘筛选资料用于解释平均匹配分口径，数值来自本系统匹配结果。",
            ),
            "positionEfficiency": [
                {
                    **item,
                    "sources": [
                        attach_sources(
                            item["efficiencyRate"],
                            recruiting_source_query,
                            "公开招聘漏斗资料用于解释岗位筛选效率口径。",
                        )["sources"][0]
                    ],
                }
                for item in sorted(position_efficiency, key=lambda value: value["screened"], reverse=True)
            ],
            "recruitmentFunnel": [
                {
                    "stage": "简历上传",
                    "count": total_resumes,
                    "conversionRate": 100,
                    "sources": attach_sources(100, recruiting_source_query, "公开招聘漏斗资料用于解释简历上传阶段。")["sources"],
                },
                {
                    "stage": "AI 初筛",
                    "count": len(matches),
                    "conversionRate": round(len(matches) / max(1, total_resumes) * 100, 1),
                    "sources": attach_sources(len(matches), recruiting_source_query, "公开招聘漏斗资料用于解释初筛阶段。")["sources"],
                },
                {
                    "stage": "推荐面试",
                    "count": len(recommended),
                    "conversionRate": round(len(recommended) / max(1, total_resumes) * 100, 1),
                    "sources": attach_sources(len(recommended), recruiting_source_query, "公开招聘漏斗资料用于解释面试推荐阶段。")["sources"],
                },
            ],
            "candidateSources": [],
            "estimatedTimeSavedHours": attach_sources(
                estimated_time_saved,
                screening_source_query,
                "公开资料用于估算人工筛选简历耗时，节省时间基于系统处理量换算。",
            ),
            "aiCalls": ai_summary["total"],
            "aiSuccessRate": ai_summary["successRate"],
            "aiFailedCount": ai_summary["failedTotal"],
            "aiFeatureBreakdown": ai_summary["featureBreakdown"],
            "roleBreakdown": ai_summary["roleBreakdown"],
            "aiCallLogs": ai_logs,
            "notes": "当前简历数、推荐数和平均分来自系统数据库；候选人来源分布因缺少真实来源字段暂不返回演示拆分值。",
            "candidateSourcesStatus": "unavailable_without_source_tracking",
            "estimatedFields": ["estimatedTimeSavedHours"],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"公开来源补充失败，无法返回无来源数据: {e}") from e


@router.get("/resume/{resume_id}")
async def get_resume(resume_id: int) -> Dict[str, Any]:
    repo = ResumeRepo()
    record = repo.get_record(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到该 resumeId 的记录")

    return {
        "resumeId": record.id,
        "filename": record.filename,
        "extractedTextPreview": _preview(record.extracted_text or ""),
        "sections": repo.get_sections(resume_id) or [],
        "suggestions": repo.get_suggestions(resume_id),
        "createdAt": record.created_at,
        "updatedAt": record.updated_at,
    }
