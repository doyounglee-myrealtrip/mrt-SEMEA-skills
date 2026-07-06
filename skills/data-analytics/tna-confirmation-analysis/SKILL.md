---
name: tna-confirmation-analysis
description: T&A 확정률(CFR=CGMV/GMV)/취소 문제를 진단하는 정본 스킬. 확정률이 빠졌을 때 "언제 구조가 바뀌었나(월별+주차 WoW 추세)→rate/mix 중 무엇인가→어느 지역·카테고리·상품이 범인인가→실제 취소 사유가 뭔가(사유 컬럼)→통제 가능/불가"를 순서대로 규명한다. "확정률 분석/진단", "취소 왜 늘었어", "CFR 하락 원인", "환불율 급증" 요청에 사용. tna-mbor-draft·tna-country-analysis가 확정률 이슈를 만나면 이 스킬 방법론을 참조한다.
---

# T&A 확정률(CFR)·취소 진단 (정본)

> 확정률(CFR)이 빠지거나 취소·환불이 급증했을 때, **원인을 데이터로 끝까지 규명**하는 방법론과 쿼리 템플릿. tna-mbor-draft(월간 회고)·tna-country-analysis(국가 진단)가 확정률 문제를 만나면 이 스킬을 참조한다.

## 이 스킬이 존재하는 이유 — 확정률 진단에서 반복된 실수 4가지
1. **여행월로 필터해서 봤다** → 보고 숫자와 안 맞는다. `CFR=CGMV/GMV`에서 **환불 차감은 취소월(REFUND_DATE) 기준**이라, 여행월로 필터하면 취소월이 다른 건이 빠져 어긋난다.
2. **취소 사유를 타이밍으로 "추정"했다** → 실제 **취소 사유 컬럼이 존재**한다(`MART_OFFER_SALE_D.CANCEL_REASON`). 추정 말고 읽어라.
3. **YoY만 보고 "이번 달 미달"로 귀속했다** → 과거에 구조가 한 단계 내려앉은 것을 이번 달 사건으로 오독. **월별 시계열 + MoM으로 교차검증** 필수.
4. **전 지역 골고루 얕게 봤다** → 범인은 소수 상품에 집중. 지역→카테고리→상품(GID)으로 좁혀라.

---

## 진단 순서 (반드시 이 순서)

### STEP 0 — 관점 고정: CFR = CGMV / GMV (net-event, 결제월/환불월 분리)
- **정의(정본)**: `CFR = CGMV / GMV`.
  - `GMV` = `Σ(GMV | CONFIRM_KST_DATE ∈ 대상기간)` — **확정월 결제분**(환불 차감 전). ← "총예약액"이 아니라 이걸 뜻함.
  - `CGMV` = `GMV − Σ(REFUND_GMV | REFUND_DATE ∈ 대상기간)` — 환불 차감 후 net.
  - 따라서 `CFR = CGMV/GMV = 1 − Σ환불GMV(취소월)/Σ확정GMV(확정월)` — **같은 지표의 두 표기**(둘 다 맞음).
- **결제 side는 `CONFIRM_KST_DATE`, 환불 side는 `REFUND_DATE`로 분리 귀속**한다. 6월 CFR = 6월 확정 GMV 대비 6월 환불 GMV 차감. 한 건이라도 확정월·취소월이 다르면 각 side가 다른 달로 들어간다.
- 그래서 **여행월(TRAVEL_START_DATE)로 필터하지 않는다** — {여행월 7월·예약월 5월·취소월 6월}인 건은 6월 CFR을 깎지만 여행월 필터에선 빠져 보고 숫자와 어긋난다. 여행월은 **원인 설명용 보조 변수**로만(예: "취소된 회차가 어느 출발월이었나").
- 정식 컬럼 정의·집계는 tna-mbor-draft `references/bigquery.md` §확정월+환불월 표준을 따른다(부호: `REFUND_GMV`/`REFUND_CM`은 **양수 저장 → 차감**).

### STEP 1 — 구조 브레이크 탐지 (월별 + 주차별) ⭐ 인풋1
YoY 갭이 크면 **먼저 "언제부터 이렇게 됐나"를 시계열로 본다.** 한 지점에서 레벨이 계단식으로 바뀌고 그 뒤로 유지되면 = **구조적 레벨 이동**(과거 사건)이지 이번 달 실패가 아니다.
- **월별(12~18개월)** = 구조 브레이크 시점·YoY 서사용. **주차별 WoW** = 변동 큰 주를 핀포인트하는 용(노이즈↑ 이므로 GMV 규모 큰 주 위주로 해석).

