---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 22px;
  }
  h1 { color: #2d6a4f; }
  h2 { color: #40916c; border-bottom: 2px solid #40916c; padding-bottom: 6px; }
  code { background: #f0f4f0; padding: 2px 6px; border-radius: 4px; font-size: 18px; }
  pre { background: #f0f4f0; padding: 16px; border-radius: 8px; }
  table { font-size: 18px; }
  .small { font-size: 16px; }
---

# 🥗 Naengo AI
## 채팅 기반 레시피 추천 AI 서버

냉장고 재료 · 취향 · 상황을 분석해 최적 레시피를 추천합니다

---

## 목차

1. 프로젝트 개요
2. 전체 아키텍처
3. 데이터 수집 파이프라인
4. 데이터베이스 구조
5. AI 에이전트
6. API 구조
7. 현재 구현 현황

---

## 1. 프로젝트 개요

> **"냉장고에 있는 재료로 뭐 해먹지?"** 를 AI가 해결해줍니다

**핵심 기능**

| 기능 | 설명 |
|---|---|
| 채팅 기반 추천 | 재료, 사진, 상황을 자연어로 입력 |
| pgvector 검색 | embedding 기반 의미 검색으로 실제 DB 레시피 연결 |
| 사용자 프로필 | 취향, 알레르기, 식이 제한 반영 |
| Live Research | 최신 트렌드 요리는 웹 검색으로 보강 |

**기술 스택**

`FastAPI` · `PostgreSQL + pgvector` · `PydanticAI` · `OpenAI API` · `SQLAlchemy`

---

## 2. 전체 아키텍처

```
Client (앱/웹)
  └─ FastAPI Router
       └─ Service Layer
            ├─ AgentService        ← LLM 실행, tool 호출, 스트리밍
            ├─ RecipeRetrievalService ← embedding 검색
            ├─ LiveResearchService ← 웹 검색 보강
            └─ RecipeImportService ← 데이터 수집 파이프라인
```

| 레이어 | 역할 |
|---|---|
| Router | HTTP 요청/응답, 의존성 주입 |
| Service | 유스케이스 실행, 트랜잭션 경계 |
| Agent | LLM 실행, tool 호출, 응답 스트리밍 |
| Retrieval | embedding 생성, 벡터 검색 |
| Ingestion | 외부 레시피 수집 → 정규화 → import |

---

## 3. 데이터 수집 파이프라인 개요

외부 레시피를 수집해서 정식 서비스 데이터로 승격하는 4단계 과정

```
① SCRAPE     만개의레시피 HTML 파싱 → recipe_sources 저장
     ↓
② PARSE      raw_payload → staging 테이블 (extraction)
             칼로리 AI 추정, 카테고리 자동 분류
     ↓
③ REVIEW     관리자 검수 → APPROVED / REJECTED
     ↓
④ IMPORT     staging → 정식 recipes 테이블 + embedding 생성
```

---

## 3-1. 수집 단계 (SCRAPE)

**스크래퍼**: `scripts/scrape_10000recipe.py`

```bash
uv run python scripts/scrape_10000recipe.py --limit 100 --resume
```

- 만개의레시피 목록 페이지에서 레시피 ID 수집
- HTML 파싱: 제목, 재료, 조리 단계, 이미지, 태그
- `recipe_sources` 테이블에 `collection_status = COLLECTED`로 저장
- `--resume`: 이미 수집된 레시피 자동 스킵

---

## 3-2. 파싱 단계 (PARSE)

**파서**: `scripts/parse_recipe_sources.py`

```bash
uv run python scripts/parse_recipe_sources.py --limit 300
```

| 처리 항목 | 방법 |
|---|---|
| 조리 시간 | 정규식 파싱 (`30분`, `1시간 20분`) |
| 난이도 | 시간 + 재료 수 기반 자동 추론 |
| 카테고리 | 규칙 기반 분류 (볶음/국/찌개/베이킹 등) |
| **칼로리** | **AI (gpt-5.4-mini) 1인분 추정** |

**결과 상태**: `PARSED` / `REVIEW_REQUIRED` / `INVALID` / `DUPLICATE`

---

## 3-3. Lifecycle 상태 관리

단일 `status` 대신 역할별 4개 상태 필드로 분리

| 필드 | 값 | 역할 |
|---|---|---|
| `collection_status` | COLLECTED / FAILED / SKIPPED | 수집 결과 |
| `parse_status` | NOT_PARSED / PARSED / INVALID / DUPLICATE / REVIEW_REQUIRED | 파싱 결과 |
| `review_status` | PENDING / APPROVED / REJECTED | 관리자 검수 |
| `import_status` | NOT_IMPORTED / IMPORTED / FAILED | import 결과 |

---

## 3-4. Import 단계

**import**: `scripts/import_recipe_sources.py`

```
APPROVED source
  → recipes (제목, 설명, 난이도, 칼로리, 조리시간)
  → recipe_ingredients (재료 행 단위)
  → recipe_steps (단계별 설명)
  → recipe_labels (태그, 카테고리, 팁)
  → recipe_media (대표 이미지 URL)
  → recipe_embeddings (OpenAI text-embedding-3-small)
```

embedding 생성 실패 시 레시피 import는 유지 (비차단)

---

## 4. 데이터베이스 구조

**Staging 테이블** (검수 전)

```
recipe_sources
  └─ recipe_source_extractions
       ├─ recipe_source_extracted_ingredients
       ├─ recipe_source_extracted_steps
       └─ recipe_source_extracted_labels
```

**Production 테이블** (서비스 노출)

```
recipes
  ├─ recipe_ingredients   recipe_labels      recipe_media
  ├─ recipe_steps         recipe_embeddings  recipe_stats
  └─ recipe_classifications (추천/개인화용, 추후 백필)
```

---

## 4-1. 핵심 설계 원칙

**왜 staging 테이블을 따로 두나요?**

```
raw_payload (원본 백업)
  ↓ 파싱
recipe_source_extractions (검수 후보, 수정 가능)
  ↓ 승인
recipes (서비스 노출, 불변)
```

- 원본 데이터 보존 → 언제든 재파싱 가능
- 관리자가 검수 단계에서 데이터 수정 가능
- 잘못된 데이터가 서비스에 노출되지 않음

**embedding 분리 이유**

검색 목적별로 여러 embedding을 둘 수 있도록 `recipe_embeddings` 별도 테이블

---

## 5. AI 에이전트

**현재 흐름 (구현됨)**

```
사용자 입력 → PydanticAI Agent
  → search_recipes tool
  → RecipeRetrievalService → pgvector 검색
  → SSE 스트림으로 답변 + 레시피 반환
```

**목표 흐름 (설계 완료)**

```
사용자 입력
  → IntentClassifier (요리 관련 여부 + 요청 타입 분류)
  → AgentRouter
      → RecipeSearchPlanner (검색 전략 수립)
      → LiveResearchService (최신 트렌드 필요 시)
  → 스트리밍 응답
```

---

## 5-1. Intent 분류

모든 입력을 RAG 검색에 보내지 않고 **의도 먼저 분류**

| Intent Type | 처리 방식 |
|---|---|
| `RECIPE_RECOMMENDATION` | 재료/상황 기반 검색 |
| `COOKING_TIP` | AI 직접 답변 |
| `DIET_OR_ALLERGY` | 사용자 프로필 + 검색 |
| `IMAGE_BASED_RECIPE` | 이미지 분석 + 검색 |
| `SMALLTALK` | 짧은 답변 + 요리 유도 |
| `OFF_TOPIC` | 정중한 범위 안내 |

**2-Step 분류**: 명백한 케이스 → 규칙 기반, 나머지 → LLM 분류

---

## 5-2. Live Research

내부 DB에 없거나 **최신성이 중요한** 요리 정보를 웹에서 보강

**사용하는 경우**
- 최신 유행 레시피 / SNS 트렌드 요리
- 시즌·이벤트성 메뉴
- DB 검색 결과가 부족한 경우

**사용하지 않는 경우**
- 일반 냉장고 재료 기반 추천 (DB로 충분)
- 사용자 프로필만으로 해결 가능한 질문

```
LiveResearchService
  → SearchProvider → PageFetcher → ContentExtractor
  → EvidenceSummarizer → CitationBuilder
```

---

## 6. API 구조

3개 그룹으로 분리

| 그룹 | 경로 | 대상 |
|---|---|---|
| User API | `/api/v1/users`, `/recipes`, `/chat` | 앱 사용자 |
| Admin API | `/api/v1/admin/*` | 운영자 |
| Internal API | `/api/v1/internal/*` | 배치/워커 |

**설계 원칙**
- 모든 목록 API: cursor 기반 페이지네이션
- 오래 걸리는 작업: `BackgroundTasks`로 비동기 처리
- 비싼 AI 작업: User API에서 직접 호출 금지

---

## 6-1. Admin API (검수 흐름)

```
GET    /admin/recipe-sources              목록 조회
GET    /admin/recipe-sources/{id}         상세 조회
PATCH  /admin/recipe-sources/{id}         extraction 수정
POST   /admin/recipe-sources/{id}/approve → APPROVED
POST   /admin/recipe-sources/{id}/reject  → REJECTED
POST   /admin/recipe-sources/{id}/import  → recipes 테이블로 import
```

**에러 응답 공통 형식**
```json
{
  "error": {
    "code": "RECIPE_SOURCE_NOT_FOUND",
    "message": "레시피 소스를 찾을 수 없습니다.",
    "details": {}
  }
}
```

---

## 7. 현재 구현 현황

| 영역 | 상태 |
|---|---|
| 데이터 수집 파이프라인 (scrape → parse → import) | ✅ 완료 |
| 칼로리 AI 추정 | ✅ 완료 |
| pgvector embedding 검색 | ✅ 완료 |
| Admin 검수 API | ✅ 완료 |
| AI 채팅 (기본 RAG) | ✅ 완료 |
| Intent 분류 + AgentRouter | 🔜 설계 완료, 구현 예정 |
| Live Research | 🔜 설계 완료, 구현 예정 |
| 사용자 개인화 (recipe_classifications) | 🔜 백필 예정 |
| S3 이미지 업로드 | 🔜 예정 |

**현재 DB**: 레시피 108개, embedding 108개 적재 완료

---

## 감사합니다

**Naengo AI** — 냉장고 속 재료로 오늘 저녁 메뉴 고민 끝

```
FastAPI  ·  PostgreSQL + pgvector  ·  PydanticAI  ·  OpenAI API
```
