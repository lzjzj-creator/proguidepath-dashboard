import unittest
from unittest.mock import patch

from app.api import resume_routes


class _StubRepo:
    def create_record(self, filename: str) -> int:
        return 1

    def set_ocr_result(self, resume_id: int, extracted_text: str, sections) -> None:
        return None


class OcrPipelineTests(unittest.TestCase):
    def test_run_ocr_pipeline_skips_layout_analysis_after_llm_fallback(self) -> None:
        with patch.object(resume_routes, "ResumeRepo", return_value=_StubRepo()), patch.object(
            resume_routes,
            "extract_text_from_pdf_bytes",
            return_value="张三\nVue、TypeScript",
        ), patch.object(
            resume_routes,
            "llm_extract_sections",
            side_effect=RuntimeError("llm timeout"),
        ), patch.object(
            resume_routes,
            "fallback_extract_sections",
            return_value=[{"name": "技能", "content": "Vue、TypeScript"}],
        ), patch.object(resume_routes, "analyze_resume_layout") as mock_analyze_layout:
            result = resume_routes._run_ocr_pipeline("resume.pdf", b"%PDF-1.4 stub")

        self.assertGreater(result.resumeId, 0)
        self.assertTrue(result.sections)
        mock_analyze_layout.assert_not_called()


if __name__ == "__main__":
    unittest.main()
