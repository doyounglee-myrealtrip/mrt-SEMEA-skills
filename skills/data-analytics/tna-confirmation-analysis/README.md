# T&A 확정률(CFR)·취소 진단

> 확정률(CFR)이 빠지거나 취소·환불이 급증했을 때, **"언제 구조가 바뀌었나 → rate/mix 중 무엇인가 → 어느 지역·카테고리·상품이 범인인가 → 실제 취소 사유가 뭔가 → 통제 가능한가"** 를 순서대로 데이터로 끝까지 규명하는 정본 스킬입니다.
>
> `tna-mbor-draft`(월간 회고)·`tna-country-analysis`(국가 진단)가 확정률 문제를 만나면 이 스킬의 방법론을 참조합니다.

---

## 한 줄 요약

```
/tna-confirmation-analysis 남부유럽 확정률 왜 빠졌어
/tna-confirmation-analysis 스페인 취소 급증 원인
"CFR 하락 원인 분석해줘"  ·  "환불율 급증 진단해줘"
```

> **확정률 정의(정본): `CFR = CGMV / GMV`.** `GMV`는 확정월(`CONFIRM_KST_DATE`) 결제분, `CGMV`는 환불월(`REFUND_DATE`) 환불을 차감한 net. 두 side를 서로 다른 달로 분리 귀속하므로 **여행월로 필터하지 않습니다.**

---

## 이 스킬이 존재하는 이유 — 확정률 진단에서 반복된 실수 4가지

| # | 반복된 실수 | 왜 틀리나 | 이 스킬의 교정 |
|---|-----------|----------|--------------|
| 1 | **여행월로 필터해서 봤다** | `CFR=CGMV/GMV`에서 환불 차감은 취소월(`REFUND_DATE`) 기준이라, 여행월로 필터하면 취소월이 다른 건이 빠져 보고 숫자와 어긋난다 | 결제=`CONFIRM_KST_DATE`, 환불=`REFUND_DATE` 분리 귀속 (STEP 0) |
| 2 | **취소 사유를 타이밍으로 "추정"했다** | 실제 취소 사유 컬럼이 존재한다 (`MART_OFFER_SALE_D.CANCEL_REASON`) | 추정 금지, 컬럼에서 읽는다 (STEP 6) |
| 3 | **YoY만 보고 "이번 달 미달"로 귀속했다** | 과거에 구조가 한 단계 내려앉은 것을 이번 달 사건으로 오독 | 월별 시계열 + MoM 교차검증 (STEP 1~2) |
| 4 | **전 지역 골고루 얕게 봤다** | 범인은 소수 상품에 집중 | 지역→카테고리→상품(GID)으로 좁힌다 (STEP 5) |

---

## 시작하기

### 전제 조건

| # | 필요한 것 | 왜 필요한가 | 확인 방법 |
|---|----------|-----------|----------|
| 1 | **Claude Code** | 스킬을 실행하는 AI 코딩 에이전트 | 터미널에서 `claude` 입력 시 실행되면 OK |
| 2 | **`mrt-dp-dbt-airflow` 레포 클론 + 그 안에서 실행** | 이 스킬은 그 레포의 BQ 안전 wrapper, 분석 subagent, 매출/지표 규칙, dbt 모델·metric 정의를 사용합니다 | `mrt-dp-dbt-airflow` 폴더로 이동한 뒤 `claude` 실행 |
| 3 | **BigQuery 접근 권한** (gcloud 인증) | 확정률/취소 데이터를 BigQuery(`mrtdata`)에 쿼리 | `bq query --use_legacy_sql=false "SELECT 1"` 실행 시 결과가 나오면 OK |

> ⚠️ **반드시 `mrt-dp-dbt-airflow` 폴더 안에서 실행하세요.** 다른 폴더에서 실행하면 안전 wrapper·분석 subagent·지표 규칙이 빠져서 정확도와 안전장치가 떨어집니다.

### 설치 방법

#### 방법 1: mrt-skill CLI (추천)

```bash
mrt-skill install tna-confirmation-analysis
```

#### 방법 2: 수동 설치

