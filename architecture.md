# Naengo AI Architecture

## 1. 프로젝트 목적

Naengo AI는 사용자가 보유한 재료, 냉장고 사진, 취향 정보를 바탕으로 레시피를 추천하는 AI 요리 어시스턴트 API 서버다.

현재 프로젝트의 핵심 역할은 다음과 같다.

- 사용자 입력을 채팅 형태로 받고 SSE로 AI 응답을 스트리밍한다.
- 레시피 DB의 임베딩 벡터를 pgvector로 검색해 유사 레시피를 찾는다.
- AI 응답과 함께 추천된 레시피 데이터를 클라이언트에 전달한다.
- 사용자 프로필, 채팅방, 채팅 메시지, 제출 대기 레시피, 관리자 검수 기능을 제공한다.
- Scalar 기반 API 문서를 제공한다.

## 2. 현재 기술 스택

- Runtime: Python 3.13
- API: FastAPI
- AI Agent: PydanticAI
- LLM Provider: OpenAI 호환 API 게이트웨이
- Embedding: OpenAI Embedding API
- Database: PostgreSQL
- Vector Search: pgvector
- ORM: SQLAlchemy
- Docs: scalar-fastapi
- Package Manager: uv
- Lint / Format: Ruff
- Infra: Docker, Docker Compose, AWS EC2, AWS RDS, GitHub Actions

## 3. 현재 코드 구조

```text
app/
  main.py                     # FastAPI 앱 생성, CORS, Scalar docs, router 등록
  agents/
    recipe_agent.py            # PydanticAI Agent, 벡터 검색 tool 등록
    dependencies.py            # Agent 실행 중 공유되는 의존성 상태
    system_prompts.py          # Agent system prompt
  api/v1/
    api.py                     # v1 router 집합
    deps.py                    # 공통 의존성 (get_current_user_id)
    endpoints/
      chat.py                  # 채팅방, 메시지, SSE 스트리밍, AI 실행
      recipes.py               # recipe id 목록 조회
      users.py                 # 사용자 정보/프로필 조회 및 수정
      pending_recipes.py       # 사용자 제출 레시피 CRUD
      admin/
        recipes.py             # video_url 기반 레시피 조회
        pending_recipes.py     # 제출 레시피 관리자 검수
    docs/                      # API 문서 summary, description, examples
  core/
    config.py                  # Pydantic Settings 기반 환경변수 로딩
  db/
    session.py                 # SQLAlchemy engine/session, pgvector extension 초기화
  models/
    user.py                    # User, UserProfile
    recipe.py                  # Recipe, PendingRecipe, RecipeStats
    chat.py                    # ChatRoom, ChatMessage
    social.py                  # Like, Scrap
  schemas/
    chat.py
    recipe.py
    pending_recipe.py
    user.py
  services/
    chat_service.py            # 채팅방/메시지 DB 로직
    embedding_service.py       # OpenAI Embedding 호출
    recipe_retrieval_service.py # 임베딩 생성 + 벡터 검색
    pending_recipe_service.py  # 제출 레시피 비즈니스 로직 + 승인 플로우
    user_service.py            # 사용자 정보 조회/수정
```

## 4. 현재 아키텍처

라우터는 얇게 유지되고, 도메인별 서비스와 AI/RAG 계층이 분리된 구조다.

```text
Client
  |
  v
FastAPI Router (api/v1/endpoints/)
  |
  v
Service Layer (services/)
  |
  +-- ChatService / UserService / PendingRecipeService
  |
  +-- Agent (agents/recipe_agent.py)
        |
        +-- RecipeRetrievalService
              |
              +-- EmbeddingService
              +-- pgvector query
```

| 계층 | 책임 |
| --- | --- |
| Router | 요청/응답 스키마, dependency 주입, HTTP status 변환 |
| Service | 유스케이스 실행, 트랜잭션 경계, 도메인 규칙 |
| Agent | PydanticAI Agent 구성, tool 등록, 모델 실행 |
| Retrieval | 임베딩 생성, 벡터 검색 |
| Schema | 외부 API contract |
| Model | DB 테이블 매핑 |
| Config | Pydantic Settings 기반 환경변수 검증 |

