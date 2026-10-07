"""나라장터 원시 공고 목록을 정제·분류·집계하여 ai_projects.json을 만듭니다. 표준 라이브러리만 사용합니다."""

# ---------------------------------------------------------------------------
# 원시 항목 이름 → 출력 항목 이름 매핑 (팀원 1 모듈의 항목 이름이 바뀌면 여기만 고치세요)
# ---------------------------------------------------------------------------
FIELD_MAP = {
    "bidNtceNo": "id",           # 공고번호
    "bidNtceNm": "title",        # 공고명
    "dminsttNm": "agency",       # 수요기관
    "asignBdgtAmt": "budget",    # 배정예산
    "bidClseDt": "close_date",   # 마감일시
    "bidNtceDtlUrl": "link",     # 링크
}
# 출력에는 넣지 않고 주간/월간 신규 공고 수 집계에만 쓰는 원시 항목
NOTICE_DATE_FIELD = "bidNtceDt"  # 공고일시

import argparse
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")

# 공고명에 하나라도 있어야 AI 관련 공고로 봅니다. 공백을 지우고 대문자로 바꾼 뒤 비교합니다.
AI_KEYWORDS = ["인공지능", "AI", "LLM", "생성형", "챗봇", "머신러닝", "딥러닝", "거대언어모델", "초거대", "GPT"]
# AI 키워드가 있어도 단순 조달이면 제외합니다.
EXCLUDE_KEYWORDS = ["물품", "납품", "구매", "구입", "임차", "렌탈"]

# 위에서부터 먼저 맞는 카테고리 하나를 붙입니다. 아무것도 맞지 않으면 DEFAULT_CATEGORY입니다.
CATEGORY_RULES = [
    ("생성형AI", ["생성형", "LLM", "GPT", "거대언어모델", "초거대"]),
    ("챗봇", ["챗봇", "상담봇", "대화형"]),
    ("컴퓨터비전", ["영상", "이미지", "비전", "CCTV", "OCR", "객체인식", "안면인식"]),
    ("데이터구축", ["데이터구축", "학습데이터", "학습용데이터", "라벨링", "데이터셋"]),
]
DEFAULT_CATEGORY = "기타AI"

# top_keywords 후보: 표시 이름 → 공고명에서 찾을 단어들
KEYWORD_LABELS = {
    "생성형AI": ["생성형"],
    "LLM": ["LLM", "거대언어모델", "초거대"],
    "챗봇": ["챗봇", "상담봇"],
    "컴퓨터비전": ["영상", "이미지", "비전", "CCTV", "OCR"],
    "데이터구축": ["데이터구축", "학습데이터", "학습용데이터", "라벨링"],
    "딥러닝": ["딥러닝", "머신러닝"],
    "예측모델": ["예측"],
}
TOP_KEYWORD_LIMIT = 5
TOP_BUDGET_LIMIT = 5
TOP_AGENCY_LIMIT = 5


def normalize_text(text):
    """키워드 비교용: 공백을 모두 지우고 대문자로 바꿉니다."""
    return re.sub(r"\s+", "", str(text or "")).upper()


def contains_keyword(normalized, keyword):
    """영문 키워드는 앞뒤가 영문자가 아닐 때만 맞습니다('MAIN' 속 'AI' 방지). 한글은 부분 일치입니다."""
    keyword = normalize_text(keyword)
    if keyword.isascii():
        return re.search(rf"(?<![A-Z]){re.escape(keyword)}(?![A-Z])", normalized) is not None
    return keyword in normalized


def contains_any(text, keywords):
    normalized = normalize_text(text)
    return any(contains_keyword(normalized, keyword) for keyword in keywords)


def extract_items(raw):
    """API 응답 전체, body, items, 목록 어느 형태든 공고 목록(list)으로 정규화합니다."""
    data = raw
    if isinstance(data, dict) and "response" in data:
        header = data["response"].get("header", {})
        code = str(header.get("resultCode", "00"))
        if code not in ("00", "0", "0000"):
            raise ValueError(f"API 오류 응답입니다: {code} {header.get('resultMsg', '')}".strip())
        data = data["response"].get("body", {})
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if isinstance(data, dict) and "item" in data:
        data = data["item"]
    if data in (None, ""):
        return []
    if isinstance(data, dict):
        return [data]
    if not isinstance(data, list):
        raise ValueError("공고 목록을 찾을 수 없습니다. 목록 또는 API 응답 형식이어야 합니다.")
    for number, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{number}번째 공고는 객체여야 합니다.")
    return data


def parse_budget(value):
    """예산을 정수로 바꿉니다. 빈 값·숫자가 아닌 값은 0입니다. 쉼표와 소수점 문자열도 처리합니다."""
    if value is None or isinstance(value, bool):
        return 0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0
    try:
        return max(int(Decimal(text)), 0)
    except (InvalidOperation, ValueError):
        return 0


def parse_datetime(value):
    """'2026-10-24 10:00:00', '2026-10-24 10:00', '202610241000' 형식을 datetime(KST)으로 바꿉니다."""
    text = str(value or "").strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    for length, pattern in ((14, "%Y%m%d%H%M%S"), (12, "%Y%m%d%H%M"), (8, "%Y%m%d")):
        if len(digits) >= length:
            try:
                return datetime.strptime(digits[:length], pattern).replace(tzinfo=KST)
            except ValueError:
                continue
    return None