```bash
mkdir -p .claude/skills/tna-confirmation-analysis
curl -fsSL https://raw.githubusercontent.com/doyounglee-myrealtrip/mrt-SEMEA-skills/main/skills/data-analytics/tna-confirmation-analysis/SKILL.md \
  -o .claude/skills/tna-confirmation-analysis/SKILL.md
```

---

## 진단 순서 (반드시 이 순서)

```
STEP 0  관점 고정        CFR = CGMV/GMV (결제월/환불월 분리, net-event)
   │
STEP 1  구조 브레이크    월별(12~18개월) + 주차별 WoW → "언제부터 이렇게 됐나"
   │
STEP 2  MoM × YoY 삼각검증  안착된 옛 레벨인가 vs 진행 중 악화인가
   │
STEP 3  드라이버 분해    CM = GMV × CFR × CMR → 미달이 정말 확정 단계 문제인가
   │
STEP 4  rate vs mix     상품군 자체 확정률 악화(rate) vs 저확정 카테고리 비중 증가(mix)
   │
STEP 5  범인 좁히기      지역 → 카테고리 → 상품(GID), 환불 CM 집중 셀 선별
   │
STEP 6  실제 취소 사유    CANCEL_REASON/CANCEL_SUBJECT 컬럼에서 읽기 (⚠️ 추정 금지)
   │
STEP 7  통제 가능/불가    사유↔레버↔액션 매핑 + pocket별 CFR 회복 CM upside
```

### 각 STEP이 답하는 질문

| STEP | 답하는 질문 | 핵심 산출 |
|------|-----------|----------|
| **0** | 확정률을 어떻게 정의·집계하나 | `CFR = 1 − Σ환불GMV(취소월)/Σ확정GMV(확정월)` |
| **1** | 언제부터 이렇게 됐나 | 월별·주차별 CFR 추세, 구조 브레이크 시점 |
| **2** | 지금도 움직이나, 안착했나 | MoM flat=안착 / MoM 하락=진행 중 악화 |
| **3** | 미달이 수요·마진 아니라 확정 문제인가 | CM 변화를 GMV·CFR·CMR로 %·%p 분해 |
| **4** | 상품군이 나빠졌나, 믹스가 바뀌었나 | rate_pp / mix_pp 기여 분리 |
| **5** | 어느 지역·카테고리·상품이 범인인가 | 환불 CM 집중 Top-N 셀 |
| **6** | 왜 취소하나 (실제 사유) | `LACK_TRAVELER`(최소모객) / 고객사유 / 파트너 등 |
| **7** | 통제 가능한가, 회복 시 얼마 버나 | 통제 가능/불가 구분 + CFR +Xp 회복 CM upside |

---

## rate effect vs mix effect — 왜 갈라야 하나

전체 CFR 변화가 두 원인 중 무엇인지에 따라 **처방이 완전히 다릅니다.**

| 성격 | 무엇이 변했나 | 처방 |
|------|-------------|------|
| **rate effect** | 카테고리 자체 확정률이 나빠짐 (비중 고정) | 해당 상품군의 취소·공급 문제 해결 (회차운영·공급사 관리) |
| **mix effect** | 저확정률 카테고리 비중이 커짐 (확정률 고정) | 판매·노출 믹스를 만든 채널·프로모션·상품구성 조정 |

`전체 CFR = Σ_c (share_c × CFR_c)` 를 두 시점으로 분해:
- **rate**: `Σ_c share_c^base × (CFR_c^cur − CFR_c^base)` (비중 고정, 확정률만 변화)
- **mix**: `Σ_c (share_c^cur − share_c^base) × CFR_c^base` (확정률 고정, 비중만 변화)

---

## 실제 취소 사유 코드 (STEP 6)

취소 사유는 **`MART_OFFER_SALE_D`에서 읽습니다** (`CANCEL_REASON`, `CANCEL_SUBJECT`). FPNA 마트(금액)에는 사유 텍스트가 없어 `RESVE_ID`로 조인합니다.

