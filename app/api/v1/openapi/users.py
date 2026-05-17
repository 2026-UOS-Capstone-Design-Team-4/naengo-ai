from app.api.v1.openapi.errors import VALIDATION_ERROR_RESPONSE, error_response
from app.api.v1.openapi.examples import (
    RECIPE_LIST_RESPONSE_EXAMPLE,
    USER_EXAMPLE,
    USER_PROFILE_EXAMPLE,
)

USER_NOT_FOUND_RESPONSE = error_response(
    "사용자를 찾을 수 없습니다.",
    "RESOURCE_NOT_FOUND",
    "사용자를 찾을 수 없습니다.",
)

PROFILE_NOT_FOUND_RESPONSE = error_response(
    "프로필을 찾을 수 없습니다.",
    "RESOURCE_NOT_FOUND",
    "프로필을 찾을 수 없습니다.",
)

NICKNAME_CONFLICT_RESPONSE = error_response(
    "이미 사용 중인 닉네임입니다.",
    "CONFLICT",
    "이미 사용 중인 닉네임입니다.",
)

GET_ME_SUMMARY = "내 정보 조회"
GET_ME_DESCRIPTION = "현재 사용자의 기본 정보를 반환합니다."

GET_ME_RESPONSES = {
    200: {
        "description": "사용자 정보",
        "content": {"application/json": {"example": USER_EXAMPLE}},
    },
    404: USER_NOT_FOUND_RESPONSE,
}

PATCH_ME_SUMMARY = "내 정보 수정"
PATCH_ME_DESCRIPTION = r"""
현재 사용자의 기본 정보 중 수정 가능한 값을 변경합니다.

요청 예시:

```json
{
  "nickname": "냉장고요리왕"
}
```
"""

PATCH_ME_RESPONSES = {
    200: {
        "description": "수정된 사용자 정보",
        "content": {"application/json": {"example": USER_EXAMPLE}},
    },
    404: USER_NOT_FOUND_RESPONSE,
    409: NICKNAME_CONFLICT_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

GET_MY_PROFILE_SUMMARY = "내 프로필 조회"
GET_MY_PROFILE_DESCRIPTION = r"""
사용자가 직접 저장한 취향, 알레르기, 선호 정보를 조회합니다.

응답의 `user_input`은 최근에 추가된 문장이 먼저 오도록 반환됩니다.
"""

GET_MY_PROFILE_RESPONSES = {
    200: {
        "description": "사용자 프로필",
        "content": {"application/json": {"example": USER_PROFILE_EXAMPLE}},
    },
    404: PROFILE_NOT_FOUND_RESPONSE,
}

POST_MY_PROFILE_USER_INPUT_SUMMARY = "프로필 문장 추가"
POST_MY_PROFILE_USER_INPUT_DESCRIPTION = r"""
사용자 프로필에 저장할 문장 하나를 추가합니다.

요청 예시:

```json
{
  "text": "새우 알레르기가 있어요"
}
```

프로필 정보로 저장하기 어려운 문장이면 `422 PROFILE_INPUT_NOT_USER_INFO`를 반환합니다.
"""

POST_MY_PROFILE_USER_INPUT_RESPONSES = {
    200: {
        "description": "문장이 추가된 사용자 프로필",
        "content": {"application/json": {"example": USER_PROFILE_EXAMPLE}},
    },
    404: PROFILE_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

DELETE_MY_PROFILE_USER_INPUT_SUMMARY = "프로필 문장 삭제"
DELETE_MY_PROFILE_USER_INPUT_DESCRIPTION = r"""
사용자 프로필의 `user_input`에서 문장 하나를 삭제합니다.

요청 예시:

```json
{
  "text": "새우 알레르기가 있어요"
}
```

한 번의 요청에서는 문장 하나만 삭제할 수 있습니다.
"""

DELETE_MY_PROFILE_USER_INPUT_RESPONSES = {
    200: {
        "description": "문장이 삭제된 사용자 프로필",
        "content": {"application/json": {"example": USER_PROFILE_EXAMPLE}},
    },
    404: PROFILE_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

GET_MY_SCRAPS_SUMMARY = "내 스크랩 레시피 조회"
GET_MY_SCRAPS_DESCRIPTION = r"""
내가 스크랩한 레시피 목록을 커서 기반 페이지네이션으로 반환합니다.

응답의 각 레시피에는 `is_scrapped = true`가 포함됩니다.
"""

GET_MY_SCRAPS_RESPONSES = {
    200: {
        "description": "스크랩한 레시피 목록",
        "content": {"application/json": {"example": RECIPE_LIST_RESPONSE_EXAMPLE}},
    },
    422: VALIDATION_ERROR_RESPONSE,
}
