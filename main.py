"""
AI Public Tender Monitor - Main Pipeline Orchestrator
3개 파트(API 수집 -> 데이터 가공 -> 대시보드 데이터 저장 & 디스코드 알림)를
하나로 연결하는 통합 실행 파일입니다.
"""

import json
import os
from pathlib import Path
import sys

# Windows 콘솔 인코딩 대응
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tender_api import get_tenders
from process_data import process, atomic_write
from notify_discord import send_discord_notification


def run_pipeline(output_path: str = "data/ai_projects.json") -> int:
    print("=" * 60)
    print("🚀 [파이프라인 시작] 나라장터 AI 프로젝트 모니터링 데이터 갱신")
    print("=" * 60)

    # 1단계: API 데이터 수집 (팀원 1 모듈)
    print("\n[1/3] 나라장터 공고 수집 시작...")
    raw_items = get_tenders()
    print(f"-> 수집 완료: 원시 공고 {len(raw_items)}건 확보")

    # 2단계: 데이터 정제·분류 및 통계 집계 (팀원 2 모듈)
    print("\n[2/3] AI 공고 필터링, 카테고리 태깅 및 통계 집계 중...")
    processed_result = process(raw_items)
    summary = processed_result.get("summary", {})
    print(f"-> 정제 완료: AI 관련 공고 {summary.get('total_count', 0)}건 선별")
    print(f"-> 총 발주 예산: {summary.get('total_budget', 0):,}원")

    # 3단계: data/ai_projects.json 파일 저장
    output_file = Path(output_path)
    content = json.dumps(processed_result, ensure_ascii=False, indent=2) + "\n"
    atomic_write(output_file, content)
    print(f"-> 파일 저장 완료: {output_file.resolve()}")

    # 4단계: 디스코드 웹훅 알림 발송 (팀원 3 모듈)
    print("\n[3/3] 디스코드 웹훅 알림 확인 중...")
    send_discord_notification()

    print("\n" + "=" * 60)
    print("🎉 [파이프라인 완료] 모든 단계가 성공적으로 종료되었습니다.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