```sql
-- ① 월별 GMV·CGMV·CFR (확정=CONFIRM월, 환불차감=REFUND월) 12~18개월
WITH conf AS (
  SELECT DATE_TRUNC(CONFIRM_KST_DATE, MONTH) m, SUM(GMV) gmv
  FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D`
  WHERE {SCOPE} AND CONFIRM_KST_DATE >= '{START}' AND CONFIRM_KST_DATE < '{END}' GROUP BY 1),
ref AS (
  SELECT DATE_TRUNC(REFUND_DATE, MONTH) m, SUM(REFUND_GMV) rgmv
  FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D`
  WHERE {SCOPE} AND REFUND_DATE >= '{START}' AND REFUND_DATE < '{END}' GROUP BY 1)
SELECT FORMAT_DATE('%Y-%m', COALESCE(conf.m, ref.m)) month,
  ROUND(conf.gmv/1e6,1) gmv_M,
  ROUND((conf.gmv - IFNULL(ref.rgmv,0))/1e6,1) cgmv_M,
  ROUND((conf.gmv - IFNULL(ref.rgmv,0))/NULLIF(conf.gmv,0)*100,1) cfr_pct
FROM conf FULL OUTER JOIN ref USING(m) ORDER BY 1
```

```sql
-- ② 주차별 CFR + WoW (WEEK 월요일 시작): 변동 큰 주 특정. 당일(미완료 배치) 제외.
WITH conf AS (
  SELECT DATE_TRUNC(CONFIRM_KST_DATE, WEEK(MONDAY)) w, SUM(GMV) gmv
  FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D`
  WHERE {SCOPE} AND CONFIRM_KST_DATE >= '{START}' AND CONFIRM_KST_DATE < CURRENT_DATE() GROUP BY 1),
