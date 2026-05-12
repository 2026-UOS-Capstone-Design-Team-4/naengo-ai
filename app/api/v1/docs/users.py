from app.api.v1.docs.examples import (
    RECIPE_LIST_RESPONSE_EXAMPLE,
    USER_EXAMPLE,
    USER_PROFILE_EXAMPLE,
)

GET_ME_SUMMARY = "내 정보 조회"
GET_ME_DESCRIPTION = r"""
현재 사용자의 기본 정보를 반환합니다.

현재 인증 시스템은 임시 사용자 ID(`TEMP_USER_ID`)를 사용합니다.
"""

GET_ME_RESPONSES = {
    200: {
        "description": "사용자 정보",
        "content": {"application/json": {"example": USER_EXAMPLE}},
    },
    404: {"description": "사용자를 찾을 수 없습니다."},
}

PATCH_ME_SUMMARY = "내 정보 수정"
PATCH_ME_DESCRIPTION = r"""
현재 사용자의 기본 정보 중 수정 가능한 값을 변경합니다.

**요청 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `nickname` | string \| null | 변경할 닉네임 |
"""

PATCH_ME_RESPONSES = {
    200: {
        "description": "수정된 사용자 정보",
        "content": {"application/json": {"example": USER_EXAMPLE}},
    },
    404: {"description": "사용자를 찾을 수 없습니다."},
    409: {"description": "이미 사용 중인 닉네임입니다."},
}

GET_MY_PROFILE_SUMMARY = "내 프로필 조회"
GET_MY_PROFILE_DESCRIPTION = r"""
사용자가 직접 입력한 취향/알레르기 정보(`user_input`)를 반환합니다.
"""

GET_MY_PROFILE_RESPONSES = {
    200: {
        "description": "사용자 프로필",
        "content": {"application/json": {"example": USER_PROFILE_EXAMPLE}},
    },
    404: {"description": "프로필을 찾을 수 없습니다."},
}

PATCH_MY_PROFILE_SUMMARY = "내 프로필 수정"
PATCH_MY_PROFILE_DESCRIPTION = r"""
사용자가 직접 입력한 취향/알레르기 정보(`user_input`)를 전체 교체합니다.

- 기존 `user_input` 배열은 요청 본문의 배열로 덮어씁니다.
- 빈 배열(`[]`)을 전달하면 `user_input`이 초기화됩니다.
"""

PATCH_MY_PROFILE_RESPONSES = {
    200: {
        "description": "수정된 사용자 프로필",
        "content": {"application/json": {"example": USER_PROFILE_EXAMPLE}},
    },
    404: {"description": "프로필을 찾을 수 없습니다."},
}

GET_MY_SCRAPS_SUMMARY = "내 스크랩 레시피 조회"
GET_MY_SCRAPS_DESCRIPTION = r"""
내가 스크랩한 레시피 목록을 커서 기반 페이지네이션으로 반환합니다.

스크랩한 최신순으로 정렬합니다. 응답의 각 레시피에는 `is_scrapped = true`가 포함됩니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `cursor` | string | 없음 | 이전 응답의 `next_cursor` 값 |
| `limit` | int | `20` | 한 번에 가져올 개수. 최대 100개입니다. |
"""

GET_MY_SCRAPS_RESPONSES = {
    200: {
        "description": "스크랩한 레시피 목록",
        "content": {"application/json": {"example": RECIPE_LIST_RESPONSE_EXAMPLE}},
    }
}
