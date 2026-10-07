"""
AI Public Tender Monitor - Discord Notification Module
팀원 3 (DevOps) 구현: 배포 시 또는 일일 스케줄 실행 시 디스코드 웹훅으로 요약 전송
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Windows 콘솔 인코딩 대응
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def format_budget(amount):
    """원화 금액을 억원/만원 단위로 포맷팅"""
    if not amount or not isinstance(amount, (int, float)):
        return "-"
    eok = int(amount // 100_000_000)
    remainder = int(amount % 100_000_000)
    man = int(remainder // 10_000)
    
    if eok > 0 and man > 0:
        return f"{eok:,}억 {man:,}만원"
    elif eok > 0:
        return f"{eok:,}억원"
    elif man > 0:
        return f"{man:,}만원"
    return f"{amount:,}원"

def send_discord_notification():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("[Discord] DISCORD_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print("   (알림 껍데기 준비 완료: GitHub Secrets에 DISCORD_WEBHOOK_URL을 등록하면 자동으로 작동합니다.)")
        return

    # JSON 데이터 로드
    json_path = os.path.join(os.path.dirname(__file__), "data", "ai_projects.json")
    if not os.path.exists(json_path):
        print(f"[Discord] 데이터 파일이 존재하지 않습니다: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    projects = data.get("projects", [])
    
    total_count = summary.get("total_count", len(projects))
    total_budget_str = format_budget(summary.get("total_budget", 0))
    closing_soon = summary.get("closing_soon_count", 0)

    # 주요 공고 상위 3건 추출
    top_projects = sorted(projects, key=lambda x: x.get("budget", 0), reverse=True)[:3]
    top_fields = []

    for i, p in enumerate(top_projects, start=1):
        title = p.get("title", "제목 없음")
        agency = p.get("agency", "-")
        budget = format_budget(p.get("budget", 0))
        close_date = p.get("close_date", "-")
        link = p.get("link", "https://www.g2b.go.kr")
        category = p.get("category", "기타")

        top_fields.append({
            "name": f"#{i} [{category}] {title[:32]}...",
            "value": f"• **수요기관**: {agency}\n• **배정예산**: `{budget}`\n• **마감일시**: `{close_date}`\n• [나라장터 공고 바로가기]({link})",
            "inline": False
        })

    # 디스코드 리치 임베드(Embed) 페이로드 구성
    payload = {
        "username": "AI 공공발주 알리미",
        "avatar_url": "https://img.icons8.com/color/96/artificial-intelligence.png",
        "embeds": [
            {
                "title": "[나라장터] 오늘의 신규 AI 공공 프로젝트 모니터링",
                "description": "공공데이터포털(data.go.kr) 조달청 나라장터 Open API에서 수집된 최신 인공지능 입찰 공고 현황입니다.",
                "url": "https://hanjisubusiness22222.github.io/project6/",
                "color": 6524913,  # Indigo (#6366f1)
                "fields": [
                    {
                        "name": "총 공고 수",
                        "value": f"**{total_count}건**",
                        "inline": True
                    },
                    {
                        "name": "총 발주 예산",
                        "value": f"**{total_budget_str}**",
                        "inline": True
                    },
                    {
                        "name": "마감 임박 (D-7)",
                        "value": f"**{closing_soon}건**",
                        "inline": True
                    },
                    *top_fields
                ],
                "footer": {
                    "text": "기술개발연구프로젝트 · AI Public Tender Monitor Dashboard",
                    "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                }
            }
        ]
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                print("[Discord] 디스코드 채널로 성공적으로 알림을 전송했습니다!")
            else:
                print(f"[Discord] 알림 전송 완료 (응답 코드: {resp.status})")
    except urllib.error.HTTPError as e:
        print(f"[Discord] HTTP 전송 오류: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[Discord] 전송 중 오류 발생: {e}")

if __name__ == "__main__":
    send_discord_notification()
