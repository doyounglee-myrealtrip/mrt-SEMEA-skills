# T&A 도시별 공헌이익 종합 분석

> 국가명 또는 도시명을 입력하면, 해당 지역의 T&A 공헌이익을 **도시별 × 퍼널 6단계 × 카테고리 × 상품** 레벨로 자동 진단하고, 문제와 해결 방향까지 도출합니다.
>
> **핵심 원칙: 모든 분석은 도시 레벨로 수행됩니다.** 국가명 입력은 "해당 국가의 Top 5 도시를 자동 식별"하기 위한 편의 기능입니다.

---

## 한 줄 요약

```
/tna-country-analysis 스페인      →  Top 5 도시 자동 식별  →  도시별 분석  →  Confluence 보고서
/tna-country-analysis Barcelona   →  해당 도시만 분석  →  Confluence 보고서
```

---

## 시작하기

### 전제 조건

이 스킬을 사용하려면 아래 3가지가 준비되어 있어야 합니다.

| # | 필요한 것 | 왜 필요한가 | 확인 방법 |
|---|----------|-----------|----------|
| 1 | **Claude Code** | 스킬을 실행하는 AI 코딩 에이전트 | 터미널에서 `claude` 입력 시 실행되면 OK |
| 2 | **BigQuery 접근 권한** (gcloud 인증) | 데이터 분석을 위해 BigQuery에 쿼리를 실행 | `bq query --use_legacy_sql=false "SELECT 1"` 실행 시 결과가 나오면 OK |
| 3 | **Confluence MCP 플러그인** | 분석 결과 보고서를 Confluence에 자동 발행 | Claude Code에서 `/mcp` 입력 후 Atlassian 항목이 보이면 OK |

> 아직 준비가 안 되어 있다면? Claude Code를 열고 "초기 세팅해줘"라고 말하면 자동으로 설치/인증을 진행합니다.

### 설치 방법

#### 방법 1: mrt-skill CLI (추천)

```bash
mrt-skill install tna-country-analysis
```

#### 방법 2: 수동 설치

```bash
# 1. 스킬 디렉토리 생성
mkdir -p .claude/skills/tna-country-analysis

# 2. SKILL.md 다운로드
curl -fsSL https://raw.githubusercontent.com/doyounglee-myrealtrip/mrt-SEMEA-skills/main/skills/data-analytics/tna-country-analysis/SKILL.md \
  -o .claude/skills/tna-country-analysis/SKILL.md
```

### 설치 확인

Claude Code를 열고 아래처럼 입력하면 스킬이 동작합니다:

```
/tna-country-analysis 스페인
```

---

## 이 스킬은 무엇을 하나요?

여행 T&A(투어·티켓·액티비티) 사업에서 **"이 도시의 공헌이익을 어떻게 늘릴 수 있을까?"** 라는 질문에 답합니다.

공헌이익에 영향을 주는 6가지 요소를 하나하나 진단하고, 문제가 있는 곳을 **도시 → 카테고리 → 개별 상품** 순서로 파고들어 원인을 특정합니다.

### 분석하는 6가지 요소 (퍼널)

```
① 유입    얼마나 많은 사람이 상품을 봤는가?         (상품 상세 UV)
    ↓
② 전환    본 사람 중 얼마나 샀는가?                 (CVR = 주문 / UV)
    ↓
③ 주문    총 몇 건의 주문이 발생했는가?             (주문건수)
    ↓
④ 객단가  한 건당 평균 얼마를 썼는가?               (AOV = GMV / 주문)
    ↓
⑤ 확정    주문 중 실제로 확정된 비율은?             (CFR = 확정GMV / GMV)
    ↓
⑥ 마진    확정 금액에서 비용 빼고 남는 비율은?      (CON_MARGIN / 확정GMV)
    ↓
= 공헌이익
```

이 6가지 중 **어디가 좋아지고, 어디가 나빠지고 있는지**를 도시별로 보여줍니다.

---

## 사용법

### 국가명으로 입력 (Top 5 도시 자동 식별)

```
/tna-country-analysis 스페인       → Barcelona, Seville, Madrid 등 Top 5 도시 자동 분석
/tna-country-analysis Spain        → 위와 동일
/tna-country-analysis 일본         → Tokyo, Osaka, Kyoto 등 Top 5 도시 자동 분석
/tna-country-analysis Japan        → 위와 동일
```

### 도시명으로 입력 (해당 도시만 분석)

```
/tna-country-analysis 바르셀로나    → Barcelona 한 도시만 심층 분석
/tna-country-analysis Barcelona    → 위와 동일
/tna-country-analysis 리스본        → Lisbon 한 도시만 심층 분석
/tna-country-analysis Lisbon       → 위와 동일
```

