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

## 3. 현재 코드 구조 요약

```text
app/
  main.py                     # FastAPI 앱 생성, CORS, Scalar docs, router 등록
  agents/
    recipe_agent.py            # PydanticAI Agent, embedding 생성, 벡터 검색 tool
    dependencies.py            # Agent 실행 중 공유되는 의존성 상태
    system_prompts.py          # Agent system prompt
  api/v1/
    api.py                     # v1 router 집합
    endpoints/
      chat.py                  # 채팅방, 메시지, SSE 스트리밍, AI 실행
      recipes.py               # recipe id 목록 조회
      users.py                 # 임시 사용자 기반 내 정보/프로필 조회 및 수정
      pending_recipes.py       # 사용자 제출 레시피 CRUD 일부
    admin/
      recipes.py               # video_url 기반 레시피 조회
      pending_recipes.py       # 제출 레시피 관리자 검수
    docs/                      # API 문서 summary, description, examples
  core/
    config.py                  # 환경변수 로딩, 임시 사용자 ID
  crud/
    recipe.py                  # 벡터 기반 레시피 검색
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
    api_client.py              # 현재는 placeholder
```

## 4. 현재 설계의 문제 지점

현재 구조는 MVP로는 이해하기 쉽지만, 기능이 늘어나면 다음 문제가 커진다.

- 라우터가 HTTP 처리, DB 조회/저장, 비즈니스 규칙, AI 실행을 동시에 담당한다.
- `chat.py`가 채팅방 관리, 히스토리 변환, Agent 실행, SSE 이벤트 생성, 메시지 저장을 모두 포함한다.
- `recipe_agent.py`의 tool이 embedding client, DB session, CRUD 호출을 직접 생성한다.
- 인증/인가가 아직 없고 `TEMP_USER_ID = 1`에 의존한다.
- 환경변수 누락 검증이 없어 앱 시작 후 런타임 오류로 이어질 수 있다.
- Alembic 마이그레이션 경계가 명확하지 않고, 앱 시작 시 `CREATE EXTENSION`만 수행한다.
- 에러 응답 형식, 상태값, role 값 같은 도메인 상수가 문자열로 흩어져 있다.
- 한글 문서/주석이 터미널에서 깨져 보여 협업 시 혼란을 만들 수 있다.
- 테스트가 root health check 수준이라 핵심 채팅/검색/검수 흐름을 보호하지 못한다.

## 5. 목표 아키텍처

목표는 라우터를 얇게 만들고, 도메인별 서비스와 AI/RAG 계층을 분리하는 것이다.

```text
Client
  |
  v
FastAPI Router
  |
  v
Application Service
  |
  +-- Domain Repository / CRUD
  |
  +-- Agent Service
        |
        +-- Prompt / Tool Definition
        +-- Retrieval Service
              |
              +-- Embedding Client
              +-- Recipe Vector Repository
```

권장 계층 책임은 다음과 같다.

| 계층 | 책임 |
| --- | --- |
| Router | 요청/응답 스키마, dependency 주입, HTTP status 변환 |
| Service | 유스케이스 실행, 트랜잭션 경계, 도메인 규칙 |
| Repository / CRUD | SQLAlchemy query, persistence 세부 구현 |
| Agent | PydanticAI Agent 구성, tool 등록, 모델 실행 |
| Retrieval | 임베딩 생성, 벡터 검색, 검색 결과 정규화 |
| Schema | 외부 API contract |
| Model | DB 테이블 매핑 |
| Config | 환경변수 검증과 앱 설정 |

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

향후 인증 도입 후에는 `TEMP_USER_ID` 대신 request context에서 현재 사용자를 가져와야 한다.

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
- 작성자: `author_type`, `author_id`
- 검색: `embedding`

`embedding`은 레시피 본문/재료/태그 등을 조합한 검색용 텍스트에서 생성하는 것이 좋다.

### PendingRecipe

사용자가 제출하고 관리자가 검수하는 레시피다.

- 상태: `PENDING`, `APPROVED`, `REJECTED`
- 관리자 검수: `admin_note`, `reviewed_at`
- 승인 시 `Recipe`로 승격될 수 있다.

현재는 상태만 바꾸며, `APPROVED`가 실제 `Recipe` 생성까지 이어지는 정책은 아직 분리되어 있지 않다.

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

현재 API에는 social 기능이 충분히 노출되어 있지 않다.

## 7. 주요 유스케이스

### 7.1 새 채팅방에서 레시피 추천

