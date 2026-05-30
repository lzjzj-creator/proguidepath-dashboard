import json
import unittest

from app.api.resume_routes import _load_resume_context
from app.services.career_flow import generate_application_strategy


class _StubRecord:
    def __init__(self, extracted_text: str) -> None:
        self.extracted_text = extracted_text


class _StubRepo:
    def get_record(self, resume_id: int):
        return _StubRecord(f"db text for {resume_id}")

    def get_sections(self, resume_id: int):
        return [{"name": "教育经历", "content": f"db sections for {resume_id}"}]


class _CaptureClient:
    def __init__(self) -> None:
        self.calls = []

    def chat(self, *, messages, temperature, max_tokens):
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return json.dumps(
            {
                "shouldApply": True,
                "priority": "中",
                "resumeVersionAdvice": "use tailored resume",
                "applicationMessage": "hello",
                "riskWarnings": [],
                "resumeContentToImprove": [],
                "bestChannels": ["官网"],
                "followUpPlan": ["3 days later"],
            },
            ensure_ascii=False,
        )


class ResumeContextTests(unittest.TestCase):
    def test_load_resume_context_prefers_inline_optimized_context_over_db_defaults(self):
        repo = _StubRepo()

        context = _load_resume_context(
            repo,
            resume_id=7,
            raw_resume_text="optimized raw resume",
            sections=[{"name": "项目经历", "content": "optimized section"}],
            structured_resume={"targetRole": "前端实习生"},
        )

        self.assertEqual(context["resumeId"], 7)
        self.assertEqual(context["rawResumeText"], "optimized raw resume")
        self.assertEqual(context["sections"], [{"name": "项目经历", "content": "optimized section"}])
        self.assertEqual(context["structuredResume"], {"targetRole": "前端实习生"})

    def test_application_strategy_prompt_contains_resume_context(self):
        client = _CaptureClient()
        resume_context = {
            "rawResumeText": "optimized raw resume",
            "sections": [{"name": "项目经历", "content": "built Vue dashboard"}],
            "structuredResume": {"targetRole": "前端实习生"},
        }

        generate_application_strategy(
            client,
            {"major": "软件工程"},
            resume_context,
            {"title": "前端实习生"},
            {"match_score": 82},
        )

        prompt = client.calls[0]["messages"][1]["content"]
        self.assertIn("optimized raw resume", prompt)
        self.assertIn("structuredResume", prompt)


if __name__ == "__main__":
    unittest.main()
