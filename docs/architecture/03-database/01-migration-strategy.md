# 01. Migration Strategy

## 현재 DDL 관리 방식

`db/schema.sql`이 DDL의 단일 소스다. SQLAlchemy 모델은 이미 만들어진 테이블에 매핑되는 용도이며 `create_all()`을 호출하지 않는다.

schema.sql을 먼저 수정하고, 이후 SQLAlchemy 모델을 맞춘다. 순서를 지키지 않으면 DB와 모델이 어긋난다.

## 개발 환경

```bash
# 초기 DB 생성
psql -U postgres -d naengo_db -f db/schema.sql

# 스키마 변경 시: DB 드롭 후 재생성
psql -U postgres -c "DROP DATABASE IF EXISTS naengo_db;"
psql -U postgres -c "CREATE DATABASE naengo_db;"
psql -U postgres -d naengo_db -f db/schema.sql
```

## 운영 환경

운영 데이터가 생기기 전까지는 schema.sql 기준 재생성을 허용한다. 다음 조건 중 하나가 충족되면 Alembic으로 전환한다.

- 운영 환경에 실제 사용자 데이터가 존재함
- schema.sql 재생성이 부담스러워짐
- 컬럼 추가/변경이 잦아져서 수동 관리가 어려워짐

Alembic 전환 시 `db/schema.sql`은 참고 문서로 유지하고, migration 파일이 DDL의 소스가 된다.