1. 클라이언트가 `POST /api/v1/chat/rooms`로 `prompt`, 선택적으로 `image`를 보낸다.
2. 서버가 `ChatRoom`을 생성한다.
3. SSE `room` 이벤트로 `room_id`를 보낸다.
4. Agent가 사용자 입력을 처리한다.
5. Agent tool이 재료/의도를 query로 만들어 레시피 벡터 검색을 수행한다.
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
5. 향후 `APPROVED` 전환 시 `Recipe` 생성, embedding 생성, stats 초기화를 하나의 트랜잭션으로 처리한다.

### 7.4 사용자 프로필 수정

1. 사용자가 `PATCH /api/v1/users/me/profile`로 `user_input`을 수정한다.
2. 서버는 프로필에 직접 입력 값을 저장한다.
3. 향후 비동기 분석 job이 allergy/preference/category 등의 구조화 필드를 갱신한다.

## 8. AI/RAG 설계

### 현재 흐름

```text
User Prompt
  -> PydanticAI Agent
  -> search_recipes tool
  -> OpenAI Embedding API
  -> pgvector cosine distance query
  -> Recipe rows
  -> Agent response stream
  -> SSE message + recipes
```

### 개선 목표

Agent tool 내부에서 DB session과 embedding client를 직접 생성하지 않고 다음처럼 나눈다.

```text
RecipeAgentService
  -> RecipeRetrievalService
       -> EmbeddingService
       -> RecipeRepository
```

권장 모듈:

```text
app/
  services/
    chat_service.py
    recipe_service.py
    pending_recipe_service.py
    user_service.py
  ai/
    recipe_agent.py
    prompts.py
    tools.py
  retrieval/
    embedding_service.py
    recipe_retrieval_service.py
  repositories/
    recipe_repository.py
    chat_repository.py
    user_repository.py
    pending_recipe_repository.py
```

`crud/`를 유지한다면 `repositories/` 대신 기존 `crud/`를 확장해도 된다. 중요한 것은 SQL 쿼리와 유스케이스 로직을 분리하는 것이다.

### 검색 품질 개선 방향

- query text에 사용자 재료, 싫어하는 재료, 조리 시간, 난이도 조건을 함께 반영한다.
- 레시피 embedding 생성 기준을 문서화한다.
- `Recipe.embedding IS NOT NULL` 조건을 추가한다.
- similarity score를 함께 반환해 cutoff 정책을 둘 수 있게 한다.
- 검색 결과가 없을 때 “DB 추천 없음”과 “AI 일반 제안”을 구분한다.
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
| `metadata` | `{ "model": string, "room_id": number }` | 클라이언트 디버깅/표시 |

권장 규칙:

- `message`는 순수 텍스트 delta만 보낸다.
- 최종 저장 결과나 추천 ID는 `done`에서 한 번 더 알려준다.
- `recipes`는 중복 제거된 추천 레시피 상세만 보낸다.
- 스트림 중 예외가 발생하면 가능한 경우 `error` 이벤트를 보내고 DB에는 실패 상태를 남긴다.

## 10. API 설계 방향

현재 public API:

- `GET /api/v1/chat/rooms`
- `GET /api/v1/chat/rooms/{room_id}`
- `DELETE /api/v1/chat/rooms/{room_id}`
- `POST /api/v1/chat/rooms`
- `POST /api/v1/chat/rooms/{room_id}`
- `GET /api/v1/recipes?ids=1&ids=2`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `GET /api/v1/users/me/profile`
- `PATCH /api/v1/users/me/profile`
- `GET /api/v1/pending-recipes`
- `GET /api/v1/pending-recipes/{pending_recipe_id}`
- `POST /api/v1/pending-recipes`
- `DELETE /api/v1/pending-recipes/{pending_recipe_id}`
- `GET /api/v1/admin/recipes?video_url=...`
- `PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}`

개선 방향:

- 인증 도입 전까지는 `TEMP_USER_ID`를 하나의 dependency로 감싸 교체 지점을 만든다.
- admin router에는 role check dependency를 붙일 수 있게 구조를 준비한다.
- `GET /recipes?ids=...` 외에 상세 조회, 검색, 인기순 조회 등 read API를 분리한다.
- pending recipe 승인 시 실제 recipe 생성 API 또는 service action을 명확히 둔다.
- social API가 필요하면 `POST /recipes/{id}/likes`, `DELETE /recipes/{id}/likes`, `POST /recipes/{id}/scraps` 등으로 노출한다.

## 11. 설정과 환경변수

현재 필요한 환경변수:

