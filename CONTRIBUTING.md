# 스킬 추가/수정 가이드

팀원 누구나 스킬을 추가하거나 수정할 수 있어요. 아래 순서를 따라해주세요.

---

## 새 스킬 추가하기

### 1. 폴더 만들기

`skills/<카테고리>/<스킬이름>/` 폴더를 만드세요.

```
skills/
└── engineering/
    └── my-new-skill/     ← 새 폴더
        ├── SKILL.md
        └── skill-meta.json
```

카테고리는 `engineering`, `data-analytics`, `product`, `common` 중 하나를 선택하세요.

---

### 2. SKILL.md 작성하기

Claude에게 줄 지시사항을 작성합니다. 아래 형식을 따라주세요:

```markdown
---
name: 스킬이름
description: 이 스킬이 무엇을 하는지, 언제 쓰는지 한두 줄로 설명
---

# 스킬 내용

Claude가 따라야 할 지시사항을 여기에 작성합니다.
```

---

### 3. skill-meta.json 작성하기

```json
{
  "version": "1.0.0",
  "author": "슬랙_닉네임",
  "category": "engineering",
  "tags": ["태그1", "태그2"],
  "description": "스킬에 대한 한 줄 설명",
  "changelog": [
    {
      "version": "1.0.0",
      "date": "YYYY-MM-DD",
      "changes": "첫 번째 배포"
    }
  ]
}
```

---

### 4. registry.json 업데이트하기

루트의 `registry.json`에 새 스킬 항목을 추가하세요:

```json
{
  "name": "스킬이름",
  "path": "engineering/my-new-skill",
  "category": "engineering",
  "description": "한 줄 설명",
  "version": "1.0.0",
  "author": "슬랙_닉네임",
  "tags": ["태그1", "태그2"]
}
```

---

### 5. Pull Request 보내기

변경사항을 PR로 올려주세요. 제목 형식:

- 새 스킬: `[스킬추가] 스킬이름 - 한줄설명`
- 수정: `[스킬수정] 스킬이름 - 변경내용`

---

## 버전 규칙

| 변경 유형 | 버전 올리는 방법 | 예시 |
|-----------|----------------|------|
| 큰 변경 (동작 방식 바뀜) | 첫 번째 숫자 +1 | 1.0.0 → 2.0.0 |
| 기능 추가 | 두 번째 숫자 +1 | 1.0.0 → 1.1.0 |
| 버그 수정, 소소한 수정 | 세 번째 숫자 +1 | 1.0.0 → 1.0.1 |

---

## 좋은 스킬 만들기 팁

- **구체적으로**: "코드를 잘 리뷰해줘" 보다 "PR에서 보안 취약점, 성능 이슈, 코드 가독성을 순서대로 확인해줘"
- **왜를 설명**: Claude는 이유를 알면 더 잘 동작해요
- **예시 포함**: 원하는 출력 형식의 예시를 넣으면 일관성이 높아져요
