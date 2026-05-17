# 06. Classification and Confidence

`recipe_classifications`는 추천, 검색 필터, 개인화 rerank에 쓰는 의미 기반 분류 테이블이다. 값은 production recipe import 이후 생성한다. 모든 값을 AI에 맡기지 않고 rule 기반 분류와 AI 보완을 함께 사용한다.

## Goals

- 레시피를 검색/추천이 이해하기 쉬운 축으로 분류한다.
- 재료, 단계, label에서 명확히 알 수 있는 값은 rule로 채운다.
- 애매하거나 표현 기반인 값은 AI가 보완한다.
- 안전/건강 관련 필드는 보수적으로 다룬다.
- classification이 비어도 기본 pgvector 검색은 계속 동작해야 한다.

## Flow

```text
recipes / recipe_ingredients / recipe_steps / recipe_labels
  -> recipes.classification_status = NOT_CLASSIFIED
  -> rule-based classifier
  -> AI classifier for missing or ambiguous fields
  -> confidence scorer
  -> recipe_classifications
  -> recipe_quality_scores.classification_confidence
  -> recipes.classification_status = CLASSIFIED / REVIEW_REQUIRED / FAILED
```

## Field Strategy

Rule 우선 필드:

- `main_ingredients`: `recipe_ingredients.normalized_name` 또는 `name`
- `cooking_methods`: 단계 문장의 동사/표현 매칭
- `equipment`: 단계 문장의 도구 키워드 매칭
- `category_labels`: `recipe_labels.label_type = CATEGORY`
- `allergen_keywords`: 재료 사전 기반 매칭

AI 보완 필드:

- `dish_type`
- `meal_types`
- `occasions`
- `situations`
- `taste_keywords`
- `texture_keywords`
- `diet_keywords`
- `cuisine_type`

보수적으로 다룰 필드:

- `allergen_keywords`
- `diet_keywords`
- 건강/질병과 연결될 수 있는 분류
- 비건, 글루텐프리, 무알레르기처럼 사용자의 안전 판단에 영향을 주는 주장

AI만으로 나온 안전 민감 필드는 높은 confidence를 주지 않는다. 가능하면 재료 사전, label, 관리자 입력처럼 검증 가능한 근거가 있어야 한다.

## Confidence Model

confidence는 실제 확률이 아니라 자동 사용 가능성을 나타내는 운영 점수다.

```text
confidence =
  source_base_score
  + evidence_score
  + consistency_bonus
  - conflict_penalty
  - risk_penalty
```

기본 source score:

| Source | Base |
| --- | ---: |
| `ADMIN` | 1.00 |
| `RULE` | 0.85 |
| `AI` | 0.70 |
| `MIXED` | 0.80 |

근거가 여러 곳에서 일치하면 올리고, rule과 AI가 충돌하거나 안전 민감 필드면 낮춘다.

## Field Caps

| Field | Rule/Admin Max | AI Only Max |
| --- | ---: | ---: |
| `allergen_keywords` | 0.98 | 0.50 |
| `diet_keywords` | 0.90 | 0.65 |
| `main_ingredients` | 0.95 | 0.70 |
| `cooking_methods` | 0.95 | 0.75 |
| `dish_type` | 0.95 | 0.85 |
| `taste_keywords` | 0.90 | 0.85 |
| `texture_keywords` | 0.85 | 0.80 |
| `occasions` | 0.85 | 0.80 |
| `situations` | 0.85 | 0.80 |

## Thresholds

| Confidence | Meaning | Use |
| ---: | --- | --- |
| `>= 0.85` | 자동 사용 가능 | hard filter 또는 강한 rerank signal |
| `0.60 - 0.85` | 약한 신호 | hard filter보다 rerank signal로 사용 |
| `< 0.60` | 신뢰 낮음 | 저장하지 않거나 review 대상 |

안전 민감 필드는 threshold를 더 보수적으로 적용한다.

## Search Behavior

classification은 검색 품질을 높이는 보조 인덱스다. classification이 없거나 confidence가 낮아도 검색이 실패하면 안 된다.

검색 우선순위:

```text
1. pgvector similarity
2. high-confidence hard filters
3. medium-confidence rerank signals
4. popularity/profile/history rerank
```

알레르기처럼 제외가 중요한 필터는 high-confidence 값만 hard filter로 사용한다.

## Review Required Conditions

다음 경우 classification 결과를 review 대상으로 보낸다.

- 필수 분류가 비어 있고 AI confidence도 낮음
- rule 결과와 AI 결과가 충돌함
- 안전 민감 필드가 AI 추정만으로 채워짐
- 제목, 재료, 단계, label이 서로 맞지 않음
- 중복 후보의 classification이 크게 다름

## Storage

`recipes.classification_status`는 분류 작업 상태 캐시다.

```text
NOT_CLASSIFIED
CLASSIFIED
FAILED
REVIEW_REQUIRED
```

`recipes.classified_at`은 마지막 분류 시도 또는 완료 시각이다. 운영 화면과 backfill 대상 조회는 이 상태 필드를 우선 사용한다.

`recipe_classifications.classification_source`는 최종 bundle의 주요 출처를 나타낸다.

```text
RULE
AI
ADMIN
MIXED
```

`recipe_classifications.confidence_score`는 전체 classification bundle의 aggregate confidence다. 개별 필드 confidence가 필요해지면 JSONB detail column 또는 별도 detail table을 추가한다.

`recipe_quality_scores.classification_confidence`는 운영자가 recipe 품질을 한눈에 볼 수 있는 aggregate 값으로 사용한다.
