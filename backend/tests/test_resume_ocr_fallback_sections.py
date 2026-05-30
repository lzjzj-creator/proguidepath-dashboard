import unittest

from app.services.resume_ocr import fallback_extract_sections


class ResumeOcrFallbackSectionTests(unittest.TestCase):
    def test_fallback_extract_sections_splits_mixed_resume_text_into_multiple_blocks(self) -> None:
        text = """
邱烨
男
专业：国际经济与贸易
求职意向：跨境电商运营专员
电话：150 1590 3928
地址：广东省珠海市
荣誉奖励
项目与运营经历
自我评价
深度参与速卖通、ozon 双平台全流程运营，完成 30+ SKU 上架并推动转化提升。
院校：韶关学院
第十届 OCALE 全国跨境电商创新创业能力大赛国家级团体一等奖及国家级个人一等奖
2025年1月10日至2025年2月10日
韶关狄卡科技有限公司
跨境电商运营实习生
2025年8月10日至今
项目主负责人
"""

        sections = fallback_extract_sections(text)
        names = [section["name"] for section in sections]

        self.assertIn("基本信息", names)
        self.assertIn("自我评价", names)
        self.assertIn("教育背景", names)
        self.assertIn("证书/奖项", names)
        self.assertIn("实习/工作经历", names)
        self.assertIn("项目经历", names)

    def test_fallback_extract_sections_separates_skill_style_lines_from_experience(self) -> None:
        text = """
刘键翎
电话：13531359344
2023.06-2024.06
党务助理
协助开展党建工作，负责文件归档与沟通对接。
外贸：掌握外贸全流程知识，熟悉报关、结算等实操，了解阿里巴巴国际站基础运营
办公：熟练使用 Office 办公软件，掌握基础 PS、Canva，可独立完成文案编辑及数据报表制作
2025 年国贸专业毕业，具备扎实的外贸理论与实操基础。
"""

        sections = fallback_extract_sections(text)
        name_to_content = {section["name"]: section["content"] for section in sections}

        self.assertIn("技能", name_to_content)
        self.assertIn("实习/工作经历", name_to_content)
        self.assertIn("自我评价", name_to_content)
        self.assertIn("外贸：掌握外贸全流程知识", name_to_content["技能"])
        self.assertIn("办公：熟练使用 Office 办公软件", name_to_content["技能"])


if __name__ == "__main__":
    unittest.main()