- `DATABASE_URL`
- `API_KEY`
- `BASE_URL`
- `MODEL_NAME`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`

개선 방향:

- Pydantic Settings로 config를 변경한다.
- 필수 값 누락 시 앱 시작 단계에서 명확한 오류를 낸다.
- `EMBEDDING_MODEL`을 코드에서 하드코딩하지 않고 설정 값을 사용한다.
- 운영/개발 CORS origin을 분리한다.
- 민감 정보가 저장소에 들어가지 않도록 `.env`와 key 파일 관리를 점검한다.

## 12. 데이터베이스와 마이그레이션

권장 원칙:

- 테이블 생성/변경은 Alembic migration으로 관리한다.
- 앱 시작 시 수행하는 DB 작업은 최소화한다.
- `CREATE EXTENSION IF NOT EXISTS vector`는 migration 또는 별도 bootstrap script로 옮긴다.
- vector index 정책을 명시한다.

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
- admin pending recipe 상태 변경 시 `reviewed_at` 기록
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
  conftest.py
```

외부 AI API는 테스트에서 mock 처리한다.

## 14. 리팩토링 로드맵

### Phase 1. 안전한 기반 정리

- 한글 인코딩과 문서 출력 환경을 정리한다.
- `TEMP_USER_ID` 접근을 dependency 함수로 감싼다.
- config를 Pydantic Settings로 전환한다.
- 하드코딩된 embedding model을 설정 값으로 교체한다.
- route handler의 중복 DB 조회 패턴을 작은 helper/service로 뺀다.

### Phase 2. Chat 흐름 분리

- `ChatService`를 만든다.
- 채팅방 생성, 방 조회, 삭제, 히스토리 로딩, 메시지 저장을 service/repository로 이동한다.
- SSE 이벤트 생성 로직을 `ChatStreamService` 또는 generator helper로 분리한다.
- Agent 실행 결과와 추천 레시피 결과를 명확한 DTO로 반환한다.

### Phase 3. Retrieval/Agent 분리

- `EmbeddingService`를 만든다.
- `RecipeRetrievalService`를 만든다.
- Agent tool은 retrieval service를 호출하도록 바꾼다.
- DB session 생성 위치를 FastAPI dependency 또는 service boundary로 통일한다.
- 검색 결과에 score와 cutoff 정책을 도입한다.

### Phase 4. PendingRecipe 승인 플로우 완성

- 승인 상태 변경과 Recipe 생성 정책을 분리한다.
- `APPROVED` 전환 시 `Recipe`, `RecipeStats`, `embedding` 생성을 하나의 트랜잭션으로 묶는다.
- 거절 사유와 수정 이력을 남길지 결정한다.

### Phase 5. 인증/인가 도입

- 현재 사용자 dependency를 실제 인증 기반으로 교체한다.
- admin router에 role guard를 추가한다.
- `is_active`, `is_blocked` 정책을 모든 사용자 API에 반영한다.

### Phase 6. 테스트와 운영 안정화

- 주요 API 테스트를 추가한다.
- AI 외부 호출 mock fixture를 만든다.
- DB migration을 정리한다.
- 로그 메시지와 에러 응답 포맷을 표준화한다.
- CORS, secret, deployment env를 운영 기준으로 정리한다.

## 15. 코드 이관 기준

설계 문서를 코드로 옮길 때는 다음 기준을 지킨다.

- 한 PR 또는 커밋은 하나의 기능 단위만 바꾼다.
- 라우터의 public contract가 바뀌는 경우 API 문서와 테스트를 같이 수정한다.
- DB schema 변경은 migration과 함께 진행한다.
- AI 응답 품질을 바꾸는 변경은 prompt/tool/retrieval 중 어느 영역의 변경인지 명확히 기록한다.
- `uv.lock` 변경이 발생하면 관련 의존성 변경과 함께 커밋한다.
- 외부 API 호출은 테스트에서 mock 가능해야 한다.

## 16. 먼저 적용하면 좋은 구체 작업

가장 먼저 추천하는 작업 순서는 다음과 같다.

1. `get_current_user_id()` dependency 추가 후 `TEMP_USER_ID` 직접 참조 제거
2. Pydantic Settings 기반 config 도입
3. `ChatService`로 채팅방/메시지 DB 로직 이동
4. `EmbeddingService`, `RecipeRetrievalService` 추가
5. `recipe_agent` tool에서 DB session 직접 생성 제거
6. pending recipe 승인 시 Recipe 승격 플로우 설계 및 구현
7. 핵심 API 테스트 추가

이 순서가 좋은 이유는 API 응답 형태를 크게 흔들지 않으면서 내부 경계를 먼저 세울 수 있기 때문이다.
