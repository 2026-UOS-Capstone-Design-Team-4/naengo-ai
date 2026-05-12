# 01. Migration Strategy

## 현재 DDL 관리 방식

`db/schema.sql`이 DDL의 단일 소스다. `app/db/session.py`의 `init_db()`는 pgvector extension 활성화만 담당하고, `Base.metadata.create_all()`을 호출하지 않는다.

```text
db/schema.sql          DDL 정의, 테이블 생성 기준
app/models/            SQLAlchemy ORM 매핑 (DDL 역할 없음)
app/db/session.py      init_db(): CREATE EXTENSION IF NOT EXISTS vector 만 실행
```

테이블은 schema.sql을 직접 실행해서 생성한다. SQLAlchemy 모델은 이미 만들어진 테이블에 매핑되는 용도다.

## 새 테이블 추가 절차

1. `db/schema.sql`에 DDL 추가
2. `app/models/`에 SQLAlchemy 모델 추가
3. 로컬 DB 재생성 (개발 환경)

```bash
# 로컬 DB 재생성
psql -U postgres -d naengo_db -f db/schema.sql
```

schema.sql을 먼저 수정하지 않고 모델만 추가하면 둘이 어긋난다. 순서를 지킨다.

## 현재 누락된 SQLAlchemy 모델

`db/schema.sql`에는 있으나 `app/models/`에 없는 테이블:

| 테이블 | 용도 | 추가 시점 |
| --- | --- | --- |
| `recipe_sources` | 외부 데이터 수집 staging | data ingestion 구현 시 |
| `recipe_ingredients` | 레시피 재료 행 단위 | data ingestion 구현 시 |
| `recipe_steps` | 레시피 조리 단계 행 단위 | data ingestion 구현 시 |
| `recipe_image_generations` | AI 이미지 생성 후보 | AI image generation 구현 시 |

현재 `recipes` 모델은 `ingredients`와 `instructions`를 JSONB로 관리한다. `recipe_ingredients`, `recipe_steps` 테이블은 data ingestion 파이프라인을 구현할 때 함께 추가한다.

## Alembic 전환 시점

운영 데이터가 생기기 전까지는 schema.sql 기준 재생성을 허용한다. 아래 조건 중 하나가 충족되면 Alembic으로 전환한다.

- 운영 환경에 실제 사용자 데이터가 존재함
- 스테이징/운영 DB를 schema.sql로 날리기가 부담스러워짐
- 컬럼 추가/변경이 잦아져서 수동 관리가 어려워짐

### Alembic 전환 절차

```bash
uv add alembic
alembic init alembic

# alembic/env.py에서 target_metadata = Base.metadata 설정
# alembic.ini에서 sqlalchemy.url 설정

# 현재 schema.sql 상태를 기준으로 첫 migration 생성
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

전환 시점에는 `db/schema.sql`을 참고 문서로만 유지하고, Alembic migration이 DDL의 소스가 된다.

## 환경별 적용 방법

### 개발 환경

```bash
# 초기 DB 생성
psql -U postgres -d naengo_db -f db/schema.sql

# 스키마 변경 시: DB 드롭 후 재생성
psql -U postgres -c "DROP DATABASE IF EXISTS naengo_db;"
psql -U postgres -c "CREATE DATABASE naengo_db;"
psql -U postgres -d naengo_db -f db/schema.sql
```

### 스테이징 / 운영 환경 (Alembic 전환 전)

데이터가 없는 스테이징은 개발과 동일하게 재생성으로 관리한다.

운영 환경에 데이터가 생기면 schema.sql 재생성은 금지하고 Alembic migration으로 전환한다.
