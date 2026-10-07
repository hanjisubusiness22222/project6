"""
나라장터 API 수집 모듈 단위 테스트 (팀원 1 파트)
"""

import unittest
from tender_api import mask_key, build_request_url, get_tenders


class TenderApiTest(unittest.TestCase):
    def test_mask_key_hides_service_key(self):
        url = "https://apis.data.go.kr/test?serviceKey=MY_SECRET_KEY_123&numOfRows=10"
        masked = mask_key(url)
        self.assertNotIn("MY_SECRET_KEY_123", masked)
        self.assertIn("serviceKey=***", masked)

    def test_build_request_url_params(self):
        url = build_request_url(
            api_key="TEST_KEY",
            keyword="인공지능",
            start_dt="202610010000",
            end_dt="202610072359",
            num_of_rows=50,
            page_no=1
        )
        self.assertIn("serviceKey=TEST_KEY", url)
        self.assertIn("type=json", url)
        self.assertIn("inqryDiv=1", url)
        self.assertIn("numOfRows=50", url)

    def test_get_tenders_fallback_loads_fixtures(self):
        # 환경변수 없이 로컬 fixture 로드 확인
        items = get_tenders("fixtures/sample_tenders.json")
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)
    def test_parse_xml_items_handles_g2b_xml_response(self):
        from tender_api import _parse_xml_items
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <response>
            <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
            <body>
                <items>
                    <item>
                        <bidNtceNo>20261099999</bidNtceNo>
                        <bidNtceNm>차세대 AI 챗봇 구축 사업</bidNtceNm>
                        <dminsttNm>조달청</dminsttNm>
                        <asignBdgtAmt>1200000000</asignBdgtAmt>
                        <bidClseDt>2026-10-31 18:00:00</bidClseDt>
                    </item>
                </items>
            </body>
        </response>"""
        items = _parse_xml_items(mock_xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["bidNtceNo"], "20261099999")
        self.assertEqual(items[0]["bidNtceNm"], "차세대 AI 챗봇 구축 사업")
        self.assertEqual(items[0]["asignBdgtAmt"], "1200000000")


if __name__ == "__main__":
    unittest.main()

