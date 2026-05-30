import unittest
from unittest.mock import patch

from app.api import resume_routes
from app.api.resume_routes import ResumeOptimizeRequest
from app.services.resume_optimize import _normalize_optimization_result


class _StubClient:
    def __init__(self, *args, **kwargs) -> None:
        self.model = "stub-model"


class OptimizeResumePipelineTests(unittest.TestCase):
    @patch.object(resume_routes, "SiliconFlowClient", _StubClient)
    def test_run_resume_optimize_pipeline_keeps_separated_sections(self) -> None:
        req = ResumeOptimizeRequest(
            rawResumeText="张三\n学生会宣传部，负责活动策划\n校园二手平台，负责前端开发\nVue、TypeScript\n英语六级",
            sections=[
                {"name": "校园经历", "content": "学生会宣传部，负责活动策划"},
                {"name": "项目经历", "content": "校园二手平台，负责前端开发"},
                {"name": "技能", "content": "Vue、TypeScript"},
                {"name": "证书/奖项", "content": "英语六级"},
            ],
            jobRequirements={
                "title": "前端实习生",
                "responsibilities": "负责前端页面开发",
                "must_haves": ["熟悉 Vue"],
                "nice_to_haves": ["有校园项目经验"],
                "keywords": ["Vue", "TypeScript"],
            },
        )

        raw_result = {
            "summary": "已完成岗位定制优化",
            "optimized_resume": {
                "target_title": "前端实习生",
                "sections": [
                    {
                        "name": "校园/社团经历",
                        "module_type": "campus",
                        "before": "学生会宣传部，负责活动策划",
                        "after": "学生会宣传部，负责活动策划与内容发布",
                        "reason": "突出校园执行经历",
                    },
                    {
                        "name": "项目经历",
                        "module_type": "projects",
                        "before": "校园二手平台，负责前端开发",
                        "after": "校园二手平台，负责前端页面开发与交互实现",
                        "reason": "突出项目动作",
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
                        "reason": "单独集中展示证明材料",
                    },
                ],
            },
        }

        normalized_result = _normalize_optimization_result(
            raw_result,
            req.rawResumeText,
            req.sections,
            req.jobRequirements,
        )

        with patch.object(resume_routes, "SiliconFlowClient", _StubClient), patch.object(
            resume_routes,
            "optimize_resume_for_job",
            return_value=normalized_result,
        ):
            result = resume_routes._run_resume_optimize_pipeline(req)

        block_keys = [item["key"] for item in result["normalizedBlocks"]]
        titles = [item["title"] for item in result["finalResumeSections"]]

        self.assertIn("campus_experience", block_keys)
        self.assertIn("projects", block_keys)
        self.assertIn("skills", block_keys)
        self.assertIn("certificates", block_keys)
        self.assertIn("校园/社团经历", titles)
        self.assertIn("专业技能", titles)
        self.assertIn("证书/奖项", titles)
        self.assertTrue(result["templateReady"])
        self.assertIn("蓝桥杯省赛二等奖", result["finalResumeText"])

    def test_timeout_fallback_returns_renderable_sections(self) -> None:
        req = ResumeOptimizeRequest(
            rawResumeText="李四\n社团负责人\nReact、Python\n英语六级",
            sections=[
                {"name": "社团经历", "content": "社团负责人"},
                {"name": "技能", "content": "React、Python"},
                {"name": "证书/奖项", "content": "英语六级"},
            ],
            jobRequirements={
                "title": "产品运营实习生",
                "responsibilities": "负责活动运营",
                "must_haves": ["良好沟通能力"],
                "keywords": ["运营", "沟通"],
            },
        )

        result = resume_routes._resume_optimize_timeout_fallback(req)

        self.assertEqual(result["fallback_status"], "resume_optimize_timeout_fallback")
        self.assertTrue(result["final_resume_sections"])
        self.assertTrue(result["templateReady"])
        self.assertIn("专业技能", [item["title"] for item in result["final_resume_sections"]])


if __name__ == "__main__":
    unittest.main()