| 사유 코드 | 의미 | 통제 가능성 |
|----------|------|-----------|
| `LACK_TRAVELER` | 최소모객 미달 (공급사가 인원 미달로 회차 취소) | **통제 가능** — 회차통합·최소인원 하향·출발보장·소규모 전환 |
| `TRAVELER_PERSONAL_REASON` / `HEALTH_PROBLEM` | 고객 개인 사유 | 대체로 통제 난이 (전 카테고리 동반 급증이면 정책 변화 의심) |
| `PARTNER_SCHEDULE` / `OVER_TRAVELER` / `TICKET_DAY_OFF` 등 | 공급사측 운영 이슈 | 통제 가능 — 파트너 관리 |

---

## 데이터 소스

| 데이터 | 테이블 | 용도 |
|--------|--------|------|
| GMV·CGMV·CFR·CM·환불금액 | `edw_fpna.MART_FPNA_NONAIR_PROFIT_D` | 확정률·드라이버·rate/mix·범인 셀 |
| 취소 사유 (`CANCEL_REASON`/`CANCEL_SUBJECT`) | `edw_mart.MART_OFFER_SALE_D` | STEP 6 실제 사유 (RESVE_ID 조인) |
| 대시보드 카테고리 | `business.TNA_dashboard_category_product_list_v1` | 1차 원인 분석 카테고리 축 |
| (선택) 항공 비교 | `edw_mart.MART_SALE_D` | status snapshot 기반 — 별도 섹션 |

> ⚠️ **손익 집계 기준 (2026-06 개편 반영).** 결제 side는 `CONFIRM_KST_DATE`, 환불 side는 `REFUND_DATE`로 분리 귀속. `REFUND_GMV`/`REFUND_CM`은 **양수로 저장되는 차감액** → net은 뺍니다. 컬럼명은 `CM`(구 `CON_MARGIN`)·`COGS`(구 `NET_PRICE`). 정식 정의·집계는 `tna-mbor-draft` `references/bigquery.md`, 국가 진단 절차는 `tna-country-analysis` SKILL.md §손익 집계 기준(패턴 A/B) 참조.

---

## FAQ

### Q: tna-country-analysis와 뭐가 다른가요?
country-analysis는 공헌이익을 **퍼널 6단계 전체(UV→CVR→주문→AOV→CFR→마진율)**로 진단합니다. 이 스킬은 그중 **확정(CFR)·취소 단계만 깊이** 파는 정본입니다. 전환(CVR)·유입(UV) 문제는 country-analysis를, 확정률·취소 문제는 이 스킬을 씁니다.

### Q: 왜 여행월로 필터하면 안 되나요?
`CFR=CGMV/GMV`에서 환불 차감은 **취소월(`REFUND_DATE`) 기준**입니다. {여행월 7월·예약월 5월·취소월 6월}인 건은 6월 CFR을 깎지만 여행월 필터에선 빠져 보고 숫자와 어긋납니다. 여행월은 원인 설명용 보조 변수로만 씁니다.

### Q: 취소 사유를 타이밍으로 추정하면 안 되나요?
실제 사유 컬럼(`CANCEL_REASON`)이 있으므로 **읽습니다.** 사유 컬럼이 정말 없는 도메인일 때만 취소 타이밍(출발 임박 집중 = 공급사/최소모객 시그니처)을 보조 근거로 쓰고, "추정"임을 명시합니다.

### Q: 항공도 분석하나요?
비항공이 본체입니다. 항공은 source(`MART_SALE_D`)·귀속 방식(status snapshot)이 달라 섞으면 해석이 흔들리므로, **요청 시 별도 비교 섹션**으로만 붙입니다.

---

## NOT for

- 숙박·보험 등 T&A 외 도메인 (취소 사유 소스가 다름)
- 전환(CVR)·유입(UV) 단계 진단 → `tna-country-analysis` 퍼널 분석 사용
- 항공은 원인 진단 본체가 아니라 **별도 비교 섹션**으로만

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2026-07-05 | 최초 배포. 확정률 진단 반복 실수 4가지 교정을 위한 7-STEP 정본 방법론과 쿼리 템플릿. `tna-mbor-draft`·`tna-country-analysis`가 확정률 이슈 시 참조. 2026-06 손익 개편(확정월/환불월 분리 귀속, `REFUND_*` 양수 차감) 기준 반영. |
