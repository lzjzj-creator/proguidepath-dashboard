from typing import Any, Dict, List

from app.services.siliconflow_client import SiliconFlowClient, extract_json_object
from app.services.resume_ocr import truncate_for_llm


def llm_generate_suggestions(client: SiliconFlowClient, resume_text: str, sections: Any) -> Any:
    truncated = truncate_for_llm(resume_text, max_chars=14000)

    system = (
        "你是简历优化教练与面试官。"
        "根据用户简历的各模块内容，给出可执行的修改建议。"
        "输出必须是 JSON，不要输出任何 JSON 之外的文字。"
    )

    user = f"""
你将获得两部分输入：
1) 简历完整文本（可能有噪声）
2) 已识别的简历模块 sections（每个模块包含 name 与 content）

请逐模块给出修改建议。要求：
- issues：指出当前模块的常见问题（最多 3-5 条）
- recommendations：给出具体怎么改（最多 3-5 条，尽量可落地）
- rewrite_example：给出一段“改写示例”（尽量贴近原意，但更简洁更量化；若原内容缺失则给出推荐写法）

输出 JSON，格式如下：
{{
  "overall_summary": "对整份简历的简短总结（1-3 句）",
  "items": [
    {{
      "name": "模块名称（与 sections 中一致）",
      "issues": ["..."],
      "recommendations": ["..."],
      "rewrite_example": "..."
    }}
  ]
}}

sections 输入如下（JSON）：
```json
{sections}
```

简历完整文本如下：
```text
{truncated}
```
"""

    content = client.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.25,
        max_tokens=2200,
    )
    return extract_json_object(content)