> **국문/영문 모두 입력 가능합니다.** 한글로 입력하면 자동으로 BigQuery의 영문 국가명/도시명으로 매핑됩니다. 영문으로 입력해도 됩니다. 편한 쪽으로 쓰세요!

### 한글 매핑 지원 목록

#### 국가

| 한글 | 영문 | | 한글 | 영문 |
|------|------|-|------|------|
| 스페인 | Spain | | 프랑스 | France |
| 일본 | Japan | | 이탈리아 | Italy |
| 태국 | Thailand | | 영국 | United Kingdom |
| 베트남 | Viet Nam | | 터키 | Turkey |
| 대만 | Taiwan | | 크로아티아 | Croatia |
| 싱가포르 | Singapore | | 포르투갈 | Portugal |
| 홍콩 | Hong Kong | | 그리스 | Greece |
| 호주 | Australia | | 체코 | Czech Republic |
| 미국 | United States | | 헝가리 | Hungary |
| 인도네시아 | Indonesia | | 모로코 | Morocco |

#### 주요 도시

| 한글 | 영문 | | 한글 | 영문 |
|------|------|-|------|------|
| 바르셀로나 | Barcelona | | 리스본 | Lisbon |
| 마드리드 | Madrid | | 포르투 | Porto |
| 세비야 | Seville | | 파리 | Paris |
| 그라나다 | Granada | | 로마 | Rome |
| 마요르카 | Majorca | | 도쿄 | Tokyo |
| 방콕 | Bangkok | | 오사카 | Osaka |
| 하노이 | Hanoi | | 교토 | Kyoto |
| 호치민 | Ho Chi Minh | | 프라하 | Prague |
| 이스탄불 | Istanbul | | 부다페스트 | Budapest |
| 두브로브니크 | Dubrovnik | | 아테네 | Athens |

위 목록에 없는 국가/도시도 영문으로 입력하면 BigQuery에서 자동 검색합니다.

### 지원 국가 (한글 매핑)

| 한글 | 영문 | | 한글 | 영문 |
|------|------|-|------|------|
| 스페인 | Spain | | 프랑스 | France |
| 일본 | Japan | | 이탈리아 | Italy |
| 태국 | Thailand | | 영국 | United Kingdom |
| 베트남 | Viet Nam | | 터키 | Turkey |
| 대만 | Taiwan | | 크로아티아 | Croatia |
| 싱가포르 | Singapore | | 포르투갈 | Portugal |
| 홍콩 | Hong Kong | | 그리스 | Greece |
| 호주 | Australia | | 체코 | Czech Republic |
| 미국 | United States | | 헝가리 | Hungary |
| 인도네시아 | Indonesia | | 모로코 | Morocco |

위 목록에 없는 국가도 영문으로 입력하면 BigQuery에서 자동 검색합니다.

---

## 분석 결과로 무엇을 알 수 있나요?

### Phase 1 — "지금 어디에 서 있나?"

| 산출물 | 설명 | 예시 |
|--------|------|------|
| **전체 YoY 성적표** | 공헌이익이 전년 대비 얼마나 성장/감소했는지 | "공헌이익 30억 → 35억 (+13.9%)" |
| **도시별 시즌 패턴** | 각 도시의 성수기/비수기가 언제인지 | "Barcelona 성수기: 9, 10, 12, 1월" |
| **퍼널 6단계 도시별 진단** | 6개 지표가 도시별로 어떻게 변했는지 | "Barcelona: UV ▲13% / CVR ▼1.8pp" |
| **문제 신호 목록** | 심각도별 문제 식별 | "Barcelona CVR 추세적 하락 — 심각도 높음" |

### Phase 2 — "문제가 어디서 발생하는가?"

| 산출물 | 설명 | 예시 |
|--------|------|------|
| **카테고리별 분해** | 문제 도시에서 어떤 상품군이 원인인지 | "GUIDE_TOUR 카테고리의 CVR ▼2.5pp가 핵심" |
| **유입 채널별 분해** | 어떤 마케팅 채널에서 문제가 발생하는지 | "자연유입 CVR 27%→18% 급락" |
| **취소 TOP 상품** | 취소가 집중되는 개별 상품 식별 | "알함브라 궁전 티켓 CFR 53%" |

### Phase 3 — "근본 원인은 무엇인가?"

| 산출물 | 설명 | 예시 |
|--------|------|------|
| **광고비 × 유입 효율** | 채널별 광고비 대비 유입/전환 효율 | "마케팅파트너: 광고비 ▼13%인데 ROAS 23.7 (최고)" |
| **체크아웃 퍼널 이탈** | 상세→체크아웃→결제 어느 단계에서 빠지는지 | "상세→체크아웃 ▼12pp (자연유입 주범)" |
| **취소 시점 패턴** | 언제, 왜 취소하는지 | "당일 취소 48%, 즉시 취소가 절반" |
| **쿠폰 ROI** | 쿠폰 투입 대비 추가 이익이 발생했는지 | "CPD 1원당 공헌이익 8원 증가 (양수)" |