## 5. 현재 설계의 문제 지점

- 인증/인가가 아직 없고 `TEMP_USER_ID = 1`에 의존한다.
- Alembic 마이그레이션 경계가 명확하지 않고, 앱 시작 시 `CREATE EXTENSION`만 수행한다.
- 에러 응답 형식, 상태값, role 값 같은 도메인 상수가 문자열로 흩어져 있다.
- 테스트가 root health check 수준이라 핵심 채팅/검색/검수 흐름을 보호하지 못한다.

## 6. 도메인 모델

### User

사용자 계정의 기본 정보다.

- `user_id`
- `email`
- `password_hash`
- `nickname`
- `role`: `USER`, `ADMIN`
- `is_active`
- `is_blocked`
- `created_at`

인증 도입 후에는 `TEMP_USER_ID` 대신 request context에서 현재 사용자를 가져와야 한다.

### UserProfile

AI 추천 개인화를 위한 사용자 취향 정보다.

- 직접 입력: `user_input`
- AI 분석 결과: `allergies`, `dietary_restrictions`, `preferred_ingredients`, `disliked_ingredients`
- 추천 조건: `preferred_categories`, `cooking_skill`, `preferred_cooking_time`, `serving_size`
- 행동 기반 정보: `frequently_used_ingredients`, `taste_keywords`, `recent_recipe_ids`

현재 API는 `user_input`만 노출한다. 이후 AI 분석 파이프라인을 붙일 때 내부 분석 필드를 채우는 별도 service가 필요하다.

### Recipe

추천 가능한 승인 레시피다.

- 기본 정보: `title`, `description`, `content`
- 재료: `ingredients`, `ingredients_raw`
- 조리: `instructions`, `servings`, `cooking_time`, `difficulty`
- 분류: `category`, `tags`
- 부가 정보: `tips`, `video_url`, `image_url`, `calories`
- 상태: `is_active`
- 작성자: `author_type` (`ADMIN` | `USER`), `author_id`
- 검색: `embedding`

### PendingRecipe

사용자가 제출하고 관리자가 검수하는 레시피다.

- 상태: `PENDING`, `APPROVED`, `REJECTED`
- 관리자 검수: `admin_note`, `reviewed_at`
- `APPROVED` 전환 시 `PendingRecipeService._promote_to_recipe()`가 `Recipe`, `RecipeStats`, `embedding`을 하나의 트랜잭션으로 생성한다.

### ChatRoom / ChatMessage

채팅 세션과 메시지 기록이다.

- `ChatRoom`: 사용자별 대화방
- `ChatMessage`: `user` 또는 `model` 메시지
- `recipe_ids`: 모델 응답에 연결된 추천 레시피 ID 목록

히스토리는 Agent message format으로 변환되어 다음 대화의 context로 들어간다.

### Like / Scrap / RecipeStats

사용자 반응과 집계 정보다.

- `Like`, `Scrap`은 사용자-레시피 unique constraint를 갖는다.
- `RecipeStats`는 레시피별 좋아요/스크랩 count를 저장한다.

현재 좋아요/스크랩 추가·취소 API는 미구현 상태다.

## 7. 주요 유스케이스

### 7.1 새 채팅방에서 레시피 추천

1. 클라이언트가 `POST /api/v1/chat/rooms`로 `prompt`, 선택적으로 `image`를 보낸다.
2. 서버가 `ChatRoom`을 생성한다.
3. SSE `room` 이벤트로 `room_id`를 보낸다.
4. Agent가 사용자 입력을 처리한다.
5. Agent tool이 재료/의도를 query로 만들어 `RecipeRetrievalService`로 벡터 검색을 수행한다.
6. 서버가 AI 응답 chunk를 SSE `message` 이벤트로 스트리밍한다.
7. 검색된 레시피가 있으면 SSE `recipes` 이벤트로 상세 데이터를 보낸다.
8. 사용자 메시지와 모델 응답을 DB에 저장한다.

### 7.2 기존 채팅방 이어가기