ref AS (
  SELECT DATE_TRUNC(REFUND_DATE, WEEK(MONDAY)) w, SUM(REFUND_GMV) rgmv
  FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D`
  WHERE {SCOPE} AND REFUND_DATE >= '{START}' AND REFUND_DATE < CURRENT_DATE() GROUP BY 1),
wk AS (SELECT COALESCE(conf.w,ref.w) w, conf.gmv, IFNULL(ref.rgmv,0) rgmv
  FROM conf FULL OUTER JOIN ref USING(w))
SELECT w week_start, ROUND(gmv/1e6,1) gmv_M, ROUND((gmv-rgmv)/1e6,1) cgmv_M,
  ROUND(SAFE_DIVIDE(gmv-rgmv,gmv)*100,1) cfr_pct,
  ROUND((SAFE_DIVIDE(gmv-rgmv,gmv) - LAG(SAFE_DIVIDE(gmv-rgmv,gmv)) OVER(ORDER BY w))*100,1) wow_cfr_pp
FROM wk ORDER BY w
```
- 카테고리별로도 같은 추세를 뽑아 **어느 카테고리가 그 시점에 함께 움직였는지** 본다. (예: 투어뿐 아니라 티켓도 같은 시점에 함께 빠지면 최소모객 같은 상품 특성이 아니라 정책·행동 등 포트폴리오 전반 요인.)

### STEP 2 — MoM × YoY 삼각검증 ⭐ 인풋1 (핵심 원칙)
구조 브레이크가 있으면 두 렌즈가 **서로 다른 것을 측정**한다:

| 렌즈 | 계절성 | 구조 브레이크 | 무엇을 답하나 |
|---|---|---|---|
| **YoY** | 제거됨 | **포함**(작년=변화 前, 올해=변화 後) | 브레이크의 크기 |
| **MoM** | 포함(오염) | **상쇄**(두 달 다 변화 後) | 지금도 움직이나 / 안착했나 |

- **규칙: YoY가 크게 빠진 지표는 반드시 MoM(+월별 시계열)로 교차 확인**한다. MoM이 flat이면 "옛날에 내려앉아 안착한 레벨"(신규 악화 아님) → 이번 달 미달로 귀속하면 오류. MoM도 빠지면 "진행 중 악화".
- 반대로 **MoM만 크게 빠졌는데 YoY는 견조**하면 계절 요인일 수 있다 → 계절 정본(seasonality.md)으로 확인. 지표마다 어느 렌즈가 무엇을 격리하는지 알고 써야 한다.
- **주차 WoW로 특정한 변동 주는 그 자체로 결론이 아니다** — 월별/YoY로 "구조 브레이크의 일부인지, 일시적 스파이크인지" 반드시 교차확인한다.

### STEP 3 — 드라이버 분해: 수요 vs 확정 vs 마진
미달이 확정률 문제인지부터 못박는다. `CM = GMV × CFR × CMR` (GMV=확정월 결제 GMV, CFR=CGMV/GMV, CMR=CM/CGMV).
- GMV(수요)·CFR(확정)·CMR(마진)을 각각 YoY/MoM(주차면 WoW)로 분해 → CM 변화가 어디서 왔는지 %·%p로 특정.
- 예: 수요 +4%·CMR +0.2%p인데 CM 미달 → 원인은 오직 CFR. "문제는 수요·가격이 아니라 확정 단계".

### STEP 4 — rate effect vs mix effect 분리 (전체 CFR 변화의 성격)
CFR 문제로 좁혀졌으면, 전체 CFR 변화가 **① 카테고리 자체 확정률이 나빠진 것(rate)** 인지 **② 저확정률 카테고리 비중이 커진 것(mix)** 인지 가른다. 둘은 처방이 완전히 다르다(rate→해당 상품군 취소·공급 문제, mix→판매·노출 믹스 문제).
- 전체 `CFR = Σ_c (share_c × CFR_c)`, `share_c = GMV_c / GMV_total`. 두 시점(cur vs base = 직전 주/월 또는 전년)으로 분해:
  - **rate**: `Σ_c share_c^base × (CFR_c^cur − CFR_c^base)` — 비중 고정, 확정률만 변화
  - **mix**: `Σ_c (share_c^cur − share_c^base) × CFR_c^base` — 확정률 고정, 비중만 변화
  - (잔차 = 상호작용항. rate + mix + 잔차 ≈ 전체 ΔCFR.)

```sql
-- 카테고리별 rate/mix 기여 (cur vs base 두 창). {CAT}=dashboard_category 우선(STEP5 참조)
WITH b AS (
  SELECT {CAT} cat, GMV, REFUND_GMV,
    (CONFIRM_KST_DATE>='{CUR_S}'  AND CONFIRM_KST_DATE<'{CUR_E}')  c_cur,
    (REFUND_DATE     >='{CUR_S}'  AND REFUND_DATE     <'{CUR_E}')  r_cur,
    (CONFIRM_KST_DATE>='{BASE_S}' AND CONFIRM_KST_DATE<'{BASE_E}') c_base,
    (REFUND_DATE     >='{BASE_S}' AND REFUND_DATE     <'{BASE_E}') r_base
  FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D`
  WHERE {SCOPE} AND ((CONFIRM_KST_DATE>='{BASE_S}' AND CONFIRM_KST_DATE<'{CUR_E}')
                  OR (REFUND_DATE    >='{BASE_S}' AND REFUND_DATE    <'{CUR_E}'))),
cat AS (
  SELECT cat,
    SUM(IF(c_cur,GMV,0))  g_cur,  SUM(IF(c_cur,GMV,0)) -SUM(IF(r_cur,REFUND_GMV,0))  cg_cur,
    SUM(IF(c_base,GMV,0)) g_base, SUM(IF(c_base,GMV,0))-SUM(IF(r_base,REFUND_GMV,0)) cg_base
  FROM b GROUP BY 1),
t AS (SELECT SUM(g_cur) tot_cur, SUM(g_base) tot_base FROM cat)  -- ⚠️ BQ 컬럼명 대소문자 무시 → 총합은 g_*와 다른 이름(tot_*)으로
SELECT cat.cat,
  ROUND(SAFE_DIVIDE(cg_base,g_base)*100,1) cfr_base_pct,
  ROUND(SAFE_DIVIDE(cg_cur ,g_cur )*100,1) cfr_cur_pct,
  ROUND(SAFE_DIVIDE(g_base,t.tot_base)*100,1) share_base_pct,
  ROUND(SAFE_DIVIDE(g_cur ,t.tot_cur )*100,1) share_cur_pct,
  ROUND(SAFE_DIVIDE(g_base,t.tot_base)*(SAFE_DIVIDE(cg_cur,g_cur)-SAFE_DIVIDE(cg_base,g_base))*100,2) rate_pp,
  ROUND((SAFE_DIVIDE(g_cur,t.tot_cur)-SAFE_DIVIDE(g_base,t.tot_base))*SAFE_DIVIDE(cg_base,g_base)*100,2) mix_pp
