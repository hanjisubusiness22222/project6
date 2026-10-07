import json
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import process_data  # noqa: E402

FIXTURE = ROOT / "fixtures" / "sample_tenders.json"
NOW = datetime(2026, 10, 7, 8, 0, tzinfo=process_data.KST)


def load_fixture():
    with FIXTURE.open(encoding="utf-8") as source:
        return json.load(source)


def raw_item(number, title, budget="100", agency="기관"):
    return {"bidNtceNo": number, "bidNtceNm": title, "dminsttNm": agency, "asignBdgtAmt": budget,
            "bidClseDt": "2026-10-20 10:00:00", "bidNtceDt": "2026-10-01 09:00:00", "bidNtceDtlUrl": "https://example.com"}


class FixtureResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = process_data.process(load_fixture(), now=NOW)
        cls.ids = [project["id"] for project in cls.result["projects"]]

    def test_output_follows_readme_format(self):
        self.assertEqual(set(self.result), {"updated_at", "summary", "projects"})
        self.assertEqual(self.result["updated_at"], "2026-10-07T08:00:00+09:00")
        for key in ("total_count", "total_budget", "top_keywords"):
            self.assertIn(key, self.result["summary"])
        for project in self.result["projects"]:
            self.assertEqual(list(project), ["id", "title", "agency", "budget", "close_date", "category", "link"])
            self.assertIsInstance(project["budget"], int)
            self.assertRegex(project["close_date"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

    def test_filters_out_simple_procurement(self):
        for excluded in ("20261001007", "20261001008", "20261001009"):  # PC 납품, GPU 서버 구매, 복합기 임차
            self.assertNotIn(excluded, self.ids)
        self.assertEqual(self.result["summary"]["total_count"], 8)

    def test_duplicate_notice_kept_once(self):
        self.assertEqual(self.ids.count("20261001002"), 1)
        self.assertEqual(len(self.ids), len(set(self.ids)))

    def test_empty_budget_becomes_zero(self):
        project = next(p for p in self.result["projects"] if p["id"] == "20261001006")
        self.assertEqual(project["budget"], 0)

    def test_total_budget(self):
        expected = 1500000000 + 850000000 + 420000000 + 2300000000 + 3200000000 + 0 + 640000000 + 760000000
        self.assertEqual(self.result["summary"]["total_budget"], expected)

    def test_top5_budget(self):
        top = [project["id"] for project in self.result["summary"]["top_budget_projects"]]
        self.assertEqual(top, ["20261001005", "20261001004", "20261001001", "20261001002", "20261001011"])

    def test_top_agencies(self):
        first = self.result["summary"]["top_agencies"][0]
        self.assertEqual(first, {"agency": "서울특별시", "count": 2, "total_budget": 2940000000})

    def test_categories(self):
        categories = {project["id"]: project["category"] for project in self.result["projects"]}
        self.assertEqual(categories["20261001001"], "생성형AI")
        self.assertEqual(categories["20261001003"], "챗봇")
        self.assertEqual(categories["20261001004"], "컴퓨터비전")
        self.assertEqual(categories["20261001005"], "데이터구축")
        self.assertEqual(categories["20261001006"], "기타AI")

    def test_new_notice_counts(self):
        summary = self.result["summary"]
        self.assertEqual(summary["new_this_month"], 5)  # 10/01, 10/02, 10/05, 10/06, 10/06
        self.assertEqual(summary["new_last_7_days"], 6)  # 위 5건 + 09/30


class UnitTest(unittest.TestCase):
    def test_is_relevant(self):
        self.assertTrue(process_data.is_relevant("생성형 AI 민원 서비스 구축"))
        self.assertFalse(process_data.is_relevant("사무용 PC 납품"))
        self.assertFalse(process_data.is_relevant("AI 학습용 서버 구매"))
        self.assertFalse(process_data.is_relevant("청사 복합기 임차"))
        self.assertFalse(process_data.is_relevant("MAIN 홈페이지 개편"))  # 'AI'가 영단어 일부인 경우

    def test_categorize_priority_and_spacing(self):
        self.assertEqual(process_data.categorize("LLM 기반 민원 챗봇"), "생성형AI")
        self.assertEqual(process_data.categorize("학습 데이터 구축"), "데이터구축")
        self.assertEqual(process_data.categorize("AI 수요 예측"), "기타AI")

    def test_parse_budget(self):
        self.assertEqual(process_data.parse_budget(""), 0)
        self.assertEqual(process_data.parse_budget(None), 0)
        self.assertEqual(process_data.parse_budget("1,500,000"), 1500000)
        self.assertEqual(process_data.parse_budget("850000000.0"), 850000000)
        self.assertEqual(process_data.parse_budget("미정"), 0)

    def test_item_shapes_normalized(self):
        one = raw_item("1", "AI 챗봇 구축")
        self.assertEqual(process_data.process({"items": {"item": one}}, now=NOW)["summary"]["total_count"], 1)
        self.assertEqual(process_data.process({"items": ""}, now=NOW)["summary"]["total_count"], 0)
        self.assertEqual(process_data.process([one, raw_item("2", "AI 영상 분석")], now=NOW)["summary"]["total_count"], 2)

    def test_api_error_raises(self):
        with self.assertRaises(ValueError):
            process_data.process({"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}}})

    def test_main_writes_file(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "out" / "ai_projects.json"
            self.assertEqual(process_data.main(["--input", str(FIXTURE), "--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["summary"]["total_count"], 8)


if __name__ == "__main__":
    unittest.main()