1. 클라이언트가 `POST /api/v1/chat/rooms/{room_id}`로 추가 prompt를 보낸다.
2. 서버가 대화방 소유자와 존재 여부를 확인한다.
3. 최근 메시지 N개를 Agent message history로 변환한다.
4. 새 채팅과 동일하게 Agent 실행, SSE 스트리밍, 메시지 저장을 수행한다.

### 7.3 레시피 제출과 관리자 검수

1. 사용자가 `POST /api/v1/pending-recipes`로 레시피를 제출한다.
2. 제출 레시피는 `PENDING` 상태로 저장된다.
3. 관리자가 `PATCH /api/v1/admin/pending-recipes/{id}`로 내용과 상태를 수정한다.
4. 상태가 변경되면 `reviewed_at`을 기록한다.
5. `APPROVED` 전환 시 필수 필드 검증 → `Recipe` 생성 → embedding 생성 → `RecipeStats` 초기화를 하나의 트랜잭션으로 처리한다.

### 7.4 사용자 프로필 수정

1. 사용자가 `PATCH /api/v1/users/me/profile`로 `user_input`을 수정한다.
2. 서버는 프로필에 직접 입력 값을 저장한다.
3. 향후 비동기 분석 job이 allergy/preference/category 등의 구조화 필드를 갱신한다.

## 8. AI/RAG 설계

### 현재 흐름

```text
User Prompt
  -> PydanticAI Agent (recipe_agent.py)
  -> search_recipes tool
  -> RecipeRetrievalService
       -> EmbeddingService (OpenAI Embedding API)
       -> pgvector cosine distance query
  -> Recipe rows
  -> Agent response stream
  -> SSE message + recipes
```

### 검색 품질 개선 방향

- query text에 사용자 재료, 싫어하는 재료, 조리 시간, 난이도 조건을 함께 반영한다.
- similarity score를 함께 반환해 cutoff 정책을 둘 수 있게 한다.
- 검색 결과가 없을 때 "DB 추천 없음"과 "AI 일반 제안"을 구분한다.
- 이미지 입력은 Agent prompt에만 넘기지 말고, 이미지 분석 결과를 검색 query에 반영하는 단계를 둔다.

## 9. SSE 이벤트 계약

현재 이벤트:

| event | data |
| --- | --- |
| `room` | `{ "room_id": number }` |
| `message` | `{ "content": string }` |
| `recipes` | `Recipe[]` |

권장 추가 이벤트:

| event | data | 목적 |
| --- | --- | --- |
| `error` | `{ "code": string, "message": string }` | 스트림 중 오류 전달 |
| `done` | `{ "message_id": number, "recipe_ids": number[] }` | 스트림 정상 종료 명시 |

## 10. 현재 API 목록

```
GET    /api/v1/chat/rooms
GET    /api/v1/chat/rooms/{room_id}
DELETE /api/v1/chat/rooms/{room_id}
POST   /api/v1/chat/rooms
POST   /api/v1/chat/rooms/{room_id}
GET    /api/v1/recipes?sort=latest|likes&cursor=...&limit=20
GET    /api/v1/recipes/{recipe_id}
POST   /api/v1/recipes/{recipe_id}/likes
DELETE /api/v1/recipes/{recipe_id}/likes
POST   /api/v1/recipes/{recipe_id}/scraps
DELETE /api/v1/recipes/{recipe_id}/scraps
GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users/me/profile
PATCH  /api/v1/users/me/profile
GET    /api/v1/users/me/scraps?cursor=...&limit=20
GET    /api/v1/pending-recipes
GET    /api/v1/pending-recipes/{pending_recipe_id}
POST   /api/v1/pending-recipes
DELETE /api/v1/pending-recipes/{pending_recipe_id}
GET    /api/v1/admin/recipes?video_url=...
PATCH  /api/v1/admin/pending-recipes/{pending_recipe_id}
```

## 11. 설정과 환경변수

현재 필요한 환경변수 (`Pydantic Settings`로 시작 시 검증):