FROM cat, t ORDER BY ABS(rate_pp)+ABS(mix_pp) DESC
```
- **rate 지배** → STEP 5~6(어느 상품군이·왜 취소됐나)로. **mix 지배** → 판매·노출 믹스 변화가 원인(상품군 자체 확정률은 그대로) → 믹스를 만든 채널·프로모션·상품구성 확인.

### STEP 5 — 범인 좁히기: 지역 → 카테고리 → 상품(GID)
취소월 기준으로 환불 CM/GMV YoY가 큰 셀을 찾는다. (전 지역 골고루 X, 집중 셀 선별 O.)
```sql
-- 도시 × 카테고리(LV1): 취소월 기준 환불율 YoY + 환불 CM
WITH b AS (
  SELECT CITY_NM, STANDARD_CATEGORY_LV_1_NM cat, GMV, REFUND_GMV, REFUND_CM,
    (CONFIRM_KST_DATE>='{M_START}' AND CONFIRM_KST_DATE<'{M_END}') c_cur,
    (REFUND_DATE >='{M_START}' AND REFUND_DATE <'{M_END}') r_cur,
    (CONFIRM_KST_DATE>='{M_START_LY}' AND CONFIRM_KST_DATE<'{M_END_LY}') c_ly,
    (REFUND_DATE >='{M_START_LY}' AND REFUND_DATE <'{M_END_LY}') r_ly
  FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D`
  WHERE {SCOPE}
    AND ((CONFIRM_KST_DATE>='{M_START}' AND CONFIRM_KST_DATE<'{M_END}') OR (REFUND_DATE>='{M_START}' AND REFUND_DATE<'{M_END}')
      OR (CONFIRM_KST_DATE>='{M_START_LY}' AND CONFIRM_KST_DATE<'{M_END_LY}') OR (REFUND_DATE>='{M_START_LY}' AND REFUND_DATE<'{M_END_LY}')))
SELECT CITY_NM, cat,
  ROUND(SUM(IF(r_cur,REFUND_GMV,0))/NULLIF(SUM(IF(c_cur,GMV,0)),0)*100,1) refund_ratio_cur,
  ROUND(SUM(IF(r_ly,REFUND_GMV,0))/NULLIF(SUM(IF(c_ly,GMV,0)),0)*100,1) refund_ratio_ly,
  ROUND(SUM(IF(r_cur,REFUND_CM,0))/1e6,1) refund_cm_cur_M
FROM b GROUP BY 1,2 HAVING SUM(IF(c_cur,GMV,0))>3e7 ORDER BY refund_cm_cur_M DESC
```
그 다음 상위 셀에서 상품(PRODUCT_TITLE/GID)별 환불 Top-N.
- **카테고리 축은 1차로 T&A 대시보드 카테고리**(`mrtdata.business.TNA_dashboard_category_product_list_v1.dashboard_category`, 상품 GID=`filter_product_id`로 조인)로 본다 — 비즈니스 해석이 쉬움. 위 쿼리의 `STANDARD_CATEGORY_LV_1_NM`은 빠른 스캔용이고, 보고·해석은 `dashboard_category`, 정합성·전사비교는 표준 `LV_2/LV_3`로 보조 검증. 사용자가 "대시보드 카테고리"라 하면 표준 LV로 임의 대체하지 않는다.

### STEP 6 — 실제 취소 사유 읽기 (⚠️ 추정 금지, 컬럼에서 읽는다)
**T&A 취소 사유는 `MART_OFFER_SALE_D`에 있다** (`CANCEL_REASON`, `CANCEL_SUBJECT`). FPNA(금액) × OFFER_SALE(사유)를 `RESVE_ID`로 조인.
> FPNA 마트(`MART_FPNA_NONAIR_PROFIT_D`) 자체에는 사유 텍스트가 **없다.** 그래서 반드시 OFFER_SALE을 조인한다.

```sql
WITH o AS (   -- OFFER_SALE은 일 스냅샷 → RESVE_ID별 최신 1행으로 dedup
  SELECT RESVE_ID, CANCEL_SUBJECT, CANCEL_REASON
  FROM `mrtdata.edw_mart.MART_OFFER_SALE_D`
  WHERE BASIS_DATE>='{M_START}' AND CANCEL_KST_DT>='{M_START}' AND CANCEL_KST_DT<'{M_END}'
  QUALIFY ROW_NUMBER() OVER(PARTITION BY RESVE_ID ORDER BY BASIS_DATE DESC)=1 )
SELECT o.CANCEL_SUBJECT, o.CANCEL_REASON,
  COUNT(*) n, ROUND(SUM(f.REFUND_CM)/1e6,1) refund_cm_M
FROM `mrtdata.edw_fpna.MART_FPNA_NONAIR_PROFIT_D` f
JOIN o ON f.RESVE_ID=o.RESVE_ID
WHERE {SCOPE} AND {CITY/CAT 좁히기}
  AND f.REFUND_DATE>='{M_START}' AND f.REFUND_DATE<'{M_END}'
GROUP BY 1,2 ORDER BY refund_cm_M DESC
```
**사유 코드 해석** (`CANCEL_SUBJECT` = 취소 주체 PARTNER/TRAVELER/MANAGER):
- `LACK_TRAVELER` = **최소모객 미달**(공급사가 인원 미달로 회차 취소) — **통제 가능**(회차통합·최소인원 하향·출발보장·소규모 전환). 이동/데이투어에서 큰 편.
- `TRAVELER_PERSONAL_REASON` / `HEALTH_PROBLEM` = **고객 사유** — 대체로 통제 난이. 티켓 등 최소모객 무관 상품에서 큼. 전 카테고리 동반 급증이면 **정책(무료취소·환불규정) 변화** 의심 → CS·정책팀 확인.
- `PARTNER_SCHEDULE` / `OVER_TRAVELER` / `NOT_ENOUGH_CONDITION_TRIP` / `TICKET_DAY_OFF` = 기타 공급사측 — 파트너 운영 이슈.
- 보조 코드: `edw.DW_MRT_ORDERS_CANCEL_CLAIMS`(requester/manager_cancel_reason_type)로 주문 레벨 교차확인 가능.

### STEP 7 — 통제 가능/불가 구분 + 개선 upside
- 사유를 **통제 가능(최소모객·파트너 운영·상품·가격) vs 통제 난이(고객 개인·외부)** 로 나눈다.
- 통제 가능 pocket의 **CFR 회복 CM upside** 산출:
```sql
-- +Xp CFR 회복 시 월 CM upside = 확정월 결제 GMV(=CFR 분모) × Xp × CMR
SELECT ROUND(SUM(IF(c_cur,GMV,0))*0.10 *
  ((SUM(IF(c_cur,CM,0))-SUM(IF(r_cur,REFUND_CM,0)))/NULLIF(SUM(IF(c_cur,GMV,0))-SUM(IF(r_cur,REFUND_GMV,0)),0))/1e6,1) AS upside_10pp_M
FROM b   -- STEP5의 b (해당 pocket으로 SCOPE 좁힘)
```
- 액션은 사유↔레버로 직결: 최소모객→회차운영, 정책성 고객취소→정책 재검토, 파트너→공급사 관리.

---

## 스코프·데이터 주의
- `{SCOPE}` 표준(남부유럽 T&A): `REGION_TNA_NM='Europe-south' AND STANDARD_CATEGORY_LV_1_CD IN ('TOUR','CLASS','SNAP','ACTIVITY','TICKET','CONVENIENCE')`. ME/A 분리 = `REGION_NM IN ('Middle East','Africa')`. (다른 국가는 `COUNTRY_NM`/`FPNA_DOMAIN_NM='TNA'`.)
- **국가/도시명은 저장값 확인 후 필터**: 사용자가 준 명칭(예: "오사카", "다낭")을 바로 필터에 넣지 않는다. `REGION_*`/`COUNTRY_NM`/`CITY_NM`의 실제 저장값(표기·언어 차이)을 먼저 조회해 확인한 뒤 필터링한다 — 안 맞으면 조용히 0건/누락으로 오해석된다.
- **당일 데이터 미사용**: 배치 미완료로 당일 확정·환불이 과소집계된다. `CONFIRM_KST_DATE`/`REFUND_DATE` 모두 **완료된 전날 배치까지만**(예: `< CURRENT_DATE()`) 조회한다.
- **카테고리 기준**: 1차 원인 분석은 **T&A 대시보드 카테고리**(`mrtdata.business.TNA_dashboard_category_product_list_v1.dashboard_category`, GID=`filter_product_id` 조인). 표준 `STANDARD_CATEGORY_LV_2/3_CD`는 보조 검증·전사 정합성용. 어느 카테고리 기준을 썼는지 산출물에 명시한다.
- **환불 부호**: `REFUND_GMV`/`REFUND_CM`은 **양수**로 저장 → net은 **뺀다**. 확정률(환불차감) = `1 − Σ환불GMV(취소월) / Σ확정GMV(확정월)`.
- `MART_OFFER_SALE_D`는 **일 스냅샷** → `RESVE_ID`별 최신 BASIS_DATE 1행으로 dedup(QUALIFY), BASIS_DATE 파티션 필터로 비용 관리.
- CFR/CGMV의 정식 정의·집계는 tna-mbor-draft `references/bigquery.md`, 국가 진단 절차는 tna-country-analysis `SKILL.md` §손익 집계 기준(패턴 A/B) 참조.
- **취소 사유를 지어내지 않는다.** 사유 컬럼이 정말 없는 도메인일 때만 취소 타이밍(TRAVEL_START_DATE − REFUND_DATE; 출발 임박 집중 = 공급사/최소모객 시그니처)을 **보조 근거**로 쓰고, "추정"임을 명시한다.

## 항공 비교 (선택 — 요청 시에만)
비항공이 본체다. 항공은 **source·귀속 방식이 달라** 섞으면 해석이 흔들리므로, 요청 시 **별도 비교 섹션**으로만 붙인다.
- source `mrtdata.edw_mart.MART_SALE_D`, 범위 `STANDARD_CATEGORY_LV_1_CD IN ('FLIGHT','AIR_ANCILLARY') AND KIND=1`.
- CFR = CGMV/GMV, 단 **status snapshot 기반**: `CGMV = Σ(IF(RECENT_STATUS IN ('confirm','finish'), SALES_KRW_PRICE, 0))`, `GMV = Σ(SALES_KRW_PRICE)`.
```sql
SELECT DATE_TRUNC(BASIS_DATE, MONTH) m,
  ROUND(SUM(SALES_KRW_PRICE)/1e6,1) gmv_M,
  ROUND(SUM(IF(RECENT_STATUS IN ('confirm','finish'), SALES_KRW_PRICE,0))/1e6,1) cgmv_M,
  ROUND(SAFE_DIVIDE(SUM(IF(RECENT_STATUS IN ('confirm','finish'),SALES_KRW_PRICE,0)),
                    SUM(SALES_KRW_PRICE))*100,1) cfr_pct
FROM `mrtdata.edw_mart.MART_SALE_D`
WHERE STANDARD_CATEGORY_LV_1_CD IN ('FLIGHT','AIR_ANCILLARY') AND KIND=1
  AND BASIS_DATE >= '{START}' AND BASIS_DATE < CURRENT_DATE()
GROUP BY 1 ORDER BY 1
```
⚠️ 항공은 **BASIS_DATE 판매 snapshot·status 기반**, 비항공 FPNA는 **결제월/환불월 net event** — 전체 합산 CFR은 만들 수 있으나 **원인 해석은 항공/비항공 분리**한다.

## 산출물
- 월별 CFR 추세(GMV·CGMV·CFR, 구조 브레이크 시점) + 주차별 WoW(변동 주) + MoM×YoY 판정("안착 vs 진행중 악화")
- 드라이버 분해(수요/확정/마진) → 미달이 확정 단계 문제인지 확정
- **rate effect vs mix effect 분리**(상품군 자체 악화 vs 믹스 변화)
- 범인 지역·카테고리(대시보드 기준)·상품 Top-N (환불 CM 기준)
- **실제 취소 사유 분해**(통제 가능/불가) + pocket별 CFR 회복 CM upside
- 사유↔레버↔액션 매핑
- (요청 시) 항공 비교 섹션 — source 차이 명시
- 명시 사항: 환불 귀속 처리 방식·사용한 카테고리 기준·당일 데이터 제외

## NOT for
- 숙박·보험 등 T&A 외 도메인 (사유 소스 다름). 항공은 원인 진단 본체가 아니라 **별도 비교 섹션**으로만(위 참조).
- 전환(CVR)·유입(UV) 단계 진단 → tna-country-analysis 퍼널 분석 사용
