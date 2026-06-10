---
name: blog-freshness-alert
description: 담당 도시·카테고리별 마리트 네이버 블로그 글 현황을 점검하고, 1년 이내 글이 없는 항목에 대해 팀 Slack에 알럿을 보냅니다. 기존 글 현황 + 신규 주제 제안을 함께 포함합니다.
allowed-tools: Bash WebSearch mcp__claude_ai_Slack__slack_send_message mcp__claude_ai_Slack__slack_search_channels
argument-hint: [도시/카테고리 목록 또는 '전체'] [--channel #채널명]
---

당신은 마이리얼트립 블로그 콘텐츠 신선도를 모니터링하는 전문가입니다.

점검 대상: $ARGUMENTS (미지정 시 아래 기본 목록 전체 사용)

**이 스킬의 목적은 담당 도시·카테고리별 블로그 콘텐츠 공백을 사전에 감지하고, 팀이 콘텐츠 기획에 바로 활용할 수 있는 실행 가능한 알럿을 만드는 것입니다.**

**블로그 소스**: `https://blog.naver.com/myrealtrip` (마이리얼트립 네이버 공식 블로그)
**데이터 수집 방식**: 네이버 블로그 RSS 피드 (`https://rss.blog.naver.com/myrealtrip.xml`)를 Python으로 파싱

아래 순서대로 진행하세요.

---

## STEP 0: 설정 확인

### 담당 도시

| 권역 | 도시/지역 | 검색 키워드 (한국어) | 검색 키워드 (영문) |
|------|----------|--------------------|--------------------|
| 스페인 | 바르셀로나 | 바르셀로나, 바르샤 | Barcelona |
| 스페인 | 마드리드 | 마드리드 | Madrid |
| 스페인 | 세비야 | 세비야, 세비아 | Seville |
| 스페인 | 그라나다 | 그라나다, 알함브라 | Granada |
| 스페인 | 마요르카 | 마요르카, 마요르까 | Mallorca, Majorca |
| 포르투갈 | 리스본 | 리스본 | Lisbon |
| 포르투갈 | 포르투 | 포르투 | Porto |
| 튀르키예 | 이스탄불 | 이스탄불, 터키 | Istanbul |
| 튀르키예 | 카파도키아 | 카파도키아 | Cappadocia |
| 그리스 | 아테네 | 아테네 | Athens |
| 그리스 | 산토리니 | 산토리니 | Santorini |
| 이집트 | 카이로 | 카이로, 이집트, 피라미드 | Cairo, Egypt |
| 이집트 | 룩소르 | 룩소르 | Luxor |
| 중동 | 두바이 | 두바이 | Dubai |
| 중동 | 아부다비 | 아부다비 | Abu Dhabi |
| 중동 | (기타 UAE) | UAE, 아랍에미리트 | UAE |
| 아프리카 | 모로코 | 모로코, 마라케시, 페스, 사하라 | Morocco, Marrakech, Fez |
| 아프리카 | 남아공 | 남아공, 케이프타운 | South Africa, Cape Town |
| 아프리카 | (기타) | 아프리카 여행, 탄자니아, 킬리만자로, 케냐 | Africa travel |

### 담당 카테고리 (도시와 별도로 점검)

| 카테고리 | 검색 키워드 (한국어) | 비고 |
|----------|--------------------|----|
| 스페인 축구 | 스페인 축구, 라리가, FC바르셀로나 경기, 레알마드리드 경기, 캄프누, 산티아고 베르나베우, 축구 직관 | 경기 관람·투어·티켓 관련 |
| 산티아고 순례길 | 산티아고 순례길, 카미노 데 산티아고, 순례자 여행, 카미노, 산티아고 순례, 순례자 | 코스·준비·숙소·후기 |
| 허니문 | 허니문, 신혼여행, 몰디브 | 몰디브 포함. 허니문 인기 지역 전반 |

사용자가 특정 도시나 카테고리만 지정하면 해당 항목만 점검합니다.

### 알럿 기준

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| 점검 기간 | 1년 (365일) | 최근 1년 이내 블로그 글이 있는지 확인 |
| `channel` | 사용자 지정 | 알럿을 보낼 Slack 채널 또는 스레드 |

---

## STEP 1: 네이버 블로그 RSS 수집 및 키워드 매칭

### 1-1. RSS 피드 수집

아래 Python 스크립트를 `.py` 파일로 저장한 뒤 `python {파일명}.py`로 실행하세요. 인라인 `-c` 방식은 한글·특수문자 이스케이프 이슈가 있으므로 반드시 파일로 실행합니다.

```python
import urllib.request, xml.etree.ElementTree as ET, json, sys, io, re
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = 'https://rss.blog.naver.com/myrealtrip.xml'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
data = resp.read().decode('utf-8', errors='replace')

root = ET.fromstring(data)
items = root.find('channel').findall('item')

posts = []
for item in items:
    title = item.find('title').text or ''
    link = item.find('link').text or ''
    pub = item.find('pubDate').text or ''
    cat = item.find('category').text or ''
    desc_raw = item.find('description').text or ''
    desc = re.sub(r'<[^>]+>', '', desc_raw)[:300]
    if link and '?' in link:
        link = link.split('?')[0]
    try:
        dt = datetime.strptime(pub.strip(), '%a, %d %b %Y %H:%M:%S %z')
    except:
        dt = None
    posts.append({
        'title': title, 'date': pub, 'dt': dt,
        'category': cat, 'link': link, 'desc': desc
    })
```

이 스크립트의 `posts` 리스트에 RSS 피드의 모든 포스트가 들어갑니다.

### 1-2. 키워드 매칭

수집된 포스트의 `title + description + category` 텍스트에서 STEP 0의 각 도시/카테고리 키워드를 대소문자 무시하고 검색합니다.

```python
targets = {
    'barcelona': {'name': '바르셀로나', 'region': '스페인', 'type': 'city',
                  'keywords': ['바르셀로나', 'barcelona', '바르샤']},
    'madrid': {'name': '마드리드', 'region': '스페인', 'type': 'city',
               'keywords': ['마드리드', 'madrid']},
    'seville': {'name': '세비야', 'region': '스페인', 'type': 'city',
                'keywords': ['세비야', '세비아', 'seville']},
    'granada': {'name': '그라나다', 'region': '스페인', 'type': 'city',
                'keywords': ['그라나다', 'granada', '알함브라']},
    'mallorca': {'name': '마요르카', 'region': '스페인', 'type': 'city',
                 'keywords': ['마요르카', '마요르까', 'mallorca', 'majorca']},
    'lisbon': {'name': '리스본', 'region': '포르투갈', 'type': 'city',
               'keywords': ['리스본', 'lisbon']},
    'porto': {'name': '포르투', 'region': '포르투갈', 'type': 'city',
              'keywords': ['포르투', 'porto']},
    'istanbul': {'name': '이스탄불', 'region': '튀르키예', 'type': 'city',
                 'keywords': ['이스탄불', 'istanbul', '터키']},
    'cappadocia': {'name': '카파도키아', 'region': '튀르키예', 'type': 'city',
                   'keywords': ['카파도키아', 'cappadocia']},
    'athens': {'name': '아테네', 'region': '그리스', 'type': 'city',
               'keywords': ['아테네', 'athens']},
    'santorini': {'name': '산토리니', 'region': '그리스', 'type': 'city',
                  'keywords': ['산토리니', 'santorini']},
    'cairo': {'name': '카이로', 'region': '이집트', 'type': 'city',
              'keywords': ['카이로', 'cairo', '이집트', 'egypt', '피라미드']},
    'luxor': {'name': '룩소르', 'region': '이집트', 'type': 'city',
              'keywords': ['룩소르', 'luxor']},
    'dubai': {'name': '두바이', 'region': '중동', 'type': 'city',
              'keywords': ['두바이', 'dubai']},
    'abudhabi': {'name': '아부다비', 'region': '중동', 'type': 'city',
                 'keywords': ['아부다비', 'abu dhabi']},
    'uae': {'name': '(기타 UAE)', 'region': '중동', 'type': 'city',
            'keywords': ['uae', '아랍에미리트']},
    'morocco': {'name': '모로코', 'region': '아프리카', 'type': 'city',
                'keywords': ['모로코', 'morocco', '마라케시', '페스', '사하라']},
    'southafrica': {'name': '남아공', 'region': '아프리카', 'type': 'city',
                    'keywords': ['남아공', '케이프타운', 'south africa', 'cape town']},
    'africa_etc': {'name': '(기타 아프리카)', 'region': '아프리카', 'type': 'city',
                   'keywords': ['아프리카 여행', 'africa', '탄자니아', '킬리만자로', '케냐']},
    'futbol': {'name': '스페인 축구', 'region': '카테고리', 'type': 'category',
               'keywords': ['라리가', '캄프누', '베르나베우', '축구 직관',
                           'fc바르셀로나', '레알마드리드 경기', '스페인 축구']},
    'camino': {'name': '산티아고 순례길', 'region': '카테고리', 'type': 'category',
               'keywords': ['순례길', '카미노', '산티아고 순례', '순례자']},
    'honeymoon': {'name': '허니문', 'region': '카테고리', 'type': 'category',
                  'keywords': ['허니문', '신혼여행', '몰디브']},
}
```

- 한 포스트가 여러 도시/카테고리에 매칭될 수 있습니다 (예: 프로모션 글에 여러 도시 언급).
- 동일 URL은 항목 내에서 중복 제거합니다.

### 1-3. 제약 사항

- **RSS 피드는 최근 약 50개 포스트만 포함합니다.** 50개 안에 해당 키워드가 없다고 해서 해당 도시 글이 전혀 없다는 뜻이 아닙니다.
- `🔴 (NEW)` 상태는 "RSS 피드 내 매칭 포스트 없음"을 의미합니다. 오래된 글은 RSS에 포함되지 않을 수 있습니다.
- `*.naver.com` 도메인은 WebSearch/WebFetch로 접근할 수 없습니다. 반드시 Python `urllib.request`로 RSS를 수집하세요.
- Windows 환경에서 Python 실행 시 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`를 추가하여 cp949 인코딩 에러를 방지하세요.

---

## STEP 2: 현황 분석

### 2-1. 항목별 현황 정리

각 도시/카테고리에 대해 아래를 계산하세요:

- **마지막 글 발행일**: 매칭된 가장 최근 블로그 글의 날짜
- **경과 일수**: 오늘 날짜 - 마지막 글 발행일
- **최근 1년 이내 글 수**: 최근 365일 이내에 발행된 매칭 글 수
- **전체 매칭 수**: RSS 피드 내 매칭된 총 글 수
- **상태**: 아래 기준으로 판정

| 조건 | 상태 | 표시 |
|------|------|------|
| 최근 1년 이내 매칭 글 없음 | 업데이트 필요 | 🔴 |
| 최근 1년 이내 매칭 글 있음 | OK | 🟢 |
| RSS 피드 내 매칭 글 자체가 없음 | 신규 작성 필요 | 🔴 (NEW) |

### 2-2. 콘텐츠 갭 분석

🔴 상태인 항목에 대해 기존 글의 주제를 정리하고, 아직 다뤄지지 않은 주제 영역을 식별하세요.

주제 체크리스트:
- [ ] 여행 코스 / 일정 가이드
- [ ] 맛집 / 음식 가이드
- [ ] 교통 / 이동 방법
- [ ] 숙소 추천
- [ ] 현지 투어 / 액티비티
- [ ] 문화 / 역사 / 축제
- [ ] 쇼핑 / 기념품
- [ ] 실용 팁 (비자, 환전, 안전)
- [ ] 시즌별 / 계절별 가이드

카테고리 항목(축구, 순례길, 허니문)은 해당 카테고리에 맞는 세부 주제로 체크합니다.

---

## STEP 3: 신규 주제 제안 생성

🔴 상태인 항목에 대해 블로그 주제를 2~3개 제안하세요.

### 제안 기준 (우선순위 순)

1. **콘텐츠 갭**: 기존 글에서 아직 안 다룬 주제 영역
2. **시즌 적합성**: 현재 시점 기준 2~3개월 내 여행 시즌에 맞는 주제
3. **검색 트렌드**: WebSearch로 `"{도시/카테고리} 여행 2026"` 등을 검색해 최근 관심 키워드 파악
4. **상품 연계**: 마리트에서 해당 도시/카테고리의 인기 상품과 연결할 수 있는 주제

### 제안 형식

각 제안에 아래를 포함하세요:

```
제안 제목: (예: "2026 라리가 직관 가이드 — 캄프누 & 베르나베우 완벽 정리")
주제 영역: (예: 스페인 축구 / 투어·액티비티)
제안 이유: (예: 최근 1년간 축구 관련 글 없음 + 2026-27 시즌 개막 앞두고 검색 증가)
예상 키워드: (예: 스페인 축구 직관, 캄프누 티켓, 라리가 일정)
연계 가능 상품: (예: 바르셀로나 캄프누 투어, 마드리드 축구 패키지)
```

---

## STEP 4: 알럿 메시지 구성

아래 형식으로 Slack 알럿 메시지를 구성하세요.

### 알럿 메시지 템플릿

```
📋 블로그 콘텐츠 현황 점검 ({오늘 날짜})

소스: blog.naver.com/myrealtrip RSS (최근 50개 포스트 기준)

🔴 최근 1년간 블로그 글 없음 — 업데이트 필요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{🔴 상태 항목별로 반복}

📍 {도시명 또는 카테고리명} ({권역}) — {🔴 또는 🔴 NEW 글 없음}
   {매칭 글이 있는 경우:}
   마지막 글: {날짜} ({N일 전}) / RSS 내 {N}편
   최근 글:
   • {글 제목 1} ({날짜})
   • {글 제목 2} ({날짜})

   📝 추천 주제:
   1. {제안 제목} — {제안 이유 한 줄}
   2. {제안 제목} — {제안 이유 한 줄}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 최근 1년 이내 글 있음 — OK
| 항목 | 권역 | 마지막 글 | 1년 내 |
|------|------|----------|--------|
{OK 항목: 항목명 | 권역 | N일 전 | N편}

참고: RSS 피드는 최근 50개 포스트만 포함합니다. 🔴 NEW 항목은 과거 글이 있을 수 있지만 최근 50개 안에 없다는 뜻입니다.
```

### 전부 OK인 경우

```
✅ 블로그 콘텐츠 점검 완료 ({오늘 날짜})
모든 담당 도시·카테고리에 최근 1년 이내 블로그 글이 있어요!

{항목별 마지막 글 날짜 요약}
```

---

## STEP 5: Slack 전송

### 5-1. 채널 확인

사용자가 `--channel` 옵션으로 채널을 지정했으면 해당 채널에 전송합니다.
지정하지 않았으면 아래를 질문하세요:

> "알럿을 보낼 Slack 채널(또는 스레드 링크)을 알려주세요!
> 예: #semea-content-planning, 또는 스레드 permalink"

### 5-2. 전송

Slack MCP 도구를 사용해서 알럿 메시지를 전송하세요.
- 채널이면 새 메시지로 전송
- 스레드 링크면 해당 스레드에 reply로 전송

전송 완료 후 사용자에게 확인:

> "알럿을 {채널명}에 전송했어요!
> 🔴 {N}개 항목이 최근 1년간 블로그 글이 없는 상태예요."

---

## STEP 6: 후속 액션 제안

알럿 전송 후, 🔴 항목이 있으면 아래를 제안하세요:

> "바로 이어서 할 수 있는 작업이에요:
>
> 1. 🔴 항목 중 하나를 골라 `naver-blog-geo` 스킬로 바로 블로그 글 작성 시작
> 2. 추천 주제의 상세 기획안 작성 (타깃 독자, 핵심 메시지, 상품 연계 계획)
> 3. 전체 콘텐츠 캘린더 초안 생성 (향후 3개월)
>
> 어떤 걸 해볼까요?"

---

## 주의사항

- **네이버 블로그 RSS 제약**: RSS 피드(`rss.blog.naver.com/myrealtrip.xml`)는 최근 약 50개 포스트만 포함합니다. RSS에서 매칭되지 않는 도시도 과거에 글이 존재할 수 있습니다.
- **WebSearch/WebFetch 제약**: `*.naver.com` 도메인은 WebSearch/WebFetch로 접근할 수 없습니다. 반드시 Python `urllib.request`로 RSS를 수집하세요.
- **Windows 환경**: Python 실행 시 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`를 추가하여 cp949 인코딩 에러를 방지하세요.
- 블로그 글의 날짜가 불확실하면 해당 글에 "날짜 미확인"을 표기하고, 최근 글 판정에서 제외하세요.
- 한 항목에 대한 검색 키워드가 여러 개인 경우 모든 키워드로 매칭해서 합산하세요 (중복 URL 제거).
- 검색 결과 중 해당 도시/카테고리와 무관한 글은 수동으로 제외하세요.
- 카테고리 항목(축구, 순례길, 허니문)은 특정 도시에 종속되지 않으므로, 도시 점검과 별도로 진행하세요.
- 허니문 카테고리는 몰디브·산토리니·두바이 등 허니문 인기 지역을 모두 포괄합니다.
- 중동·아프리카 권역은 주요 도시(두바이, 아부다비, 모로코, 남아공) 외에도 해당 권역 키워드로 넓게 검색하세요.
- 프로모션/할인 글에서 도시명이 언급된 경우 매칭은 되지만, 해당 도시 전용 콘텐츠와 구분하여 분석하세요.
