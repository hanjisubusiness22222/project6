"""
나라장터 Open API 입찰공고 수집 모듈 (팀원 1 담당 파트)
공공데이터포털(data.go.kr) 조달청_나라장터 입찰공고정보서비스를 연동하여
AI/LLM/데이터 관련 실시간 용역 입찰 공고를 수집합니다.
표준 라이브러리만 사용합니다.
"""

from datetime import datetime, timedelta
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

KST = ZoneInfo("Asia/Seoul")

# 조달청_나라장터 입찰공고정보서비스 용역(Service) 입찰공고 조회 API
ENDPOINT_URL = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServcPPSSrch"

DEFAULT_KEYWORDS = ["인공지능", "AI", "생성형", "LLM", "데이터구축"]


def mask_key(url: str) -> str:
    """로그 출력용: URL 내 인증키 값을 ***로 가립니다."""
    return re.sub(r"((?:serviceKey|ServiceKey)=)[^&]+", r"\1***", str(url))


def build_request_url(api_key: str, keyword: str, start_dt: str, end_dt: str, num_of_rows: int = 100, page_no: int = 1) -> str:
    """조달청 API 요청 URL을 생성합니다."""
    # Decoding 키를 urlencode로 안전하게 변환
    params = {
        "serviceKey": api_key.strip(),
        "numOfRows": str(num_of_rows),
        "pageNo": str(page_no),
        "inqryDiv": "1",            # 1: 공고일시 기준
        "inqryBgnDate": start_dt,   # YYYYMMDD0000
        "inqryEndDate": end_dt,     # YYYYMMDD2359
        "bidNtceNm": keyword,       # 공고명 검색 키워드
        "type": "json"              # JSON 형식 응답
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"{ENDPOINT_URL}?{query_string}"


def fetch_tenders_by_keyword(api_key: str, keyword: str, start_dt: str, end_dt: str) -> list[dict]:
    """단일 키워드로 나라장터 API를 호출하여 공고 목록을 반환합니다."""
    url = build_request_url(api_key, keyword, start_dt, end_dt)
    masked = mask_key(url)
    print(f"📡 [API 요청] 키워드 '{keyword}' 수집 중... ({masked})")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AIPublicTenderMonitor/1.0)",
            "Accept": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode("utf-8")
            data = json.loads(content)
            
            # 응답 구조 파싱
            body = data.get("response", {}).get("body", {})
            items = body.get("items", [])
            
            if isinstance(items, dict):
                item = items.get("item", [])
                if isinstance(item, list):
                    return item
                elif isinstance(item, dict):
                    return [item]
                return []
            elif isinstance(items, list):
                return items
            return []

    except urllib.error.HTTPError as e:
        print(f"⚠️ [API 경고] HTTP {e.code} 응답 ({keyword})")
        return []
    except json.JSONDecodeError:
        print(f"⚠️ [API 경고] 응답이 JSON 형식이 아닙니다 (인증키 오류 또는 점검 중)")
        return []
    except Exception as e:
        print(f"⚠️ [API 오류] 호출 실패 ({keyword}): {e}")
        return []


def collect_ai_tenders(api_key: str | None = None, days: int = 14) -> list[dict]:
    """
    여러 AI 키워드로 나라장터 API를 호출하고 공고번호(bidNtceNo) 기준으로 중복을 제거하여 반환합니다.
    인증키가 없으면 빈 목록을 돌려줍니다.
    """
    if not api_key:
        api_key = os.environ.get("DATA_GO_KR_KEY")

    if not api_key:
        print("ℹ️ DATA_GO_KR_KEY 환경변수가 설정되지 않았습니다.")
        return []

    now = datetime.now(KST)
    start_date = (now - timedelta(days=days)).strftime("%Y%m%d0000")
    end_date = now.strftime("%Y%m%d2359")

    all_items = []
    seen_ids = set()

    for kw in DEFAULT_KEYWORDS:
        items = fetch_tenders_by_keyword(api_key, kw, start_date, end_date)
        for item in items:
            notice_no = item.get("bidNtceNo")
            if notice_no and notice_no not in seen_ids:
                seen_ids.add(notice_no)
                all_items.append(item)

    print(f"[API 완료] 총 {len(all_items)}건의 고유 공고 수집 완료")
    return all_items


def get_tenders(fixture_path: str = "fixtures/sample_tenders.json") -> list[dict]:
    """
    인증키가 등록되어 있으면 실제 나라장터 API를 호출하고,
    인증키가 없거나 API 호출 결과가 0건이면 fixture 모의 데이터를 읽어서 반환합니다.
    """
    api_key = os.environ.get("DATA_GO_KR_KEY")
    items = []

    if api_key:
        items = collect_ai_tenders(api_key)

    if not items:
        if os.path.exists(fixture_path):
            print(f"[대체 실행] 로컬 모의 응답({fixture_path}) 데이터를 사용합니다.")
            with open(fixture_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("response", {}).get("body", {}).get("items", [])
        else:
            print("[경고] 모의 데이터 파일을 찾을 수 없습니다.")

    return items


if __name__ == "__main__":
    tenders = get_tenders()
    print(f"수집 결과: {len(tenders)}건")