### 최종 산출물 — Confluence 보고서

모든 분석이 완료되면 **개인 Confluence 스페이스에 종합 보고서가 자동 발행**됩니다. 보고서는 비개발자도 읽을 수 있도록 전문용어에 설명을 붙이고, 표/다이어그램/코드블록을 조합하여 작성됩니다.

---

## 분석 구조 (전체 흐름)

```
입력: 국가명 (예: "스페인")
  │
  ▼
Phase 0: 사전 준비
  ├── 국가명 매핑 (한글→영문)
  ├── 데이터 존재 확인
  └── Top 5 도시 자동 식별 (GMV 기준)
  │
  ▼
Phase 1: 현황 진단 (도시 레벨)                    ← 병렬 실행
  ├── 1-1. 도시별 시즌 패턴 (주문건수 기준, μ ± 0.5σ)
  ├── 1-2. 퍼널 6단계 도시별 YoY
  └── 1-3. 전체 YoY 성적표
  │
  ▼
  문제 신호 식별 (CVR 하락, CFR 하락, CPD 급증 등)
  │
  ▼
Phase 2: 문제별 드릴다운 (카테고리 + 상품 레벨)   ← 문제가 있는 도시만
  ├── 카테고리별 퍼널 지표 분해
  ├── 유입 채널(UTM)별 분해
  └── 취소 TOP 상품 식별 (L3)
  │
  ▼
Phase 3: 심층 분석                                ← 4개 병렬 실행
  ├── 3-1. 광고비 × 유입 효율 (투자부족 vs 효율악화 vs 전환품질)
  ├── 3-2. 체크아웃 퍼널 이탈 (상세→체크아웃→결제 단계별)
  ├── 3-3. 취소 사유·시점 패턴 (즉시취소 vs 사전취소 vs 파트너문제)
  └── 3-4. 쿠폰(CPD) ROI (1원당 증분 GM/공헌이익)
  │
  ▼
산출물: Confluence 종합 보고서 자동 발행
```

### 드릴다운 구조

문제를 찾을 때 위에서 아래로 좁혀갑니다:

```
Level 1: 도시              "Barcelona에서 문제가 있다"
  └─ Level 2: 카테고리      "그중 GUIDE_TOUR 카테고리가 원인이다"
       └─ Level 3: 상품      "특히 사그라다 파밀리아 투어의 취소율이 40%다"
```

---

## 데이터 소스

| 데이터 | 테이블 | 용도 |
|--------|--------|------|
| 주문/GMV/공헌이익/CFR/CPD | `edw_fpna.MART_FPNA_NONAIR_PROFIT_D` | 퍼널 ③④⑤⑥ |
| 상품 상세 UV/CVR | `edw_mart.MART_BIZ_LOG_PID_CONVERSION_D` + `MART_PRODUCT_D` | 퍼널 ①② |
| 광고비/ROAS | `business.mkt_dashboard_raw_data` | 채널 효율 분석 |

---

## 분석 기간

- **기본**: 최근 24개월 (오늘 기준 2년)
- **비교 방식**: 항상 YoY (전년 동기 대비). 시즌 효과를 제거하기 위해 같은 시기끼리 비교합니다.
- **시즌 분류**: 도시별로 독립 분류. 같은 국가라도 도시마다 성수기/비수기가 다릅니다.

---

## FAQ

### Q: 분석에 얼마나 걸리나요?
쿼리 실행과 분석을 병렬로 진행합니다. 국가 데이터 규모에 따라 다르지만, 보통 Phase 1-3 전체가 15-30분 정도 소요됩니다.

### Q: T&A 외에 숙박이나 항공도 분석할 수 있나요?
이 스킬은 T&A(투어/티켓/액티비티) 전용입니다. 숙박/항공은 데이터 구조와 퍼널이 다르므로 별도 스킬이 필요합니다.

### Q: 특정 도시만 분석하고 싶으면?
도시명을 직접 입력하면 됩니다: `/tna-country-analysis Barcelona`, `/tna-country-analysis 리스본`. 해당 도시만 심층 분석합니다.

### Q: 광고비 데이터가 해당 국가에 없으면?
`mkt_dashboard_raw_data`에 국가 필터가 없는 경우 T&A 전체 기준으로 분석하되, 스페인 한정이 아님을 보고서에 명시합니다.

### Q: 보고서가 자동 발행되는 Confluence 위치는?
실행한 사용자의 개인 스페이스에 발행됩니다.

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2026-04-02 | 최초 생성. 스페인 T&A 분석 사례 기반으로 스킬화. |