def format_close_date(value):
    parsed = parse_datetime(value)
    return parsed.strftime("%Y-%m-%d %H:%M") if parsed else str(value or "").strip()


def is_relevant(title):
    """AI 키워드가 있고 단순 조달(물품·납품·구매·임차 등)이 아닌 공고만 남깁니다."""
    return contains_any(title, AI_KEYWORDS) and not contains_any(title, EXCLUDE_KEYWORDS)


def categorize(title):
    for category, keywords in CATEGORY_RULES:
        if contains_any(title, keywords):
            return category
    return DEFAULT_CATEGORY


def keyword_labels(title):
    return [label for label, keywords in KEYWORD_LABELS.items() if contains_any(title, keywords)]


def deduplicate(items):
    """같은 공고번호는 처음 나온 하나만 남깁니다. 공고번호가 없는 항목은 버립니다."""
    id_field = next(raw for raw, out in FIELD_MAP.items() if out == "id")
    seen = set()
    result = []
    for item in items:
        key = str(item.get(id_field, "")).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def to_project(item):
    """원시 항목을 README 형식의 project로 바꿉니다."""
    project = {out: item.get(raw, "") for raw, out in FIELD_MAP.items()}
    project["id"] = str(project["id"]).strip()
    project["title"] = str(project["title"]).strip()
    project["agency"] = str(project["agency"]).strip()
    project["budget"] = parse_budget(project["budget"])
    project["close_date"] = format_close_date(project["close_date"])
    project["category"] = categorize(project["title"])
    project["link"] = str(project["link"]).strip()
    return {key: project[key] for key in ("id", "title", "agency", "budget", "close_date", "category", "link")}


def build_summary(projects, notice_dates, now):
    total_budget = sum(project["budget"] for project in projects)

    keyword_counter = Counter()
    for project in projects:
        keyword_counter.update(set(keyword_labels(project["title"])))
    top_keywords = [label for label, _ in sorted(keyword_counter.items(), key=lambda pair: (-pair[1], pair[0]))]

    top_budget = sorted(projects, key=lambda project: (-project["budget"], project["id"]))[:TOP_BUDGET_LIMIT]

    agency_stats = {}
    for project in projects:
        stat = agency_stats.setdefault(project["agency"], {"agency": project["agency"], "count": 0, "total_budget": 0})
        stat["count"] += 1
        stat["total_budget"] += project["budget"]
    top_agencies = sorted(agency_stats.values(), key=lambda stat: (-stat["count"], -stat["total_budget"], stat["agency"]))

    category_counts = Counter(project["category"] for project in projects)
    week_start = now - timedelta(days=7)
    dated = [notice for notice in notice_dates if notice is not None]

    return {
        "total_count": len(projects),
        "total_budget": total_budget,
        "top_keywords": top_keywords[:TOP_KEYWORD_LIMIT],
        "top_budget_projects": [
            {key: project[key] for key in ("id", "title", "agency", "budget", "category")} for project in top_budget
        ],
        "top_agencies": top_agencies[:TOP_AGENCY_LIMIT],
        "category_counts": {category: category_counts.get(category, 0)
                            for category in [name for name, _ in CATEGORY_RULES] + [DEFAULT_CATEGORY]},
        "new_last_7_days": sum(1 for notice in dated if week_start <= notice <= now),
        "new_this_month": sum(1 for notice in dated if (notice.year, notice.month) == (now.year, now.month) and notice <= now),
    }


def process(raw, now=None):
    """원시 응답(또는 공고 목록)을 받아 ai_projects.json 형식의 dict를 돌려줍니다."""
    now = (now or datetime.now(KST)).astimezone(KST)
    items = deduplicate(extract_items(raw))
    title_field = next(raw_key for raw_key, out in FIELD_MAP.items() if out == "title")
    relevant = [item for item in items if is_relevant(item.get(title_field, ""))]
    projects = [to_project(item) for item in relevant]
    notice_dates = [parse_datetime(item.get(NOTICE_DATE_FIELD)) for item in relevant]
    summary = build_summary(projects, notice_dates, now)
    # 화면 기본 순서는 마감 임박순입니다.
    projects.sort(key=lambda project: (project["close_date"] or "9999", project["id"]))
    return {
        "updated_at": now.isoformat(timespec="seconds"),
        "summary": summary,
        "projects": projects,
    }


def atomic_write(output, content):
    """같은 폴더에 임시 파일을 완성한 뒤 교체하여 기존 파일의 손상을 막습니다."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="나라장터 원시 공고를 ai_projects.json으로 정제·집계합니다.")
    parser.add_argument("--input", required=True, type=Path, help="원시 공고 JSON 경로")
    parser.add_argument("--output", default=Path("_site/ai_projects.json"), type=Path, help="출력 JSON 경로")
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding="utf-8") as source:
            raw = json.load(source)
        result = process(raw)
        atomic_write(args.output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError) as error:
        print(f"처리 실패: {error}", file=sys.stderr)
        return 1
    summary = result["summary"]
    print(f"AI 공고 {summary['total_count']}건 · 총 예산 {summary['total_budget']:,}원")
    print(f"저장 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
