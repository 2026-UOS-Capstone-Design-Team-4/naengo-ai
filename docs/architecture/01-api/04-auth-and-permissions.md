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
| `POST /user-recipes` | 불가 | 허용 | 허용 | 불가 |
| `/admin/*` | 불가 | 불가 | 허용 | 제한 |
| `/internal/*` | 불가 | 불가 | 불가 | 허용 |

로그인은 외부 백엔드에서 처리하고, Naengo AI는 access token을 검증해 사용자
인증과 권한 판단을 수행한다. refresh token은 이 서비스에서 다루지 않는다.

## Access Token

클라이언트는 인증이 필요한 API에 다음 헤더를 보낸다.

```http
Authorization: Bearer <access_token>
```

JWT 정책:

- 알고리즘: `HS512` (`HMAC-SHA512`)
- 서명 키: `JWT_SECRET_KEY`
- 필수 클레임: `sub`, `role`, `iat`, `exp`

| Claim | Type | Meaning |
| --- | --- | --- |
| `sub` | string | `users.user_id` 문자열. 인증 시 `int(payload["sub"])`로 변환한다. |
| `role` | string | `USER` 또는 `ADMIN` |
| `iat` | int | epoch seconds 발급 시각 |
| `exp` | int | epoch seconds 만료 시각 |

검증 순서:

1. `Authorization` 헤더의 Bearer token을 파싱한다.
2. `JWT_SECRET_KEY`와 `HS512` 알고리즘으로 서명과 만료 시간을 검증한다.
3. `sub`를 `int`로 변환해 `users.user_id`를 조회한다.
4. 사용자가 없거나 비활성 상태면 `401`을 반환한다.
5. 차단된 사용자는 `403`을 반환한다.
6. token의 `role`과 DB의 `users.role`이 다르면 `403`을 반환한다.
7. Admin API는 `require_admin`에서 DB role이 `ADMIN`인지 추가 확인한다.

Internal API는 사용자 access token이 아니라 `X-Internal-Secret` 기반 인증을 사용한다.

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
- user recipe approve/reject
- internal retry job
