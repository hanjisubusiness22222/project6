# 🚀 AI 모? (나라장터 AI프로젝트 공고 모니터 대시보드)

> **공공데이터포털(data.go.kr) 조달청 나라장터 Open API**를 활용하여 전국의 공공기관·지자체·대학에서 발주하는 최신 인공지능(AI) 프로젝트 및 용역 입찰 공고를 실시간으로 수집하고 시각화하는 프로젝트 기획안입니다.

---

## 📌 1. 프로젝트 개요

* **프로젝트명**: AI 공공 발주 프로젝트 모니터링 대시보드
* **데이터 출처**: 공공데이터포털(data.go.kr) - **조달청_나라장터 입찰공고정보서비스**
* **핵심 목적**:
  * 흩어져 있는 국가·공공기관의 AI/LLM/데이터 구축 사업을 한눈에 모니터링
  * 최신 AI 공공 발주 트렌드 및 예산 규모 분석
  * GitHub Actions를 통한 일일 자동 갱신 및 GitHub Pages 무료 호스팅 배포

---

## 👥 2. 3인 팀 역할 분담 및 R&R (Role & Responsibilities)

3명의 기여도가 균형 있게 분배되고 코드 충돌(Git Conflict)을 방지할 수 있도록 파이프라인 단계별로 역할을 구성했습니다.

```
┌─────────────────────────────────┐      ┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│     팀원 1: API & 파이프라인     │ ───> │     팀원 2: 데이터 가공 & 분석   │ ───> │   팀원 3: 웹 대시보드 & DevOps   │
│     (Data Pipeline / Backend)   │      │       (Data / Core Logic)       │      │       (Frontend / DevOps)       │
└─────────────────────────────────┘      └─────────────────────────────────┘      └─────────────────────────────────┘
```

### 🔹 [팀원 1] 데이터 수집 & API 파이프라인 (Backend / API)
* **목표**: data.go.kr 나라장터 Open API 연동 및 안정적인 원시 데이터 수집
* **세부 작업**:
  * `조달청_나라장터 입찰공고정보서비스` API 활용 신청 및 Secret Key 환경변수 관리
  * 요청 모듈 구현: 공고명 검색(`인공지능`, `AI`, `LLM`, `생성형` 등) 및 날짜 범위 지정
  * 페이징 처리, 요청 제한(Quota) 대응, 타임아웃 및 재시도 로직 구현
  * 네트워크/응답 에러 예외 처리 및 유닛 테스트(`tests/`) 작성
* **담당 산출물**:
  * `tender_api.py` (API 호출 및 원시 데이터 수집 모듈)
  * `tests/test_tender_api.py` (API 테스트 코드)

---

### 🔹 [팀원 2] 데이터 정제, 분류 및 통계 집계 (Data / Core Logic)
* **목표**: 원시 공고 데이터를 분석하여 유의미한 비즈니스 지표 및 JSON 생성
* **세부 작업**:
  * 무관한 공고 필터링 (단순 물품 조달, 단순 PC 납품 등 제외)
  * **태그 자동 분류**: 공고명/본문 기반 카테고리 태깅 (`#생성형AI`, `#챗봇`, `#컴퓨터비전`, `#데이터구축`)
  * **핵심 통계 집계**:
    * 주간/월간 신규 공고 수 및 총 발주 예산 규모
    * 최고 예산 프로젝트 TOP 5 산출
    * 최다 발주 수요기관 순위 집계
  * 프론트엔드가 활용할 정규화된 최종 데이터(`ai_projects.json`) 내보내기
* **담당 산출물**:
  * `process_data.py` (데이터 필터링, 정제, 통계 로직)
  * `tests/test_process_data.py` (데이터 정제 검증 테스트)
  * `fixtures/sample_tenders.json` (테스트용 모의 응답 데이터)

---

### 🔹 [팀원 3] 웹 대시보드 UI & DevOps 배포 자동화 (Frontend & DevOps)
* **목표**: 모바일 반응형 웹 대시보드 구현 및 매일 아침 자동 빌드/배포 환경 구축
* **세부 작업**:
  * **대시보드 UI 제작**: HTML5 / CSS3 / Vanilla JavaScript 기반 모던 인터페이스
  * **인터랙티브 기능**: 키워드 실시간 검색, 예산순/마감임박순 정렬, 카테고리 필터링
  * **시각화 차트**: Chart.js 등을 활용한 분야별 발주 비중 및 예산 추이 차트 구현
  * **GitHub Actions 워크플로 구축**:
    * 매일 아침 정해진 시간(예: 평일 08:30 KST) 자동 실행 Cron 스케줄링
    * 빌드 결과물(`index.html`, `ai_projects.json`)을 GitHub Pages로 자동 배포
  * **문서화 총괄**: README 관리 및 프로젝트 보고서/발표 자료 취합
