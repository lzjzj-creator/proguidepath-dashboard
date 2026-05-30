from typing import Any, Dict, List

from app.services.siliconflow_client import SiliconFlowClient, extract_json_object


def _json_or_error(content: str, message: str) -> Dict[str, Any]:
    parsed = extract_json_object(content)
    if not isinstance(parsed, dict):
        raise ValueError(message)
    return parsed


def generate_career_plan(client: SiliconFlowClient, profile: Dict[str, Any]) -> Dict[str, Any]:
    system = (
        "You are a practical career-planning assistant for university students. "
        "Give realistic, stage-appropriate advice. Output JSON only."
    )
    user = f"""
Generate a career plan in JSON.

Required JSON shape:
{{
  "recommendedDirections": [
    {{
      "direction": "frontend internship",
      "score": 86,
      "reason": "why it fits",
      "gaps": ["gap"],
      "actionPlan": ["action"]
    }}
  ],
  "learningRoadmap": [
    {{"stage": "2 weeks", "tasks": ["task"], "outcome": "outcome"}}
  ],
  "portfolioSuggestions": ["suggestion"],
  "cityAdvice": "city advice",
  "riskWarnings": ["risk"]
}}

Rules:
- Recommend 3-5 directions when possible.
- Keep advice realistic for students.
- Never suggest fabricating internships, companies, or projects.

student profile:
```json
{profile}
```
"""
    content = client.chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=1600,
    )
    return _json_or_error(content, "career plan result is not a JSON object")


def fallback_career_plan(profile: Dict[str, Any]) -> Dict[str, Any]:
    skills = [str(item).strip() for item in profile.get("skills") or [] if str(item).strip()]
    interests = [str(item).strip() for item in profile.get("interests") or [] if str(item).strip()]
    major = str(profile.get("major") or "").strip()
    grade = str(profile.get("grade") or "").strip()
    target_city = str(profile.get("targetCity") or "").strip()
    experience = str(profile.get("experience") or "").strip()

    direction_labels: List[str] = []
    lowered = {item.lower() for item in skills + interests}
    if {"python", "java", "fastapi", "backend"} & lowered:
        direction_labels.append("后端开发 / 平台研发")
    if {"vue", "react", "typescript", "frontend"} & lowered:
        direction_labels.append("前端开发")
    if {"ai", "llm", "nlp", "machine learning", "deep learning"} & lowered:
        direction_labels.append("AI 应用 / 数据方向")
    if not direction_labels:
        direction_labels = ["通用技术实习", "项目型岗位探索"]

    recommended_directions = []
    for index, direction in enumerate(direction_labels[:3], start=1):
        recommended_directions.append(
            {
                "direction": direction,
                "score": max(60, 86 - index * 6),
                "reason": f"基于当前专业、技能和兴趣，{direction} 与现有背景的可迁移性较高。",
                "gaps": [
                    "补充可展示项目成果",
                    "准备与目标岗位相关的技术表达",
                    "用真实经历支撑简历关键词",
                ],
                "actionPlan": [
                    "整理 1 个最能代表能力的真实项目并补足结果描述",
                    "围绕目标岗位准备 3-5 个高频问题回答框架",
                    "按周投递并记录反馈，持续修正方向",
                ],
            }
        )

    return {
        "recommendedDirections": recommended_directions,
        "learningRoadmap": [
            {"stage": "1-2 周", "tasks": ["梳理现有项目证据", "补齐简历中的结果描述"], "outcome": "形成可投递基础版简历"},
            {"stage": "2-4 周", "tasks": ["补强岗位高频技能", "完成一次模拟面试"], "outcome": "提升投递通过率"},
        ],
        "portfolioSuggestions": [
            "保留一个可演示、可讲清职责和结果的真实项目",
            "为项目补充问题背景、技术方案、个人贡献和结果",
        ],
        "cityAdvice": (
            f"优先关注 {target_city} 的校招与实习机会，结合远程和异地投递提升机会。"
            if target_city
            else "优先关注目标行业集中城市，同时保留远程和异地投递选项。"
        ),
        "riskWarnings": [
            "不要把课程作业或团队成果写成完全独立完成",
            "不要补写不存在的公司、实习或技能熟练度",
            "如果项目经历较少，优先补强作品质量而不是堆砌关键词",
        ],
        "profileSummary": {
            "major": major,
            "grade": grade,
            "skillsCount": len(skills),
            "interestsCount": len(interests),
            "hasExperience": bool(experience),
        },
    }


