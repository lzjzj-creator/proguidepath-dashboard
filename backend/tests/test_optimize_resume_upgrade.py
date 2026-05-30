import unittest

from app.services.resume_ocr import normalize_optimize_sections
from app.services.resume_optimize import _normalize_optimization_result, optimize_resume_for_job


class _PromptCaptureClient:
    def __init__(self) -> None:
        self.messages = None

    def chat(self, *, messages, temperature, max_tokens, timeout_seconds=None, max_retries=0):
        self.messages = messages
        return """{
          "summary": "已生成",
          "optimized_resume": {
            "target_title": "前端实习生",
            "summary": "突出匹配证据",
            "sections": [
              {
                "name": "技能",
                "module_type": "skills",
                "before": "Vue、TypeScript",
                "after": "前端：Vue、TypeScript",
                "reason": "按类别整理"
              }
            ]
          }
        }"""


class OptimizeResumeUpgradeTests(unittest.TestCase):
    def test_normalize_optimize_sections_maps_sections_to_canonical_blocks(self):
        sections = [
            {"name": "教育经历", "content": "北京某大学 计算机科学与技术"},
            {"name": "校园经历", "content": "学生会宣传部，负责活动策划"},
            {"name": "实习经历", "content": "某科技公司前端实习"},
            {"name": "专业技能", "content": "Vue、TypeScript、Python"},
        ]

        result = normalize_optimize_sections("resume text", sections)

        self.assertEqual(result["recognitionMode"], "text-first")
        self.assertTrue(result["normalizedBlocks"])
        self.assertEqual(result["normalizedBlocks"][0]["key"], "education")
        self.assertEqual(result["normalizedBlocks"][1]["key"], "campus_experience")
        self.assertEqual(result["normalizedBlocks"][2]["key"], "practical_experience")
        self.assertEqual(result["normalizedBlocks"][3]["key"], "skills")
        self.assertEqual(result["sections"][0]["name"], "教育背景")
        self.assertEqual(result["sections"][1]["name"], "校园/社团经历")

    def test_normalize_optimize_sections_keeps_project_skills_and_certificates_separate(self):
        sections = [
            {"name": "项目经历", "content": "校园二手平台，负责前端开发与发布"},
            {"name": "实习经历", "content": "某科技公司前端实习，负责组件开发"},
            {"name": "技能", "content": "Vue、TypeScript、Python"},
            {"name": "证书/奖项", "content": "英语六级、蓝桥杯省赛二等奖"},
        ]

        result = normalize_optimize_sections("resume text", sections)
        keys = [item["key"] for item in result["normalizedBlocks"]]
        names = [item["name"] for item in result["sections"]]

        self.assertIn("projects", keys)
        self.assertIn("practical_experience", keys)
        self.assertIn("skills", keys)
        self.assertIn("certificates", keys)
        self.assertIn("项目经历", names)
        self.assertIn("技能", names)
        self.assertIn("证书/奖项", names)

    def test_normalize_optimization_result_exposes_final_resume_text(self):
        raw_result = {
            "summary": "总结",
            "optimized_resume": {
                "target_title": "前端实习生",
                "summary": "适合前端岗位",
                "sections": [
                    {
                        "name": "项目经历",
                        "module_type": "projects",
                        "before": "原始项目描述",
                        "after": "优化后的项目描述",
                        "reason": "突出前端项目成果",
                    }
                ],
            },
        }

        normalized = _normalize_optimization_result(
            raw_result,
            "张三\n北京某大学",
            [{"name": "项目经历", "content": "原始项目描述"}],
            {"title": "前端实习生"},
        )

        self.assertIn("final_resume_text", normalized)
        self.assertTrue(normalized["final_resume_text"].strip())
        self.assertIn("教育背景", normalized["final_resume_text"])
        self.assertEqual(normalized["finalResumeText"], normalized["final_resume_text"])

    def test_normalize_optimization_result_renders_campus_skills_and_certificates_sections(self):
        raw_result = {
            "summary": "总结",
            "optimized_resume": {
                "target_title": "前端实习生",
                "sections": [
                    {
                        "name": "校园/社团经历",
                        "module_type": "campus",
                        "before": "学生会宣传部，负责活动策划",
                        "after": "学生会宣传部，负责活动策划与内容发布",
                        "reason": "保留真实经历并突出执行动作",
                    },
                    {
                        "name": "技能",
                        "module_type": "skills",
                        "before": "Vue、TypeScript",
                        "after": "前端：Vue、TypeScript",
                        "reason": "按类别整理技能",
                    },
                    {
                        "name": "证书/奖项",
                        "module_type": "certificates",
                        "before": "英语六级",
                        "after": "英语六级\n蓝桥杯省赛二等奖",
                        "reason": "集中展示可验证证明",
                    },
                ],
            },
        }

        normalized = _normalize_optimization_result(
            raw_result,
            "张三\n学生会宣传部，负责活动策划\nVue、TypeScript\n英语六级",
            [
                {"name": "校园/社团经历", "content": "学生会宣传部，负责活动策划"},
                {"name": "技能", "content": "Vue、TypeScript"},
                {"name": "证书/奖项", "content": "英语六级"},
            ],
            {"title": "前端实习生"},
        )

        final_titles = [item["title"] for item in normalized["final_resume_sections"]]
        self.assertIn("校园/社团经历", final_titles)
        self.assertIn("专业技能", final_titles)
        self.assertIn("证书/奖项", final_titles)
        self.assertIn("校园/社团经历", normalized["final_resume_text"])
        self.assertIn("前端：Vue、TypeScript", normalized["final_resume_text"])
        self.assertIn("蓝桥杯省赛二等奖", normalized["final_resume_text"])

    def test_optimize_resume_for_job_prompt_template_does_not_crash(self):
        client = _PromptCaptureClient()

        result = optimize_resume_for_job(
            client,
            "张三\nVue、TypeScript\n英语六级",
            [
                {"name": "技能", "content": "Vue、TypeScript"},
                {"name": "证书/奖项", "content": "英语六级"},
            ],
            {
                "title": "前端实习生",
                "responsibilities": "负责前端开发",
                "must_haves": ["熟悉 Vue"],
                "keywords": ["Vue", "TypeScript"],
            },
        )

        self.assertIsNotNone(client.messages)
        self.assertEqual(result["optimized_resume"]["target_title"], "前端实习生")
        self.assertTrue(result["final_resume_text"].strip())


if __name__ == "__main__":
    unittest.main()