- `DATABASE_URL`
- `API_KEY`
- `BASE_URL`
- `MODEL_NAME`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL` (기본값: `text-embedding-3-small`)

## 12. 데이터베이스와 마이그레이션

권장 원칙:

- 테이블 생성/변경은 Alembic migration으로 관리한다.
- 앱 시작 시 수행하는 DB 작업은 최소화한다.
- `CREATE EXTENSION IF NOT EXISTS vector`는 migration 또는 별도 bootstrap script로 옮긴다.

권장 인덱스:

- `recipes.is_active`
- `recipes.video_url`
- `recipes.embedding` vector index
- `chat_rooms.user_id, chat_rooms.is_active, chat_rooms.updated_at`
- `chat_messages.room_id, chat_messages.created_at`
- `pending_recipes.user_id, pending_recipes.status, pending_recipes.created_at`
- `users.email`, `users.nickname`

## 13. 테스트 전략

우선순위 높은 테스트:

- root health check
- chat room 생성 시 `room` SSE 이벤트 반환
- identity 질문 처리 시 Agent 호출 없이 고정 응답 반환
- 메시지 저장과 히스토리 로딩
- recipe vector search query 구성
- pending recipe 생성/조회/삭제
- admin pending recipe 상태 변경 시 `reviewed_at` 기록 및 Recipe 승격
- user nickname 중복 검증
- profile `user_input` 수정

테스트 구조:

```text
tests/
  api/
    test_chat.py
    test_recipes.py
    test_users.py
    test_pending_recipes.py
    test_admin_pending_recipes.py
  services/
    test_chat_service.py
    test_recipe_retrieval_service.py
    test_pending_recipe_service.py
  conftest.py