def generate_application_strategy(
    client: SiliconFlowClient,
    student_profile: Dict[str, Any],
    resume_context: Dict[str, Any],
    job_requirements: Dict[str, Any],
    match_result: Dict[str, Any],
) -> Dict[str, Any]:
    system = (
        "You are a truthful application-strategy assistant for university students. "
        "Base advice on the student's real background, resume context, job requirements, and match diagnosis. "
        "Never encourage fabrication. Output JSON only."
    )
    user = f"""
Generate an application strategy in JSON.

Required JSON shape:
{{
  "shouldApply": true,
  "priority": "high/medium/low",
  "resumeVersionAdvice": "which resume version to use and what to emphasize",
  "applicationMessage": "an honest outreach message",
  "riskWarnings": ["risk"],
  "resumeContentToImprove": ["specific resume improvement"],
  "bestChannels": ["official site"],
  "followUpPlan": ["follow-up action"]
}}

Rules:
- If must-have requirements are clearly unmet, allow shouldApply=false or lower priority.
- applicationMessage must stay honest and evidence-based.
- resumeContentToImprove must point to concrete modules, evidence, or missing proof.

student profile:
```json
{student_profile}
```

resume context:
```json
{resume_context}
```

job requirements:
```json
{job_requirements}
```

match diagnosis:
```json
{match_result}
```
"""
    content = client.chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=2400,
    )
    return _json_or_error(content, "application strategy result is not a JSON object")


def generate_interview_prepare(
    client: SiliconFlowClient,
    student_profile: Dict[str, Any],
    resume_context: Dict[str, Any],
    job_requirements: Dict[str, Any],
    match_result: Dict[str, Any],
) -> Dict[str, Any]:
    system = (
        "You are an interview coach for university students. "
        "Generate preparation material grounded in real resume evidence, job requirements, and match gaps. "
        "Never encourage fabrication. Output JSON only."
    )
    user = f"""
Generate interview preparation in JSON.

Required JSON shape:
{{
  "highFrequencyQuestions": [
    {{"question": "question", "answerFramework": "framework", "scoreDimensions": ["dimension"]}}
  ],
  "resumeFollowUpQuestions": [
    {{"question": "question", "riskPoint": "risk"}}
  ],
  "projectQuestions": [
    {{"question": "question", "answerFramework": "goal-solution-problem-result"}}
  ],
  "behavioralQuestions": [
    {{"question": "question", "answerFramework": "STAR"}}
  ],
  "answerFrameworks": [
    {{"name": "STAR", "usage": "behavioral interview", "structure": ["Situation", "Task", "Action", "Result"]}}
  ],
  "scoreDimensions": ["dimension"],
  "riskPoints": ["risk"],
  "practicePlan": ["action"]
}}

student profile:
```json
{student_profile}
```

resume context:
```json
{resume_context}
```

job requirements:
```json
{job_requirements}
```

match diagnosis:
```json
{match_result}
```
"""
    content = client.chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=3000,
    )
    return _json_or_error(content, "interview preparation result is not a JSON object")


def normalize_student_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    def _list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    return {
        "major": str(raw.get("major") or ""),
        "grade": str(raw.get("grade") or ""),
        "skills": _list(raw.get("skills")),
        "experience": str(raw.get("experience") or ""),
        "targetCity": str(raw.get("targetCity") or ""),
        "interests": _list(raw.get("interests")),
    }
