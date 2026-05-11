from app.api.v1.docs.examples import USER_EXAMPLE, USER_PROFILE_EXAMPLE

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

GET_ME_SUMMARY = "내 정보 조회"
GET_ME_DESCRIPTION = r"""
현재 사용자의 기본 정보를 반환합니다.

**응답 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `user_id` | int | 사용자 ID |
| `email` | string | 이메일 |
| `nickname` | string | 닉네임 |
| `role` | string | 권한 (`USER` / `ADMIN`) |
| `is_active` | bool | 계정 활성화 여부 |
| `is_blocked` | bool | 계정 차단 여부 |
| `created_at` | datetime | 가입 시각 |
"""

GET_ME_RESPONSES = {
    200: {
        "description": "사용자 정보",
        "content": {"application/json": {"example": USER_EXAMPLE}},
    },
    404: {"description": "사용자를 찾을 수 없습니다."},
}

GET_MY_PROFILE_SUMMARY = "내 프로필 조회"
GET_MY_PROFILE_DESCRIPTION = r"""
사용자가 직접 입력한 취향/알레르기 정보(`user_input`)를 반환합니다.

**응답 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `user_input` | string[] | 사용자가 직접 입력한 취향/알레르기 문장 목록 |
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

**요청 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `user_input` | string[] | 새 취향/알레르기 문장 목록 |
"""

PATCH_MY_PROFILE_RESPONSES = {
    200: {
        "description": "수정된 사용자 프로필",
        "content": {"application/json": {"example": USER_PROFILE_EXAMPLE}},
    },
    404: {"description": "프로필을 찾을 수 없습니다."},
}
