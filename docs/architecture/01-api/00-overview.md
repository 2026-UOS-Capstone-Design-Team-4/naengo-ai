# 00. API Overview

Naengo AI API는 사용자 기능, 관리자 기능, 내부 작업을 분리해서 설계합니다. 현재 구현된 API와 목표 contract가 섞일 수 있으므로, 각 문서에서 current scope와 deferred scope를 명확히 나눕니다.

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
| User API | 모바일/웹 사용자 앱 | 조회, 추천, 채팅, 좋아요, 스크랩, 사용자 제출 |
| Admin API | 운영자 관리 화면 | 서비스 데이터 관리, pending recipe 관리, 향후 source 검수와 이미지 생성 |
| Internal API | worker, batch, scheduler | 스크래핑, import, embedding, 이미지 처리, cache refresh |

## Design Principles

- 사용자 API는 응답 안정성과 backward compatibility를 우선합니다.
- 관리자 API는 운영 action과 검토 데이터를 명확히 드러냅니다.
- 내부 API는 일반 client에 공개하지 않습니다.
- 오래 걸리는 작업은 가능한 job으로 분리하고 API는 job id를 반환합니다.
- 비용이 드는 AI 작업은 User API에서 직접 트리거하지 않습니다.
- list API는 cursor pagination을 기본으로 합니다.
- 모든 변경 API는 권한과 audit 가능성을 고려합니다.

## Resource Naming

resource 중심 URL을 기본으로 사용합니다.

```text
GET    /recipes
GET    /recipes/{recipe_id}
POST   /recipes/{recipe_id}/likes
DELETE /recipes/{recipe_id}/likes

GET    /admin/recipes
PATCH  /admin/recipes/{recipe_id}

POST   /internal/jobs/embedding-backfill
```

action이 필요한 경우에는 하위 action path를 사용합니다.

```text
POST /admin/recipe-sources/{source_id}/approve
POST /admin/recipes/{recipe_id}/image-generations/{generation_id}/select
```

image generation admin API는 예정 scope입니다. source 검수 API(`/admin/recipe-sources/*`)는 구현되어 있습니다.

## Pagination

List API는 cursor 기반 pagination을 기본으로 합니다.

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

공통 에러 응답은 다음 형식을 사용합니다.

```json
{
  "error": {
    "code": "RECIPE_NOT_FOUND",
    "message": "레시피를 찾을 수 없습니다.",
    "details": {}
  }
}
```

HTTP status와 `error.code`를 함께 사용합니다. 프론트엔드는 사용자 노출 문구를 `message` 또는 클라이언트 localization 정책으로 처리합니다.

## Documents

- [01. User API](01-user-api.md)
- [02. Admin API](02-admin-api.md)
- [03. Internal API](03-internal-api.md)
- [04. Auth and Permissions](04-auth-and-permissions.md)
- [05. Error Response](05-error-response.md)
