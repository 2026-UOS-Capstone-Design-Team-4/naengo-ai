# 04. Auth and Permissions

로그인은 나중에 고도화하지만, API 설계는 권한 경계를 먼저 정해둡니다.

## Roles

| Role | Description |
| --- | --- |
| `GUEST` | 비로그인 사용자 |
| `USER` | 일반 사용자 |
| `ADMIN` | 운영 관리자 |
| `SYSTEM` | 내부 worker 또는 scheduler |

## Access Matrix

| API Group | GUEST | USER | ADMIN | SYSTEM |
| --- | --- | --- | --- | --- |
| `GET /recipes` | 허용 가능 | 허용 | 허용 | 제한 |
| `POST /recipes/{id}/likes` | 불가 | 허용 | 허용 | 불가 |
| `POST /pending-recipes` | 불가 | 허용 | 허용 | 불가 |
| `/admin/*` | 불가 | 불가 | 허용 | 제한 |
| `/internal/*` | 불가 | 불가 | 불가 | 허용 |

초기에는 `TEMP_USER_ID`를 사용할 수 있지만, 다음 전환을 염두에 둡니다.

- access token 기반 사용자 인증
- role 기반 admin guard
- internal API secret 또는 private network 제한

## Dependency Direction

```text
get_current_user
  -> User API

require_admin
  -> Admin API

require_system
  -> Internal API
```

## Audit

변경 API는 누가, 언제, 무엇을 바꿨는지 추적할 수 있어야 합니다.

초기 audit 대상:

- admin recipe source approve/reject/import
- admin recipe patch
- AI image generation request/select/reject
- pending recipe approve/reject
- internal retry job