* **담당 산출물**:
  * `index.html`, `style.css`, `app.js` (또는 `main.py` 템플릿 렌더러)
  * `.github/workflows/deploy.yml` (CI/CD 자동화 워크플로)
  * `README.md` 및 프로젝트 문서

---

## 🛠️ 3. 기술 스택 및 데이터 규격

| 영역 | 기술 스택 | 설명 |
|---|---|---|
| **Language** | Python 3.12+ | 표준 라이브러리(`urllib`, `json`, `unittest` 등) 우선 활용 |
| **API** | data.go.kr Open API | 조달청_나라장터 입찰공고정보서비스 (용역 부문) |
| **Frontend** | HTML5, CSS3, JavaScript | 가볍고 빠른 반응형 웹 대시보드 |
| **CI / CD** | GitHub Actions | 주기적 자동 수집 (Cron) & Pages 배포 |
| **Hosting** | GitHub Pages | 정적 웹 호스팅 |

### 📋 공유 데이터 인터페이스 (`ai_projects.json`)
팀원 간 원활한 병렬 개발을 위해 사전에 약속하는 데이터 포맷입니다:

```json
{
  "updated_at": "2026-10-07T08:00:00+09:00",
  "summary": {
    "total_count": 24,
    "total_budget": 12850000000,
    "top_keywords": ["생성형AI", "LLM", "데이터구축"]
  },
  "projects": [
    {
      "id": "20261001001",
      "title": "생성형 AI 기반 대국민 민원 안내 서비스 구축 용역",
      "agency": "한국지역정보개발원",
      "budget": 1500000000,
      "close_date": "2026-10-24 10:00",
      "category": "생성형AI",
      "link": "https://www.g2b.go.kr/..."
    }
  ]
}
```

---

## 🤝 4. 깃허브 협업 및 충돌 방지 전략

1. **브랜치 분리 개발**:
   * `main`: 배포용 안정 브랜치 (직접 push 금지)
   * `feature/api`: 팀원 1 전용 (API 수집 모듈 개발)
   * `feature/data-logic`: 팀원 2 전용 (데이터 정제/분류 개발)
   * `feature/dashboard`: 팀원 3 전용 (UI 및 GitHub Actions 워크플로 개발)
2. **Mock Data(더미 데이터)를 활용한 병렬 개발**:
   * 팀원 3은 팀원 1의 API 개발이 끝날 때까지 기다리지 않고, 사전에 정의한 `sample_tenders.json`을 사용하여 프론트엔드 UI를 바로 개발할 수 있습니다.
3. **코드 리뷰 및 PR (Pull Request)**:
   * 최소 1인 이상의 승인 후 `main` 브랜치로 병합(Merge)하여 코드 품질을 유지합니다.

---

## 🔔 5. (선택) 디스코드 알림 연동 가이드

GitHub Actions가 실행될 때마다(또는 매일 아침 자동 스케줄링 시) 디스코드 채널로 오늘의 AI 공고 요약 알림을 받아볼 수 있는 모듈(`notify_discord.py`)이 내장되어 있습니다.

1. **디스코드 웹훅 생성**:
   * 알림을 받을 디스코드 채널 설정 → **연동** → **웹후크 만들기**
   * 웹후크 URL 복사 (`https://discord.com/api/webhooks/...`)
2. **GitHub Secrets 등록**:
   * 저장소 **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   * Name: `DISCORD_WEBHOOK_URL`
   * Secret: 복사한 디스코드 웹훅 URL 입력 후 등록
3. **확인**:
   * 등록 후 GitHub Actions가 실행되면 디스코드 채널로 예쁜 임베드 카드 형태의 공고 요약이 자동 발송됩니다.
   * 등록하지 않아도 웹 배포는 정상 동작합니다.

---

## ⚡ 6. 실행 및 테스트 방법 (Quick Start)

### 1) 단위 테스트 전체 실행 (18개 테스트)
```bash
python -m unittest discover -s tests -v
```

### 2) 전체 파이프라인 수집·정제·갱신 실행
```bash
# 인증키가 있으면 실제 API 호출, 없으면 모의 응답(fixtures)으로 자동 안전 실행
python main.py
```

### 3) 로컬 웹 대시보드 실행 및 확인
```bash
python -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```



