# 00. API Overview

Naengo AI API는 사용자 앱, 관리자 도구, 내부 작업자를 분리해서 설계합니다. 현재 구현된 API는 초기 버전으로 보고, 아래 구조를 목표 API contract로 둡니다.

## API Groups

```text
/api/v1/users/*
/api/v1/recipes/*
/api/v1/chat/*
/api/v1/pending-recipes/*

/api/v1/admin/*

/api/v1/internal/*
```

## Boundaries

| Group | Consumer | Responsibility |
| --- | --- | --- |
| User API | 모바일/웹 앱 사용자 | 조회, 추천, 채팅, 좋아요, 스크랩, 사용자 제출 |
| Admin API | 운영자/관리자 화면 | 검수, 승인, import, 재처리, AI 이미지 생성 |
| Internal API | worker, batch, scheduler | 스크래핑, embedding, 이미지 처리, 백필 |

## Design Principles

- 사용자 API는 응답 안정성을 우선합니다.
- 관리자 API는 운영 액션과 검수 데이터를 명확하게 드러냅니다.
- 내부 API는 외부 클라이언트에 공개하지 않습니다.
- 오래 걸리는 작업은 가능하면 job으로 분리하고 API는 job id를 반환합니다.
- 비싼 AI 작업은 User API에서 직접 호출하지 않습니다.
- 모든 list API는 cursor pagination을 기본으로 합니다.
- 모든 변경 API는 권한과 audit 가능성을 고려합니다.

## Resource Naming

리소스 중심 URL을 기본으로 사용합니다.

```text
GET    /recipes
GET    /recipes/{recipe_id}
POST   /recipes/{recipe_id}/likes
DELETE /recipes/{recipe_id}/likes

GET    /admin/recipe-sources
POST   /admin/recipe-sources/{source_id}/import

POST   /internal/jobs/embedding-backfill
```

액션이 필요한 경우에는 하위 action path를 사용합니다.

```text
POST /admin/recipe-sources/{source_id}/approve
POST /admin/recipes/{recipe_id}/image-generations/{generation_id}/select
```

## Pagination

List API는 cursor 기반 페이지네이션을 기본으로 합니다.

```json
{
  "items": [],
  "next_cursor": "eyJpZCI6MTAwfQ==",
  "has_more": true
}
```

기본 query:

- `limit`: 기본 20, 최대 100
- `cursor`: 다음 페이지 cursor
- `sort`: 필요한 경우 명시

## Error Response

공통 에러 응답은 다음 형태를 사용합니다.

```json
{
  "error": {
    "code": "RECIPE_NOT_FOUND",
    "message": "레시피를 찾을 수 없습니다.",
    "details": {}
  }
}
```

HTTP status와 `error.code`를 함께 사용합니다. 프론트엔드는 사용자 노출 문구를 `message` 또는 클라이언트 로컬라이징 정책으로 처리합니다.

## Documents

- [01. User API](01-user-api.md)
- [02. Admin API](02-admin-api.md)
- [03. Internal API](03-internal-api.md)
- [04. Auth and Permissions](04-auth-and-permissions.md)
- [05. Error Response](05-error-response.md)
