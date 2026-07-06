---
name: tna-country-analysis
description: 특정 국가의 T&A 공헌이익을 퍼널 6단계(UV→CVR→주문→AOV→CFR→마진율)로 진단하고, 도시→카테고리→상품 레벨로 드릴다운하여 문제를 특정하고 해결 방향을 도출하는 종합 분석 skill. "스페인 T&A 분석해줘", "일본 T&A 공헌이익", "/tna-country-analysis 태국" 등에 사용.
---

# T&A 국가별 공헌이익 종합 분석

> 특정 국가의 T&A 공헌이익을 퍼널 6단계로 진단하고, 문제를 특정하여 해결 방향을 도출한다.

## 핵심 원칙

> **모든 분석은 도시 레벨로 수행한다.** 국가 전체 합산으로 분석하지 않는다. 국가 입력은 "해당 국가의 Top 5 도시를 자동 식별"하기 위한 편의 기능일 뿐이다.

## 손익 집계 기준 (2026-06 개편 반영)

> 2026-06-23 배포로 비항공 손익 집계 기준이 바뀌었다. 출처: [FP&A 비항공 손익 집계 기준 변경 안내 (2026-06)](https://myrealtrip.atlassian.net/wiki/spaces/NBDDIV/pages/5935038476). 이 스킬의 모든 손익 수치는 아래 기준을 따른다.

### 1) 기준 테이블·컬럼

- 기준 테이블은 그대로 `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D` (일 단위)를 **월별로 집계**한다.
- 컬럼명 변경: **`CON_MARGIN` → `CM`**, **`NET_PRICE` → `COGS`**.
- 환불 전용 컬럼 신설: **`REFUND_DATE`, `REFUND_GMV`, `REFUND_CM`, `REFUND_COGS`, `REFUND_REVENUE`**.
- 귀속일: 결제(확정) 측은 **`CONFIRM_KST_DATE`**, 환불 측은 **`REFUND_DATE`**.

### 2) 관점(lens)을 먼저 정한다 — 두 기준은 답이 다르다

| 관점 | 무엇을 묻나 | 환불 귀속 | 이 스킬에서 |
|------|------------|----------|------------|
| **월별 FP&A 실적** | 그 달에 결제·환불이 얼마 발생했나 | 환불을 **발생월**에 반영 | Phase 1 도시 월별 추세·성적표, Phase 3-4 동기비교 |
| **예약/상품/프로모션 최종성과** | 이 예약/상품/쿠폰이 **최종** 얼마 남겼나 | 환불을 **원 예약**에 다시 붙임 | Phase 2 GID·쿠폰·상품·AOV 드릴다운 |

> `CM`과 `REFUND_CM`을 모든 상황에서 하나의 공식처럼 쓰면 안 된다. **단위(월 vs 예약/상품/프로모션)를 먼저 정하고** 아래 패턴 (A)/(B)를 고른다. 예약 A(5월 결제·6월 환불)는 월별 실적에서는 5월 결제·6월 환불로 쪼개져 보이고, 최종성과에서는 환불을 5월 예약에 붙여 본다.

### 3) 캐노니컬 집계 패턴

**(A) 월별 FP&A 실적** — 확정월 + 환불월 분리 귀속:
```sql
WITH confirm_side AS (
  SELECT FORMAT_DATE('%Y-%m', CONFIRM_KST_DATE) AS month, CITY_NM,
    COUNT(DISTINCT ORDER_ID) AS order_cnt, SUM(GMV) AS gmv, SUM(CM) AS cm
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE FPNA_DOMAIN_NM='TNA' AND COUNTRY_NM='{COUNTRY}'
    AND CONFIRM_KST_DATE IS NOT NULL
    AND CONFIRM_KST_DATE BETWEEN '{START}' AND '{END}'
  GROUP BY 1, 2
),
refund_side AS (
  SELECT FORMAT_DATE('%Y-%m', REFUND_DATE) AS month, CITY_NM,
    SUM(REFUND_GMV) AS refund_gmv, SUM(REFUND_CM) AS refund_cm
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE FPNA_DOMAIN_NM='TNA' AND COUNTRY_NM='{COUNTRY}'
    AND REFUND_DATE IS NOT NULL
    AND REFUND_DATE BETWEEN '{START}' AND '{END}'
  GROUP BY 1, 2
)
SELECT c.month, c.CITY_NM, c.order_cnt,
  c.gmv - IFNULL(r.refund_gmv,0) AS cgmv,   -- 월 CGMV = 확정월 GMV − 환불월 REFUND_GMV
  c.cm  - IFNULL(r.refund_cm,0)  AS cm,      -- 월 CM   = 확정월 CM  − 환불월 REFUND_CM
  SAFE_DIVIDE(c.cm - IFNULL(r.refund_cm,0), c.gmv - IFNULL(r.refund_gmv,0)) AS cmr
FROM confirm_side c LEFT JOIN refund_side r USING (month, CITY_NM)
ORDER BY c.CITY_NM, c.month
```

**(B) 예약/상품/프로모션 최종성과** — 환불을 원 행(예약)에 붙여 net:
```sql
SELECT CITY_NM, GID, PRODUCT_COUPON_ID,
  COUNT(DISTINCT ORDER_ID) AS order_cnt,
  SUM(GMV - IFNULL(REFUND_GMV,0)) AS net_gmv,   -- 환불 차감 후 최종 GMV
  SUM(CM  - IFNULL(REFUND_CM,0))  AS net_cm,     -- 환불 차감 후 최종 CM
  SAFE_DIVIDE(SUM(CM - IFNULL(REFUND_CM,0)), SUM(GMV - IFNULL(REFUND_GMV,0))) AS net_cmr
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE FPNA_DOMAIN_NM='TNA' AND COUNTRY_NM='{COUNTRY}' AND CITY_NM='{TARGET_CITY}'
  AND CONFIRM_KST_DATE BETWEEN '{START}' AND '{END}'
GROUP BY 1, 2, 3
```

> **부호 (검증 완료, 2026-06-30)**: `REFUND_GMV`/`REFUND_CM`은 **양수로 저장**되는 차감액이다. 따라서 월/예약 net은 `GMV - REFUND_GMV`, `CM - REFUND_CM`로 **뺀다**. (dataagent 재산출 결과 lisbon GMV 611,900,980 − REFUND_GMV 123,816,661 = CGMV 488,084,319로 확인.) CPD는 `REFUND_CPD_AMOUNT` 컬럼이 없어 환불 차감이 안 되므로 `CPD_AMOUNT` 그대로 보되 환불쿠폰 영향은 근사치임에 주의.

### 4) 주의

- **`RECENT_STATUS IN ('confirm','finish')` + `BASIS_DATE`로 확정 GMV를 잡던 개편 전 방식은 폐기**한다. 아래 Phase 쿼리에 남아 있던 이 표현은 모두 (A)/(B)로 대체되었다. 새로 쿼리를 쓸 때도 이 방식을 쓰지 않는다.
- **T&A 외부정산**(connected/external) 매출·CM은 invoice·수수료율 기준 우선 반영으로 **숫자가 달라질 수 있다.** 기존 시트와 차이가 곧 오류는 아니며, 의도된 기준 변경 구간인지 확인한다.
- 전날/최근일은 정산 데이터 미도착으로 예약기준 금액으로 먼저 보이고 이후 정산기준으로 재반영될 수 있다. 결론은 완료월 중심.
- 로컬 dbt 레포의 `MART_FPNA_NONAIR_PROFIT_D` 모델은 배포(6/23)보다 이전 상태(`CON_MARGIN`/`NET_PRICE`)일 수 있다. **신규 컬럼 존재는 dataagent 또는 dev table `mrtdata.edw_fpna_dev.MART_FPNA_NONAIR_PROFIT_D`로 확인**한 뒤 본 쿼리를 돌린다.

## 사용법

```
# 국가 단위 입력 → 해당 국가 Top 5 도시를 자동 식별하여 도시별 분석
/tna-country-analysis 스페인
/tna-country-analysis Japan

# 도시 단위 입력 → 해당 도시만 분석
/tna-country-analysis Barcelona
/tna-country-analysis 리스본
```

## 입력 파라미터

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| 국가명 또는 도시명 | 필수 | 한글 또는 영문. 국가 입력 시 Top 5 도시 자동 식별. 도시 입력 시 해당 도시만 분석. |

### 입력 판별 로직

1. 한글 → 영문 매핑 테이블에서 먼저 국가명 매칭 시도
2. 국가명에 없으면 → BigQuery에서 `CITY_NM` 매칭 시도
3. 둘 다 없으면 → `COUNTRY_NM`, `CITY_NM` 양쪽에서 LIKE 검색

### 한글 → 영문 매핑 (주요 국가)

| 한글 | COUNTRY_NM |
|------|-----------|
| 스페인 | Spain |
| 일본 | Japan |
| 태국 | Thailand |
| 베트남 | Viet Nam |
| 프랑스 | France |
| 이탈리아 | Italy |
| 영국 | United Kingdom |
| 미국 | United States |
| 호주 | Australia |
| 대만 | Taiwan |
| 싱가포르 | Singapore |
| 홍콩 | Hong Kong |
| 터키 | Turkey |
| 크로아티아 | Croatia |
| 포르투갈 | Portugal |
| 그리스 | Greece |
| 체코 | Czech Republic |
| 헝가리 | Hungary |
| 모로코 | Morocco |
| 인도네시아 | Indonesia |

### 주요 도시 한글 → 영문 매핑

| 한글 | CITY_NM | | 한글 | CITY_NM |
|------|--------|-|------|--------|
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

위 목록에 없는 국가/도시는 BigQuery에서 값을 직접 확인한다:
```sql
SELECT DISTINCT COUNTRY_NM FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE FPNA_DOMAIN_NM = 'TNA' AND LOWER(COUNTRY_NM) LIKE '%입력값%'
LIMIT 10
```

---

## 분석 프레임워크

### 고객 퍼널 (3단계) + 부가 분석 지표

고객이 실제로 거치는 퍼널은 3단계이고, 각 단계에서 공헌이익에 영향을 주는 부가 지표를 함께 분석한다.

```
① 유입(상품 상세 UV)  →  ② 전환(CVR)  →  ③ 확정(CFR)  →  공헌이익
```

**퍼널 3단계:**

| 퍼널 단계 | 지표 | 정의 | 데이터 소스 |
|----------|------|------|-----------|
| **① 유입** | 상품 상세페이지 UV (PID 기준) | 해당 도시 T&A 상품을 본 유저 수 | `MART_BIZ_LOG_PID_CONVERSION_D` + `MART_PRODUCT_D` |
| **② 전환** | CVR = 주문건수 / UV | 본 사람 중 주문한 비율 | ①과 FP&A 조합 |
| **③ 확정** | CFR = CGMV / GMV | 확정거래액 비중 | `MART_FPNA_NONAIR_PROFIT_D` |

**각 단계의 부가 분석 지표:**

**각 단계의 핵심 분석 → 딥다이브 순서:**

| 퍼널 단계 | 핵심 분석 (먼저) | 딥다이브 (이후) |
|----------|----------------|---------------|
| ① 유입 | 채널별 UV + 광고비/ROAS → 투자부족 vs 효율악화 진단 | 채널별 UV 추이, Paid vs Organic 비중 |
| ② 전환 | **체크아웃 퍼널 이탈** (상세→체크아웃→결제 어디서 빠지는가?) | 카테고리별/채널별 CVR 분해, 주문건수, 객단가(AOV) |
| ③ 확정 | **취소 시점/사유 패턴** (언제, 왜 취소하는가?) | 마진율(CM/CGMV), 쿠폰(CPD) ROI, 파트너별 취소율 |

> **분석 순서가 중요하다.** 전환 단계에서는 "어디서 빠지는가(체크아웃 퍼널)"를 먼저 보고, 그 원인을 파악한 뒤에 주문건수/객단가 등 딥다이브 지표로 들어간다.

### 드릴다운 구조 (3단계)

```
Level 1: 도시 (CITY_NM)            ← Phase 1
  └─ Level 2: 카테고리 (CATEGORY_NM) ← Phase 2
       └─ Level 3: 개별 상품 (GID)    ← Phase 2
```

### 시간축

- 비교 기준은 **Phase 0.5에서 사용자와 먼저 확정**한다 (YoY 단독 고정 금지). 기본 후보는 YoY(전년 동월)·MoM(직전월)·직전 피크 대비·마진율(CMR) 추세. 공헌이익이 YoY로는 늘었는데 마진율만 빠지는 케이스가 흔하므로, 한 축만 보면 "감소"를 놓친다.
- **구조 브레이크 → MoM×YoY 삼각검증 (필수)**: 어떤 지표가 YoY로 크게 빠졌으면 "이번 기간 실패"인지 "과거에 한 번 내려앉아 안착한 레벨"인지부터 구분한다. **먼저 월별 시계열(12~18개월)로 레벨이 언제 바뀌었는지** 본다. 구조 브레이크가 있으면 **YoY는 그 이동을 포함**(작년=변화 前), **MoM은 상쇄**(둘 다 변화 後)해 *지금도 악화 중인지*를 드러낸다(계절성은 반대로 MoM 오염·YoY 제거). MoM flat이면 "안착(신규 악화 아님)", MoM도 하락이면 "진행 중". YoY만 보고 이번 기간 미달로 귀속하면 오독이다.
- 시즌은 **도시별 예약인원(`SUM(RESVE_PRSNL_CNT)`)** 기준으로 독립 분류 (월평균 ± 0.5σ). 1명이 동행 N명분을 결제하므로 주문수는 수요를 과소집계 → **계절성·수요 크기는 인원**을 쓴다(단 CVR·AOV·CM 분해 등 거래 기반 지표는 **주문수 유지**, 혼용 금지). 인원 이상치(예: >50 또는 인당 GMV 불가값)는 오류로 제외.
  - **남부유럽(Europe-south: 스페인·포르투갈·터키·그리스·UAE·이집트 등)은 사전 산출된 `/Users/doyoung-lee/Documents/my-project/seasonality.md`(단일 정본, 인원 기준, as-of 명시)를 조회해 재계산 없이 사용** — 프로모션 오염월 제외·여행월 교차검증·리드타임 반영됨. (파일 없으면 연 1회 재산출.)
- 분석 기간: 최근 24개월 (오늘 기준 2년). 단, 사용자가 특정 기간을 지정하면 그 기간을 우선한다.

### 유입 경로 분석 (추가 차원)

퍼널 ①②에 **유입 채널(UTM source)** 차원을 추가하여 채널별 유입량과 전환 품질을 분석한다.

---

## 실행 절차

### Phase 0: 사전 준비

1. **국가명 매핑**: 한글 입력이면 위 매핑 테이블로 `COUNTRY_NM` 확정
2. **오늘 날짜 확인**: `date -u -v+9H +%Y-%m-%d` (KST 기준). 배치 데이터에서 오늘 제외.
3. **분석 기간 설정**: `ANALYSIS_END = 오늘 - 1일의 월 마지막 날`, `ANALYSIS_START = ANALYSIS_END - 24개월`
4. **데이터 존재 확인**: 해당 국가에 T&A 데이터가 충분한지 빠르게 확인

```sql
SELECT COUNT(DISTINCT ORDER_ID) AS total_orders, MIN(BASIS_DATE) AS min_date, MAX(BASIS_DATE) AS max_date
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA'
  AND BASIS_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 24 MONTH)
```

5. **Top 5 도시 식별**: GMV 기준 상위 5개 도시 자동 선정

```sql
SELECT CITY_NM, SUM(GMV) AS total_gmv, COUNT(DISTINCT ORDER_ID) AS total_orders
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA'
  AND BASIS_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY 1 ORDER BY 2 DESC LIMIT 5
```

---

### Phase 0.5: 분석 전 얼라인 (비교기준·배경) — 필수

본 분석에 들어가기 전에 **결과를 바꾸는 축을 사용자와 먼저 맞춘다.** 공헌이익은 YoY로는 늘었는데 마진율(CMR)만 빠지는 식으로 "감소"의 정의에 따라 결론이 정반대가 되기 때문이다. Phase 0에서 데이터 존재·Top 5 도시·최근 추이를 빠르게 확인한 뒤, 아래를 1회 정렬한다.

| 맞출 축 | 후보 | 비고 |
|--------|------|------|
| **비교 기준** | YoY(전년 동월) / MoM(직전월) / 직전 피크 대비 / 마진율(CMR) 추세 | YoY 단독으로 고정하지 않는다. 여러 축을 동시에 보겠다고 해도 됨 |
| **분석 기간** | 최근 24개월(기본) / 특정 기간 지정 | 미완료 당월은 MTD/부분월로 표시하고 결론은 완료월 중심 |
| **배경/의도** | 수익성 방어·개선 액션 / 이상 징후 점검 / 리포트용 | 원인 분석이라 배경에 따라 보는 각도가 달라짐 |
| **집계 관점(lens)** | 월별 FP&A 실적(발생월 귀속) / 예약·상품·프로모션 최종성과(환불 원예약 귀속) | §손익 집계 기준 참고. 기본: Phase 1·3-4 = 월별 실적, Phase 2 = 최종성과. FP&A 공식 실적과 맞춰야 하면 월별 실적 기준 |

- Phase 0에서 최근 12~18개월 월별 CM·CMR·주문수 추이를 먼저 뽑아 **"실제로 어디서, 어떤 기준으로 빠졌는지"를 근거로 제시**한 뒤 위 축을 묻는다. 빈손으로 묻지 않는다.
- 사용자가 `알아서 해줘`면 가장 보수적인 기준(YoY + MoM 병행, CMR 추세 포함)으로 진행하고 응답 상단에 사용한 기준을 명시한다.
- 범위는 이 스킬 기준 T&A 고정. 리셀마켓·B2B·마이팩(PKG)·패키지(PKC) 포함 여부가 결과를 바꾸면 그때만 추가로 확인한다.

---

### Phase 1: 현황 진단 (L1 도시 레벨)

**3개 분석을 병렬 실행한다.**

#### 1-1. 시즌 패턴 정의 (도시별)

> **남부유럽(Europe-south)이면 재계산하지 말고 `/Users/doyoung-lee/Documents/my-project/seasonality.md`(인원 기준, as-of) 조회로 대체.** 그 외 국가만 아래로 산출.

각 도시별로 독립적으로 (지표 = **예약인원 `SUM(RESVE_PRSNL_CNT)`**, 수요 크기의 정확한 단위):
1. 같은 월끼리 2개년 평균 **인원** 산출
2. 해당 도시의 12개월 평균(μ)과 표준편차(σ) 계산
3. 분류: 성수기(μ+0.5σ 이상), 비수기(μ-0.5σ 이하), 준성수기(나머지)

```sql
SELECT CITY_NM, FORMAT_DATE('%Y-%m', CONFIRM_KST_DATE) AS month,
  SUM(RESVE_PRSNL_CNT) AS pax          -- 수요 크기 = 인원(주문수는 동행분 과소집계)
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA'
  AND CITY_NM IN ({TOP_5_CITIES})
  AND CONFIRM_KST_DATE IS NOT NULL
  AND CONFIRM_KST_DATE BETWEEN '{START}' AND '{END}'
  AND RESVE_PRSNL_CNT <= 50            -- 인원 입력오류(예: 88000) 제외
GROUP BY 1, 2 ORDER BY 1, 2
```

#### 1-2. 퍼널 6단계 도시별 YoY

**주문/GMV/CGMV/CMR** (③~⑥) — 월별 FP&A 실적 기준이므로 §손익 집계 기준 **패턴 (A)** 를 도시 × period로 적용:
```sql
WITH confirm_side AS (
  SELECT CITY_NM,
    CASE WHEN CONFIRM_KST_DATE BETWEEN '{CURRENT_START}' AND '{CURRENT_END}' THEN 'current'
         WHEN CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}' THEN 'prior' END AS period,
    COUNT(DISTINCT ORDER_ID) AS order_cnt, SUM(GMV) AS gmv, SUM(CM) AS cm, SUM(CPD_AMOUNT) AS cpd
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM IN ({TOP_5_CITIES})
    AND CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
  GROUP BY 1, 2
),
refund_side AS (
  SELECT CITY_NM,
    CASE WHEN REFUND_DATE BETWEEN '{CURRENT_START}' AND '{CURRENT_END}' THEN 'current'
         WHEN REFUND_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}' THEN 'prior' END AS period,
    SUM(REFUND_GMV) AS refund_gmv, SUM(REFUND_CM) AS refund_cm
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM IN ({TOP_5_CITIES})
    AND REFUND_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
  GROUP BY 1, 2
)
SELECT c.CITY_NM, c.period, c.order_cnt,
  SAFE_DIVIDE(c.gmv, c.order_cnt) AS aov,
  c.gmv - IFNULL(r.refund_gmv,0) AS cgmv,
  c.cm  - IFNULL(r.refund_cm,0)  AS cm,
  SAFE_DIVIDE(c.cm - IFNULL(r.refund_cm,0), c.gmv - IFNULL(r.refund_gmv,0)) AS cmr,
  c.cpd AS cpd
FROM confirm_side c LEFT JOIN refund_side r USING (CITY_NM, period)
WHERE c.period IS NOT NULL ORDER BY cgmv DESC
```
> CFR(확정률 = 확정 GMV/총 GMV)는 예약 코호트 개념이므로 필요 시 패턴 (B)의 net 기준 또는 별도 코호트 쿼리로 본다. 월별 실적에서는 CGMV·CM·CMR을 위 (A)로 본다.

**UV/CVR** (①②):
```sql
SELECT p.CITY_NM,
  CASE WHEN c.BASIS_DATE BETWEEN '{CURRENT_START}' AND '{CURRENT_END}' THEN 'current'
       WHEN c.BASIS_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}' THEN 'prior' END AS period,
  COUNT(DISTINCT c.PID) AS uv_pid,
  SUM(c.CHECKOUT_COMPLETE_FLAG) AS purchases
FROM mrtdata.edw_mart.MART_BIZ_LOG_PID_CONVERSION_D c
JOIN mrtdata.edw_mart.MART_PRODUCT_D p ON c.ITEM_ID = p.GID
WHERE c.OFFER_DETAIL_FLAG = 1
  AND p.COUNTRY_NM = '{COUNTRY}'
  AND p.STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
  AND p.CITY_NM IN ({TOP_5_CITIES})
  AND c.BASIS_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
GROUP BY 1, 2 ORDER BY uv_pid DESC
```

> **주의**: BIZ_LOG는 대용량. 24개월 풀스캔이 너무 크면 12개월씩 나눠서 실행.

#### 1-3. 도시별 YoY 성적표

**도시별로** 주문건수, GMV, CGMV, 공헌이익, CPD, 채널수수료 YoY 비교. 국가 전체 합산은 참고용으로만 부기하고, 주 분석 단위는 도시.

#### 1-4. 공헌이익(CM) 드라이버 분해 — 필수

지표를 나열만 하지 않고, **CM 변화가 어느 드라이버에서 나왔는지 정량 분해**한다. 곱셈 분해식:

```
CM = 주문수 × AOV(객단가) × 잔존율(net_retention) × CMR(마진율)
  ※ AOV = 확정월 GMV / 주문수
  ※ 잔존율 = CGMV / 확정월 GMV  (= (확정GMV − 환불월 REFUND_GMV) / 확정GMV — 개편 전 CFR 역할)
  ※ CMR = 월 CM / CGMV,  CGMV = 확정월 GMV − 환불월 REFUND_GMV (REFUND_*는 양수 차감)
  ※ 위 4개를 곱하면 월 CM(net)으로 환원됨
```

로그 분해로 각 드라이버의 기여도를 %p 단위로 산출한다 (`Δlog(CM) = Δlog(주문) + Δlog(AOV) + Δlog(CFR) + Δlog(CMR)`). Phase 0.5에서 정한 비교 기준(MoM·YoY)별로 각각 분해한다.

```sql
-- 드라이버 분해용 월별 집계 (월별 FP&A 실적 기준 = 패턴 (A))
WITH confirm_side AS (
  SELECT FORMAT_DATE('%Y-%m', CONFIRM_KST_DATE) AS month,
    COUNT(DISTINCT ORDER_ID) AS order_cnt, SUM(GMV) AS gmv, SUM(CM) AS cm
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM = '{TARGET_CITY}'
    AND STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
    AND CONFIRM_KST_DATE BETWEEN '{START}' AND '{END}'
  GROUP BY 1
),
refund_side AS (
  SELECT FORMAT_DATE('%Y-%m', REFUND_DATE) AS month,
    SUM(REFUND_GMV) AS refund_gmv, SUM(REFUND_CM) AS refund_cm
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM = '{TARGET_CITY}'
    AND STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
    AND REFUND_DATE BETWEEN '{START}' AND '{END}'
  GROUP BY 1
)
SELECT c.month, c.order_cnt,
  SAFE_DIVIDE(c.gmv, c.order_cnt) AS aov,                              -- 확정월 단가
  SAFE_DIVIDE(c.gmv - IFNULL(r.refund_gmv,0), c.gmv) AS net_retention, -- 환불 차감 후 잔존율 (구 CFR 역할)
  SAFE_DIVIDE(c.cm - IFNULL(r.refund_cm,0), c.gmv - IFNULL(r.refund_gmv,0)) AS cmr,
  c.cm - IFNULL(r.refund_cm,0) AS cm                                   -- 월 CM (net)
FROM confirm_side c LEFT JOIN refund_side r USING (month)
ORDER BY c.month
```

- 산출물은 "월 × 드라이버(주문/AOV/CFR/CMR) 기여도 %p" 표. 어느 드라이버가 CM 변화를 주도/상쇄했는지 한 줄 진단.
- **자주 나오는 패턴**: AOV 상승이 CMR·주문 하락을 덮어 CM은 YoY 유지 → 겉으로는 멀쩡해 보여도 수익성 펀더멘털이 약해지는 신호. 이 경우 Phase 2에서 CMR(쿠폰)·AOV(단가/믹스)·CVR을 우선 드릴다운한다.

#### Phase 1 산출물

- 도시별 시즌 비교표 (월 × 도시 매트릭스)
- **퍼널 6단계 도시별 종합 표** (Phase 0.5에서 정한 비교 기준으로, 도시별 독립 진단이 핵심)
- **CM 드라이버 기여도 분해 표** (주문/AOV/CFR/CMR %p) + 한 줄 진단
- 도시별 한 줄 진단 (UV↑/CVR↓ 등)
- 문제 신호 목록 (심각도 + **도시** + 상세)

---

### Phase 2: 문제별 드릴다운 (L2 카테고리 + L3 상품)

Phase 1에서 식별된 문제 신호를 기반으로, **문제가 있는 도시만** L2/L3으로 드릴다운한다.

#### 드릴다운 대상 (Phase 1 결과에 따라 동적 결정)

| 신호 | 드릴다운 |
|------|---------|
| CVR 하락 도시 | 해당 도시의 카테고리별 UV/CVR + UTM별 CVR + 체크아웃 퍼널 단계 이탈(상세→체크아웃→결제) |
| 주문 역성장 도시 | 카테고리별 주문건수 YoY + UV vs CVR 분해 |
| CFR 하락 도시 | 카테고리별 CFR + 성수기 vs 비수기 + 취소 TOP 상품(L3) |
| **CMR(마진율) 하락 도시** | 카테고리(LV2)별 CMR + CPD/CGMV 비중 → **GID·쿠폰ID 레벨 쿠폰 누수 추적** (아래 템플릿) |
| CPD 급증 | 도시 × 카테고리별 CPD YoY + 월별 추이 + GID·쿠폰ID 분해 |
| **AOV 급변 도시** | AOV shift-share 분해(단가효과 vs 믹스효과) + 단가 인상 Top GID + 가격저항 신호 (아래 템플릿) |

#### 핵심 쿼리 템플릿

**카테고리별 주문/최종성과/CPD** (예약·상품 최종성과 = 패턴 (B), 확정월 기준 period):
```sql
SELECT CITY_NM, CATEGORY_NM,
  CASE WHEN CONFIRM_KST_DATE BETWEEN '{CURRENT_START}' AND '{CURRENT_END}' THEN 'current'
       WHEN CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}' THEN 'prior' END AS period,
  COUNT(DISTINCT ORDER_ID) AS order_cnt,
  SUM(GMV - IFNULL(REFUND_GMV,0)) AS net_gmv,
  SUM(CM  - IFNULL(REFUND_CM,0))  AS net_cm,
  SAFE_DIVIDE(SUM(CM - IFNULL(REFUND_CM,0)), SUM(GMV - IFNULL(REFUND_GMV,0))) AS net_cmr,
  SUM(CPD_AMOUNT) AS cpd
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA'
  AND CITY_NM = '{TARGET_CITY}'
  AND CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
GROUP BY 1, 2, 3 ORDER BY net_gmv DESC
```

**UTM별 UV/CVR** (BIZ_LOG):
```sql
SELECT IFNULL(c.UTM_SOURCE, '(direct/none)') AS utm_source,
  CASE WHEN c.BASIS_DATE BETWEEN '{RECENT_CURRENT}' AND '{CURRENT_END}' THEN 'current'
       WHEN c.BASIS_DATE BETWEEN '{RECENT_PRIOR}' AND '{PRIOR_END_6M}' THEN 'prior' END AS period,
  COUNT(DISTINCT c.PID) AS uv, SUM(c.CHECKOUT_COMPLETE_FLAG) AS purchases,
  ROUND(SAFE_DIVIDE(SUM(c.CHECKOUT_COMPLETE_FLAG), COUNT(DISTINCT c.PID)) * 100, 2) AS cvr_pct
FROM mrtdata.edw_mart.MART_BIZ_LOG_PID_CONVERSION_D c
JOIN mrtdata.edw_mart.MART_PRODUCT_D p ON c.ITEM_ID = p.GID
WHERE c.OFFER_DETAIL_FLAG = 1 AND p.COUNTRY_NM = '{COUNTRY}' AND p.CITY_NM = '{TARGET_CITY}'
  AND p.STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
  AND c.BASIS_DATE BETWEEN '{RECENT_PRIOR}' AND '{CURRENT_END}'
GROUP BY 1, 2 HAVING uv >= 100 ORDER BY uv DESC
```

**취소(환불) TOP 상품 (L3)** — 확정월 기준 코호트에 환불을 붙여 본다(패턴 (B)):
```sql
SELECT CITY_NM, CATEGORY_NM, GID, PRODUCT_TITLE,
  COUNT(DISTINCT ORDER_ID) AS order_cnt, SUM(GMV) AS gmv,
  SUM(IFNULL(REFUND_GMV,0)) AS refund_gmv,                              -- 환불액(양수 표기)
  SAFE_DIVIDE(SUM(GMV - IFNULL(REFUND_GMV,0)), SUM(GMV)) AS net_retention -- 환불 차감 후 잔존율
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM = '{TARGET_CITY}'
  AND CONFIRM_KST_DATE BETWEEN '{PEAK_START}' AND '{PEAK_END}'
GROUP BY 1, 2, 3, 4 HAVING order_cnt >= 5 ORDER BY refund_gmv DESC LIMIT 20
```

**마진율(CMR) 하락 → GID·쿠폰ID 누수 추적** (CMR 하락 신호가 잡힌 도시·카테고리):
```sql
-- 1단계: LV2 카테고리별 CMR·CPD 비중으로 누수 카테고리 특정 (확정월 기준 net = 패턴 (B))
SELECT FORMAT_DATE('%Y-%m', CONFIRM_KST_DATE) AS month, STANDARD_CATEGORY_LV_2_CD AS lv2,
  ROUND(SUM(GMV - IFNULL(REFUND_GMV,0))/1e8, 3) AS net_cgmv_eok,
  ROUND(SAFE_DIVIDE(SUM(CM - IFNULL(REFUND_CM,0)), SUM(GMV - IFNULL(REFUND_GMV,0)))*100, 2) AS net_cmr_pct,
  ROUND(SAFE_DIVIDE(SUM(CPD_AMOUNT), SUM(GMV - IFNULL(REFUND_GMV,0)))*100, 2) AS cpd_ratio_pct
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM = '{TARGET_CITY}'
  AND STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
  AND CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
GROUP BY 1, 2 ORDER BY 2, 1;

-- 2단계: 누수 카테고리 안에서 GID별 CPD 누수 Top + 쿠폰ID/쿠폰명 분해
--         (PRODUCT_COUPON vs ORDER_COUPON, COUPON/DISCOUNT/POINT 구성까지)
SELECT GID, ANY_VALUE(PRODUCT_TITLE) AS product_title,
  PRODUCT_COUPON_ID, ANY_VALUE(PRODUCT_COUPON_TITLE) AS coupon_title,
  COUNT(DISTINCT ORDER_ID) AS order_cnt,
  ROUND(SUM(GMV - IFNULL(REFUND_GMV,0))/1e6, 2) AS net_cgmv_mil,
  ROUND(SUM(CM - IFNULL(REFUND_CM,0))/1e6, 2) AS net_cm_mil,
  ROUND(SAFE_DIVIDE(SUM(CM - IFNULL(REFUND_CM,0)), SUM(GMV - IFNULL(REFUND_GMV,0)))*100, 2) AS net_cmr_pct,
  ROUND(SUM(CPD_AMOUNT)/1e6, 2) AS cpd_mil,
  ROUND(SUM(COUPON_PRICE)/1e6, 2) AS coupon_mil,
  ROUND(SUM(DISCOUNT_PRICE)/1e6, 2) AS discount_mil
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM = '{TARGET_CITY}'
  AND STANDARD_CATEGORY_LV_2_CD = '{LEAK_CATEGORY}'
  AND CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
GROUP BY GID, PRODUCT_COUPON_ID ORDER BY cpd_mil DESC LIMIT 20
```

> 쿠폰이 단일 GID·단일 쿠폰ID에 집중되는지, 여러 GID에 깔린 도메인성 할인인지 본다. **누수가 "쿠폰 신설"인지 "수요 폭증 × 고정 할인율"인지 구분**한다(주문수 추이와 CPD/CGMV 비중 추이를 함께 본다). 쿠폰 발급/적용 정책의 의도성은 데이터로 단정하지 말고 쿠폰팀·T&A PM 확인 영역으로 안내한다(`source-logic-boundary.md`).

**AOV shift-share 분해 (단가효과 vs 믹스효과)** (AOV 급변 신호):
```sql
-- LV2 카테고리 weight × AOV로 분해: ΔAOV = 단가효과 + 믹스효과 + 상호작용
WITH cat AS (
  SELECT
    CASE WHEN CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}' THEN 'prior' ELSE 'current' END AS period,
    STANDARD_CATEGORY_LV_2_CD AS lv2,
    COUNT(DISTINCT ORDER_ID) AS ord, SUM(GMV) AS gmv   -- AOV는 단가이므로 확정월 GMV(gross) 기준
  FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
  WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA' AND CITY_NM = '{TARGET_CITY}'
    AND STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
    AND CONFIRM_KST_DATE IS NOT NULL
    AND ((CONFIRM_KST_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}') OR (CONFIRM_KST_DATE BETWEEN '{CURRENT_START}' AND '{CURRENT_END}'))
  GROUP BY 1, 2
), p AS (
  SELECT lv2,
    SUM(IF(period='prior', ord,0)) AS ord_p, SUM(IF(period='current', ord,0)) AS ord_c,
    SAFE_DIVIDE(SUM(IF(period='prior', gmv,0)), NULLIF(SUM(IF(period='prior', ord,0)),0)) AS aov_p,
    SAFE_DIVIDE(SUM(IF(period='current', gmv,0)), NULLIF(SUM(IF(period='current', ord,0)),0)) AS aov_c
  FROM cat GROUP BY 1
)
SELECT lv2,
  ROUND(SAFE_DIVIDE(ord_p, SUM(ord_p) OVER())*100, 2) AS share_p_pct,
  ROUND(SAFE_DIVIDE(ord_c, SUM(ord_c) OVER())*100, 2) AS share_c_pct,
  ROUND(aov_p/1e4, 2) AS aov_p_manwon, ROUND(aov_c/1e4, 2) AS aov_c_manwon,
  ROUND(SAFE_DIVIDE(ord_p, SUM(ord_p) OVER()) * (aov_c-aov_p)/1e4, 3) AS price_effect_manwon,  -- 단가효과
  ROUND((SAFE_DIVIDE(ord_c, SUM(ord_c) OVER()) - SAFE_DIVIDE(ord_p, SUM(ord_p) OVER())) * aov_p/1e4, 3) AS mix_effect_manwon  -- 믹스효과
FROM p ORDER BY (ord_p + ord_c) DESC
```

> 단가효과가 지배적이면 가격 인상 주도 → CVR 하락·가격저항 리스크를 같이 본다(월별 AOV·1인당 단가 추이에서 둔화 시점, 주문수 반등 여부). `RESVE_PRSNL_CNT`로 1인당 단가(GMV/인원)와 주문당 인원수도 분리한다. 외부 요인(환율 등) 단정은 금지(`external-context-boundary.md`).

#### Phase 2 산출물

- 카테고리별 퍼널 지표 비교표
- UTM별 UV/CVR 변화표
- 체크아웃 퍼널 단계별 이탈표 (CVR 하락 신호 시)
- GID·쿠폰ID 누수 Top + 쿠폰 구성 분해 (CMR 하락 신호 시)
- AOV shift-share 분해표 + 단가 인상 Top GID (AOV 급변 신호 시)
- 취소 TOP 상품 목록 (L3)
- 문제 원인 특정 ("X 도시 CMR 하락의 Y%는 Z 카테고리의 W 상품/쿠폰에서 발생")

---

### Phase 3: 심층 분석

4개 심층 분석을 **병렬로** 실행한다.

#### 3-1. 광고비 × 유입 효율

> **중요: `mkt_dashboard_raw_data`의 `country_en` 값과 FP&A 테이블의 `COUNTRY_NM` 값이 다를 수 있다.** 반드시 아래 순서를 따른다.

**Step 1: 해당 국가의 `country_en` 값 확인**
```sql
SELECT DISTINCT country_en FROM mrtdata.business.mkt_dashboard_raw_data
WHERE biz_type = 'T&A' AND LOWER(country_en) LIKE LOWER('%{COUNTRY}%') LIMIT 5
```

**Step 2: country_en으로 결과가 없으면, city_en으로 fallback**
```sql
-- Phase 0에서 식별한 Top 5 도시명으로 검색
SELECT DISTINCT city_en FROM mrtdata.business.mkt_dashboard_raw_data
WHERE biz_type = 'T&A' AND (LOWER(city_en) LIKE '%{CITY_1}%' OR LOWER(city_en) LIKE '%{CITY_2}%' ...) LIMIT 20
```

**Step 3: 확인된 필터로 도시 × 채널별 광고비/GMV/ROAS 추출**

> **광고비 분석은 반드시 도시 레벨로 수행한다.** 국가 전체 합산은 도시별 차이를 가린다.

```sql
SELECT city_en, channel,
  CASE WHEN date BETWEEN '{Q1_PRIOR_START}' AND '{Q1_PRIOR_END}' THEN 'prior'
       WHEN date BETWEEN '{Q1_CURRENT_START}' AND '{Q1_CURRENT_END}' THEN 'current' END AS period,
  SUM(cost) AS cost, SUM(gmv) AS gmv, SUM(con_margin) AS con_margin,
  SAFE_DIVIDE(SUM(gmv), NULLIF(SUM(cost), 0)) AS roas
FROM mrtdata.business.mkt_dashboard_raw_data
WHERE biz_type = 'T&A'
  AND (country_en = '{CONFIRMED_COUNTRY_EN}' OR city_en IN ({CONFIRMED_CITY_ENS}))
  AND date BETWEEN '{Q1_PRIOR_START}' AND '{Q1_CURRENT_END}'
GROUP BY 1, 2, 3 HAVING SUM(cost) > 0 ORDER BY city_en, cost DESC
```

**Fallback 순서 요약**:
1. `country_en` 필터로 시도 (도시별 결과가 `city_en`에 포함됨)
2. country_en 결과 없으면 → `city_en` IN (Top 5 도시) 필터로 재시도
3. 둘 다 없으면 → "해당 국가의 광고비 데이터가 `mkt_dashboard_raw_data`에 없습니다. 마케팅팀에 데이터 적재를 요청하세요."로 안내. T&A 전체 기준 ROAS를 참고 수치로 제공.

> **주의**: `city_en` 값의 대소문자가 불규칙할 수 있다 (예: `lisbon` vs `Porto`). `LOWER()` 비교로 매칭하되, 결과 표시는 원본 값을 사용한다.

채널별 진단 프레임 적용:
```
             광고비 ↓              광고비 유지/↑
            ──────────           ─────────────────
UV ↓      → A. 투자 부족           B. 효율 악화
UV 유지    →  (해당 없음)          C. 전환 품질 문제
```

#### 3-2. 체크아웃 퍼널 이탈

```sql
-- 상세→체크아웃→결제 각 단계별 전환율
SELECT
  CASE WHEN c.BASIS_DATE BETWEEN '{CURRENT_START}' AND '{CURRENT_END}' THEN 'current'
       WHEN c.BASIS_DATE BETWEEN '{PRIOR_START}' AND '{PRIOR_END}' THEN 'prior' END AS period,
  COUNT(DISTINCT c.PID) AS detail_uv,
  SUM(c.CHECKOUT_FLAG) AS checkout_cnt,
  SUM(c.CHECKOUT_COMPLETE_FLAG) AS purchase_cnt,
  ROUND(SAFE_DIVIDE(SUM(c.CHECKOUT_FLAG), COUNT(DISTINCT c.PID)) * 100, 2) AS detail_to_checkout_pct,
  ROUND(SAFE_DIVIDE(SUM(c.CHECKOUT_COMPLETE_FLAG), NULLIF(SUM(c.CHECKOUT_FLAG), 0)) * 100, 2) AS checkout_to_purchase_pct
FROM mrtdata.edw_mart.MART_BIZ_LOG_PID_CONVERSION_D c
JOIN mrtdata.edw_mart.MART_PRODUCT_D p ON c.ITEM_ID = p.GID
WHERE c.OFFER_DETAIL_FLAG = 1 AND p.COUNTRY_NM = '{COUNTRY}' AND p.CITY_NM = '{TARGET_CITY}'
  AND p.STANDARD_CATEGORY_LV_1_CD IN ('TOUR','TICKET','ACTIVITY','CLASS','CONVENIENCE','SNAP')
  AND c.BASIS_DATE BETWEEN '{PRIOR_START}' AND '{CURRENT_END}'
GROUP BY 1 ORDER BY 1
```

"상세→체크아웃"이 문제인지 "체크아웃→결제"가 문제인지 특정.

#### 3-3. 취소 사유·시점 패턴

> **확정률(CFR)이 문제인 도시는 정본 스킬 `tna-confirmation-analysis`의 7-STEP(STEP0 관점고정 ~ STEP7 통제/upside)을 따른다.** 핵심: ①`CFR=CGMV/GMV`·취소월(`REFUND_DATE`) 앵커(여행월로 필터하지 말 것) ②구조 브레이크 탐지(월별 + 주차 WoW) + MoM×YoY 삼각검증 ③**rate effect vs mix effect 분리**(상품군 자체 악화 vs 믹스 변화) ④**실제 취소 사유는 `MART_OFFER_SALE_D.CANCEL_REASON`에서 읽는다**(FPNA엔 사유 텍스트 없음 → RESVE_ID 조인). 타이밍은 사유 컬럼이 없을 때만 보조.

**실제 취소 사유 읽기 (사유 컬럼, 추정 금지)** — FPNA(금액) × OFFER_SALE(사유) `RESVE_ID` 조인:
```sql
WITH o AS (   -- 일 스냅샷 → RESVE_ID별 최신 1행 dedup
  SELECT RESVE_ID, CANCEL_SUBJECT, CANCEL_REASON
  FROM mrtdata.edw_mart.MART_OFFER_SALE_D
  WHERE BASIS_DATE >= '{PEAK_START}' AND CANCEL_KST_DT BETWEEN '{PEAK_START}' AND '{PEAK_END}'
  QUALIFY ROW_NUMBER() OVER(PARTITION BY RESVE_ID ORDER BY BASIS_DATE DESC)=1 )
SELECT o.CANCEL_SUBJECT, o.CANCEL_REASON,          -- LACK_TRAVELER(최소모객,통제가능)/TRAVELER_PERSONAL_REASON(고객)/PARTNER_SCHEDULE 등
  COUNT(*) AS n, ROUND(SUM(f.REFUND_CM)/1e6,1) AS refund_cm_M
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D f
JOIN o ON f.RESVE_ID = o.RESVE_ID
WHERE f.COUNTRY_NM = '{COUNTRY}' AND f.FPNA_DOMAIN_NM = 'TNA'
  AND f.CITY_NM IN ({CFR_PROBLEM_CITIES})
  AND f.REFUND_DATE BETWEEN '{PEAK_START}' AND '{PEAK_END}'   -- 취소월 앵커
GROUP BY 1, 2 ORDER BY refund_cm_M DESC
```

**(보조) 취소 시점 = 여행일 근접도** — 사유 코드가 빈약할 때만. `DATE_DIFF(TRAVEL_START_DATE, REFUND_DATE, DAY)`가 출발 7일 이내에 몰리면 공급사/최소모객 취소 시그니처. (`RESVE_CANCEL_DAY_DIFF`는 예약↔취소 간격이라 사유 추정엔 약함.)

취소 주체(SUBJECT)×사유로 분류: **통제 가능**(LACK_TRAVELER·파트너 운영·상품/가격) vs **통제 난이**(고객 개인·외부). 전 카테고리(티켓 포함) 동반 급증이면 정책(무료취소·환불규정) 변화 의심 → CS·정책팀 확인.

#### 3-4. 쿠폰(CPD) ROI

```sql
-- 시즌 효과 제거를 위한 동기 비교 (H2 prior vs H2 current)
SELECT CITY_NM,
  CASE WHEN CONFIRM_KST_DATE BETWEEN '{H2_PRIOR_START}' AND '{H2_PRIOR_END}' THEN 'prior_h2'
       WHEN CONFIRM_KST_DATE BETWEEN '{H2_CURRENT_START}' AND '{H2_CURRENT_END}' THEN 'current_h2' END AS period,
  COUNT(DISTINCT ORDER_ID) AS order_cnt,
  SUM(GMV - IFNULL(REFUND_GMV,0)) AS net_gmv,
  SUM(CM - IFNULL(REFUND_CM,0)) AS net_cm, SUM(CPD_AMOUNT) AS cpd
FROM mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D
WHERE COUNTRY_NM = '{COUNTRY}' AND FPNA_DOMAIN_NM = 'TNA'
  AND CITY_NM IN ({TOP_5_CITIES})
  AND CONFIRM_KST_DATE BETWEEN '{H2_PRIOR_START}' AND '{H2_CURRENT_END}'
GROUP BY 1, 2 ORDER BY 1, 2
```

CPD 1원당 증분 GMV/CM 산출. 도시별 효율 비교.

#### Phase 3 산출물

- 채널별 광고비/ROAS YoY + 진단(A/B/C)
- 퍼널 단계별 이탈 포인트 특정
- 취소 타이밍 패턴 + TOP 상품 취소 패턴
- 쿠폰 한계효과 (도시별)
- 마케팅팀 제안 액션 아이템

---

### 보고서 발행 (선택 옵션)

기본 동작은 **터미널/채팅 결과로 응답**한다. 자동 발행은 하지 않는다. 사용자가 보고서를 요청하면 형식을 골라 발행한다.

- **Confluence**: "컨플루언스에 정리해줘", "문서로 발행해줘" → 아래 구조로 개인 스페이스에 발행. (Slack Data Agent 경로에서는 Confluence 쓰기 차단이므로 발행하지 않고 터미널/권한 환경 안내)
- **HTML / xlsx / markdown 보고서**: `report-write`로 위임 (`result-export-workflow.md`).
- 분석 완료 후 후속 옵션에 위 발행 선택지를 제시하고, 사용자가 고를 때만 생성한다.

**Confluence 제목 형식**: `[분석] {국가명/도시명} T&A 공헌이익 종합 분석 ({YYYY.MM})`

**보고서 구조**:
1. **한눈에 보는 결과** — 문제 4가지의 원인/수치/방향 1줄 요약표
2. **Phase 1 현황 진단** — 전체 YoY, 시즌 패턴, 퍼널 6단계 도시별 진단
3. **Phase 2 드릴다운** — 문제별 카테고리/상품 분해
4. **Phase 3 심층 분석** — 광고비 효율, 퍼널 이탈, 취소 패턴, 쿠폰 ROI
5. **종합 문제 구조도** — 전체 퍼널을 하나의 트리로 연결
6. **Next Step** — 전략 수립 방향

각 섹션 앞에 **"왜 이 분석이 필요한가?"**를 설명하고, 전문용어에는 괄호로 설명을 붙인다.

---

## 공통 규칙

- BQ wrapper: `./.claude/hooks/run-bq-readonly.sh bq query --use_legacy_sql=false --location=asia-northeast3 --format=prettyjson --max_rows=200 "쿼리"`
- 금액 단위: 1억 이상은 `억` 단위(소수 2자리), 1만 이상은 `만` 단위
- 비율: 소수 1자리 %
- 증감 표시: ▲(증가), ▼(감소)
- 비교 기준은 Phase 0.5에서 사용자와 확정한 축(YoY/MoM/직전피크/CMR 추세)을 따른다. YoY를 쓸 때는 시즌 효과 제거를 위해 동일 시즌끼리 비교한다. YoY 단독으로 "감소"를 단정하지 않는다(YoY는 늘었는데 마진율만 빠지는 케이스 주의).
- 배치 데이터에서 오늘 날짜 제외. 당일 데이터는 미적재/불완전.
- BIZ_LOG 대용량 주의: 필요시 기간 분할 실행.
- 손익 집계는 **§손익 집계 기준 (2026-06 개편)**을 따른다. 월별 실적은 확정월(`CONFIRM_KST_DATE`)+환불월(`REFUND_DATE`) 분리 귀속(패턴 A), 예약/상품/프로모션 성과는 환불을 원 행에 붙여 net(패턴 B). 컬럼은 `CM`(구 `CON_MARGIN`)·`COGS`(구 `NET_PRICE`)·`REFUND_*`. 개편 전 `RECENT_STATUS IN ('confirm','finish')` + `BASIS_DATE` 확정 집계는 쓰지 않는다.
- `analyst` subagent(opus)에 위임하여 병렬 실행. main agent는 오케스트레이션 + 검수 + 최종 응답.
- 사용자는 사업개발/전략팀. 마케팅팀은 별도 조직. 광고비/유입 관련 산출물은 "마케팅팀에 제안할 수 있는 형태"로 정리.

## NOT for

- 항공, 숙박, 보험 등 T&A 외 도메인 분석
- dbt 모델 개발/수정
- 실시간 모니터링 (배치 데이터 기반 분석)