```

외부 AI API는 테스트에서 mock 처리한다.

## 14. 다음 작업 우선순위

1. 레시피 단건 조회 / 좋아요·스크랩 API 구현 (Section 16 참고)
2. 핵심 API 테스트 추가
3. 인증/인가 도입

## 15. 레시피 목록 API 설계

### 엔드포인트

```
GET /api/v1/recipes?sort=latest|likes&cursor=...&limit=20
GET /api/v1/users/me/scraps?cursor=...&limit=20
```

북마크(스크랩) 목록은 공개 레시피 목록과 성격이 다른 개인화 데이터이므로 `/users/me/scraps`로 분리한다.

### 응답 형태

```json
{
  "items": [...],
  "next_cursor": "string | null",
  "has_next": true
}
```

`next_cursor`가 `null`이면 마지막 페이지다.

### 커서 설계

#### 최신순 (`sort=latest`)

`recipe_id`는 자동 증가하므로 순서가 안정적이다.

- 커서: `recipe_id` (정수)
- 쿼리 조건: `WHERE recipe_id < cursor ORDER BY recipe_id DESC LIMIT limit`
- 다음 커서: 마지막 아이템의 `recipe_id`

#### 좋아요순 (`sort=likes`)

`likes_count`는 중복될 수 있고 실시간으로 변하므로 단일 커서로 쓸 수 없다. `(likes_count, recipe_id)` 복합 커서를 사용한다.

- 커서: `likes_count`와 `recipe_id`를 조합해 인코딩한 문자열 (예: `base64("{likes_count}:{recipe_id}")`)
- 쿼리 조건: `WHERE (likes_count, recipe_id) < (cursor_likes, cursor_id) ORDER BY likes_count DESC, recipe_id DESC LIMIT limit`
- 다음 커서: 마지막 아이템의 `(likes_count, recipe_id)` 인코딩 값

#### 북마크순 (`GET /users/me/scraps`)

`scrap_id`는 자동 증가하므로 스크랩한 순서를 안정적으로 표현한다.

- 커서: `scrap_id` (정수)
- 쿼리 조건: `WHERE user_id = :user_id AND scrap_id < cursor ORDER BY scrap_id DESC LIMIT limit`
- 다음 커서: 마지막 아이템의 `scrap_id`

### 쿼리 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `sort` | `latest` \| `likes` | `latest` | 정렬 기준 |
| `cursor` | string | 없음 (첫 페이지) | 이전 응답의 `next_cursor` 값 |
| `limit` | int | `20` | 한 번에 가져올 아이템 수 (최대 100) |

### 구현 위치

- 서비스: `app/services/recipe_service.py`
- 엔드포인트: `app/api/v1/endpoints/recipes.py`
- 스키마: `app/schemas/recipe.py` — `RecipeListResponse` 추가

## 16. 레시피 단건 조회 / 좋아요·스크랩 API 설계

### 엔드포인트

```
GET    /api/v1/recipes/{recipe_id}           # 단건 상세 조회
POST   /api/v1/recipes/{recipe_id}/likes     # 좋아요
DELETE /api/v1/recipes/{recipe_id}/likes     # 좋아요 취소
POST   /api/v1/recipes/{recipe_id}/scraps    # 스크랩
DELETE /api/v1/recipes/{recipe_id}/scraps    # 스크랩 취소
```

기존 `GET /api/v1/recipes/by-ids`는 단건 조회로 대체한다.

### 단건 조회 응답 (`RecipeDetailResponse`)

목록 아이템과 동일한 구조에 사회적 정보를 포함한다.

```json
{
  "id": 1,
  "title": "...",
  "likes_count": 42,
  "scrap_count": 15,
  "is_liked": true,
  "is_scrapped": false,
  ...
}
```

### 좋아요·스크랩 응답 (`RecipeStatsResponse`)

```json
{ "likes_count": 43, "scrap_count": 16 }
```

| 상황 | 응답 |
| --- | --- |
| 성공 | `200` + 변경된 counts |
| 레시피 없음 | `404` |
| 이미 좋아요/스크랩 | `409` |
| 없는 좋아요/스크랩 취소 요청 | `404` |

### 기존 목록 API 변경

`GET /api/v1/recipes`, `GET /api/v1/users/me/scraps` 응답에도 `is_liked`, `is_scrapped`를 추가한다.

**효율적 조회 방식**: 목록 조회 후 `recipe_ids`를 IN 쿼리로 한 번에 확인해 N+1을 방지한다.

```python
liked_ids = {
    row.recipe_id for row in
    db.query(Like.recipe_id)
    .filter(Like.user_id == user_id, Like.recipe_id.in_(recipe_ids))
    .all()
}
```

스크랩도 동일하게 처리한다.

### RecipeStats 동기화

`Recipe_Stats`의 count는 DB 트리거가 자동으로 관리하므로 서비스 레이어에서 직접 업데이트하지 않는다.

- `Likes` INSERT → `trigger_likes_count`가 `likes_count += 1`
- `Likes` DELETE → `trigger_likes_count`가 `likes_count -= 1`
- `Scraps` INSERT → `trigger_scrap_count`가 `scrap_count += 1`
- `Scraps` DELETE → `trigger_scrap_count`가 `scrap_count -= 1`

서비스는 `Likes`/`Scraps` 행 추가·삭제만 담당하고 count 갱신은 트리거에 위임한다.

### 스키마 변경

- `RecipeListItemResponse`: `is_liked: bool = False`, `is_scrapped: bool = False` 추가
- `RecipeDetailResponse`: `RecipeListItemResponse`를 재사용 (동일 구조)
- `RecipeStatsResponse`: `likes_count`, `scrap_count` 신규 추가

### 구현 위치

- 서비스: `app/services/recipe_service.py` — `get_recipe`, `like`, `unlike`, `scrap`, `unscrap` 메서드 추가
- 엔드포인트: `app/api/v1/endpoints/recipes.py` — 단건 조회 및 social 라우터 추가, `by-ids` 제거
- 스키마: `app/schemas/recipe.py` — `is_liked`, `is_scrapped`, `RecipeStatsResponse` 추가
- 문서: `app/api/v1/docs/recipes.py` — 단건 조회 및 social API 문서 추가

## 17. 코드 이관 기준

- 한 PR 또는 커밋은 하나의 기능 단위만 바꾼다.
- 라우터의 public contract가 바뀌는 경우 API 문서와 테스트를 같이 수정한다.
- DB schema 변경은 migration과 함께 진행한다.
- AI 응답 품질을 바꾸는 변경은 prompt/tool/retrieval 중 어느 영역의 변경인지 명확히 기록한다.
- `uv.lock` 변경이 발생하면 관련 의존성 변경과 함께 커밋한다.
- 외부 API 호출은 테스트에서 mock 가능해야 한다.
