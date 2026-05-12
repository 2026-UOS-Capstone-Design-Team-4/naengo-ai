# 04. Pending Recipe Enrichment

사용자가 제출한 레시피는 제목과 본문만 있고 재료, 조리 단계, 난이도, 태그 같은 구조화 필드가 비어 있을 수 있습니다. 관리자는 승인 전에 AI로 빈 값을 보완할 수 있습니다.

## Goal

- 사용자가 작성한 내용을 바탕으로 비어 있는 컬럼을 채울 후보를 만듭니다.
- AI 결과는 DB에 저장하지 않고 API 응답으로만 반환합니다.
- 관리자가 미리보기에서 수정한 뒤 기존 `PATCH` API로 저장합니다.
- DB가 AI 후보 이력으로 불필요하게 커지는 것을 피합니다.

## Flow

```text
pending_recipes
  -> admin requests enrichment
  -> AI returns suggested_patch
  -> frontend shows editable preview
  -> admin edits if needed
  -> PATCH pending_recipes
```

## API

```text
POST /api/v1/admin/pending-recipes/{pending_recipe_id}/enrich
PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}
```

`enrich`는 AI 보정 후보를 반환하기만 합니다. 실제 저장은 기존 `PATCH` API가 담당합니다.

## Target Fields

AI 보정 대상:

- `description`
- `ingredients`
- `ingredients_raw`
- `instructions`
- `servings`
- `cooking_time`
- `calories`
- `difficulty`
- `category`
- `tags`
- `tips`

AI가 보정하지 않는 대상:

- `user_id`
- `status`
- `admin_note`
- `reviewed_at`
- `is_active`

## Request

```json
{
  "target_fields": ["ingredients", "instructions", "difficulty", "tags"],
  "mode": "missing_only",
  "admin_instruction": "사용자가 쓴 content를 기준으로 과장하지 말고 빈 값만 채워줘."
}
```

`mode`:

- `missing_only`: 비어 있는 필드만 제안합니다.
- `override`: 관리자가 명시한 필드에 대해 기존 값이 있어도 새 후보를 제안합니다.

## Response

```json
{
  "pending_recipe_id": 31,
  "mode": "missing_only",
  "suggested_patch": {
    "ingredients": [
      {"name": "김치", "amount": "1", "unit": "컵"},
      {"name": "밥", "amount": "1", "unit": "공기"},
      {"name": "달걀", "amount": "1", "unit": "개"}
    ],
    "instructions": [
      "김치를 먹기 좋은 크기로 자릅니다.",
      "팬에 김치와 밥을 넣고 볶습니다.",
      "달걀 프라이를 올려 마무리합니다."
    ],
    "servings": 1,
    "cooking_time": 10,
    "difficulty": "easy",
    "tags": ["한그릇", "볶음밥", "김치"]
  },
  "confidence": {
    "ingredients": 0.82,
    "instructions": 0.76,
    "difficulty": 0.74,
    "tags": 0.88
  },
  "warnings": []
}
```

## Apply

프론트는 `suggested_patch`를 수정 가능한 폼에 채웁니다. 관리자가 저장하면 기존 수정 API로 보냅니다.

```text
PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}
```

이 방식에서는 별도 `apply` 또는 `reject` API가 필요하지 않습니다. 마음에 들지 않으면 저장하지 않으면 됩니다.

## Storage Policy

초기 구현에서는 AI 보정 후보를 DB에 저장하지 않습니다.

저장하지 않는 값:

- prompt
- input snapshot
- suggested patch
- confidence details

로그로 남길 수 있는 값:

- 관리자 id
- pending recipe id
- target fields
- provider/model
- 성공/실패 여부
- latency/cost

나중에 감사 이력이 필요해지면 별도 audit log 또는 object storage로 확장합니다.

## Prompt Rules

- 사용자가 작성한 내용에서 추론 가능한 값만 채웁니다.
- 확실하지 않은 값은 비워두거나 낮은 confidence로 표시합니다.
- 기존 값은 `missing_only`에서 덮어쓰지 않습니다.
- 식품 안전, 알레르기, 건강 효과를 과장하지 않습니다.

## Failure Handling

| Failure | Handling |
| --- | --- |
| 입력 정보 부족 | 빈 `suggested_patch`와 warning 반환 |
| AI provider 실패 | 502 `UPSTREAM_ERROR` |
| patch validation 실패 | 422 `VALIDATION_FAILED` |
| 이미 승인된 pending recipe | 409 `PENDING_RECIPE_ALREADY_REVIEWED` |
