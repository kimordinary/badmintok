# Band API 테스트 가이드

이 문서는 배드민톡 Band (모임/번개) API를 테스트하는 방법을 안내합니다.

## 목차

1. [기본 정보](#기본-정보)
2. [인증 방식](#인증-방식)
3. [API 엔드포인트](#api-엔드포인트)
4. [테스트 방법](#테스트-방법)
5. [오류 응답](#오류-응답)

---

## 기본 정보

### Base URL
```
http://localhost/api/band/
```

프로덕션 환경에서는 실제 도메인으로 변경하세요.

### Content-Type
모든 요청은 `application/json` 형식을 사용합니다. (이미지 업로드 제외)

### 인증
대부분의 엔드포인트는 인증이 필요하지 않지만, 생성/수정/삭제/가입/좋아요 기능은 JWT 인증이 필요합니다.

---

## 인증 방식

밴드 생성, 수정, 삭제, 가입, 게시글 작성 등 일부 기능은 **JWT (JSON Web Token)** 인증이 필요합니다.

Accounts API를 통해 로그인하여 토큰을 받아야 합니다.

### 인증 헤더 형식

```
Authorization: Bearer {access_token}
```

예시:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## API 엔드포인트

### 1. 밴드 목록

밴드 목록을 조회합니다.

**엔드포인트:** `GET /api/band/bands/`

**인증:** 불필요

**쿼리 파라미터:**
- `page` (선택): 페이지 번호 (기본값: 1)
- `page_size` (선택): 페이지당 항목 수 (기본값: 20, 최대: 100)
- `type` (선택): 밴드 타입 (`flash`, `group`, `club`)
- `region` (선택): 지역 (`all`, `capital`, `busan`, `daegu`, `gwangju`, `daejeon`, `ulsan`, `jeju`)
- `search` (선택): 검색어 (이름/설명 검색)

**성공 응답 (200 OK):**
```json
{
  "count": 100,
  "page_size": 20,
  "current_page": 1,
  "total_pages": 5,
  "results": [
    {
      "id": 1,
      "name": "밴드 이름",
      "description": "밴드 한줄 소개",
      "band_type": "flash",
      "region": "capital",
      "cover_image_url": "http://localhost/media/band/covers/...",
      "profile_image_url": "http://localhost/media/band/profiles/...",
      "is_public": true,
      "member_count": 10,
      "post_count": 5,
      "category_codes": ["flash"],
      "created_by": {
        "id": 1,
        "email": "user@example.com",
        "activity_name": "사용자명",
        "auth_provider": "email",
        "profile_image_url": "/static/images/userprofile/user.png",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "created_at": "2024-01-01T00:00:00Z",
      "is_member": false,
      "is_approved": true
    }
  ],
  "next": 2,
  "previous": null
}
```

**테스트 예시 (cURL):**
```bash
# 기본 목록
curl -X GET "http://localhost/api/band/bands/"

# 번개 타입만
curl -X GET "http://localhost/api/band/bands/?type=flash"

# 지역 필터
curl -X GET "http://localhost/api/band/bands/?region=capital"

# 검색
curl -X GET "http://localhost/api/band/bands/?search=배드민턴"

# 페이지네이션
curl -X GET "http://localhost/api/band/bands/?page=2&page_size=20"
```

---

### 2. 밴드 상세

밴드 상세 정보를 조회합니다.

**엔드포인트:** `GET /api/band/bands/<band_id>/`

**인증:** 불필요

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "name": "밴드 이름",
  "description": "밴드 한줄 소개",
  "detailed_description": "밴드 상세 설명...",
  "band_type": "flash",
  "region": "capital",
  "cover_image_url": "http://localhost/media/band/covers/...",
  "profile_image_url": "http://localhost/media/band/profiles/...",
  "is_public": true,
  "join_approval_required": false,
  "member_count": 10,
  "post_count": 5,
  "category_codes": ["flash"],
  "flash_region_detail": "서울",
  "created_by": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "auth_provider": "email",
    "profile_image_url": "/static/images/userprofile/user.png",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "is_member": false,
  "member_role": null,
  "is_approved": true,
  "categories": "flash"
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/band/bands/1/"
```

---

### 3. 밴드 생성

새로운 밴드를 생성합니다.

**엔드포인트:** `POST /api/band/bands/create/`

**인증:** 필요 (JWT)

**요청 본문:**
```json
{
  "name": "밴드 이름",
  "description": "밴드 한줄 소개",
  "detailed_description": "밴드 상세 설명",
  "band_type": "flash",
  "region": "capital",
  "is_public": true,
  "join_approval_required": false,
  "category_codes": ["flash"],
  "flash_region_detail": "서울",
  "categories": "flash"
}
```

**파일 업로드 (multipart/form-data):**
```
name: 밴드 이름
description: 밴드 한줄 소개
detailed_description: 밴드 상세 설명
band_type: flash
region: capital
is_public: true
join_approval_required: false
category_codes[]: flash
cover_image: (파일)
profile_image: (파일)
```

**성공 응답 (201 Created):**
밴드 상세 응답과 동일

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/bands/create/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "새 밴드",
    "description": "밴드 설명",
    "band_type": "flash",
    "region": "capital",
    "category_codes": ["flash"]
  }'
```

---

### 4. 밴드 수정

밴드를 수정합니다. (모임장/관리자만 가능)

**엔드포인트:** `PUT /api/band/bands/<band_id>/update/` 또는 `PATCH /api/band/bands/<band_id>/update/`

**인증:** 필요 (JWT, 모임장/관리자만)

**요청 본문:**
밴드 생성과 동일 (모든 필드 선택사항)

**성공 응답 (200 OK):**
밴드 상세 응답과 동일

**테스트 예시 (cURL):**
```bash
curl -X PUT "http://localhost/api/band/bands/1/update/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "수정된 밴드 이름",
    "description": "수정된 설명"
  }'
```

---

### 5. 밴드 가입

밴드에 가입합니다.

**엔드포인트:** `POST /api/band/bands/<band_id>/join/`

**인증:** 필요 (JWT)

**성공 응답 (201 Created):**
```json
{
  "message": "밴드 가입 신청이 완료되었습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/bands/1/join/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 6. 밴드 탈퇴

밴드에서 탈퇴합니다. (모임장은 탈퇴 불가)

**엔드포인트:** `POST /api/band/bands/<band_id>/leave/`

**인증:** 필요 (JWT)

**성공 응답 (200 OK):**
```json
{
  "message": "밴드에서 탈퇴했습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/bands/1/leave/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. 밴드 멤버 목록

밴드 멤버 목록을 조회합니다.

**엔드포인트:** `GET /api/band/bands/<band_id>/members/`

**인증:** 불필요 (공개 밴드인 경우)

**성공 응답 (200 OK):**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 1,
        "email": "user@example.com",
        "activity_name": "사용자명",
        "auth_provider": "email",
        "profile_image_url": "/static/images/userprofile/user.png",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "role": "owner",
      "status": "active",
      "joined_at": "2024-01-01T00:00:00Z",
      "last_visited_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/band/bands/1/members/"
```

---

### 8. 밴드 게시글 목록

밴드 게시글 목록을 조회합니다.

**엔드포인트:** `GET /api/band/bands/<band_id>/posts/`

**인증:** 불필요 (공개 밴드 또는 멤버인 경우)

**쿼리 파라미터:**
- `page` (선택): 페이지 번호 (기본값: 1)
- `page_size` (선택): 페이지당 항목 수 (기본값: 20, 최대: 100)

**성공 응답 (200 OK):**
```json
{
  "count": 50,
  "page_size": 20,
  "current_page": 1,
  "total_pages": 3,
  "results": [
    {
      "id": 1,
      "title": "게시글 제목",
      "content": "게시글 내용",
      "author": {
        "id": 1,
        "email": "user@example.com",
        "activity_name": "사용자명",
        "auth_provider": "email",
        "profile_image_url": "/static/images/userprofile/user.png",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "post_type": "general",
      "is_pinned": false,
      "is_notice": false,
      "view_count": 100,
      "like_count": 10,
      "comment_count": 5,
      "image_url": "http://localhost/media/band/posts/...",
      "is_liked": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "next": 2,
  "previous": null
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/band/bands/1/posts/"
```

---

### 9. 밴드 게시글 상세

밴드 게시글 상세 정보를 조회합니다.

**엔드포인트:** `GET /api/band/bands/<band_id>/posts/<post_id>/`

**인증:** 불필요 (공개 밴드 또는 멤버인 경우)

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "title": "게시글 제목",
  "content": "게시글 내용",
  "author": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "auth_provider": "email",
    "profile_image_url": "/static/images/userprofile/user.png",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "post_type": "general",
  "is_pinned": false,
  "is_notice": false,
  "view_count": 101,
  "like_count": 10,
  "comment_count": 5,
  "images": [
    {
      "id": 1,
      "image_url": "http://localhost/media/band/posts/...",
      "order_index": 0
    }
  ],
  "is_liked": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/band/bands/1/posts/1/"
```

---

### 10. 밴드 게시글 생성

밴드 게시글을 작성합니다. (멤버만 가능)

**엔드포인트:** `POST /api/band/bands/<band_id>/posts/create/`

**인증:** 필요 (JWT, 멤버만)

**요청 본문:**
```json
{
  "title": "게시글 제목",
  "content": "게시글 내용",
  "post_type": "general",
  "is_pinned": false,
  "is_notice": false
}
```

**성공 응답 (201 Created):**
게시글 상세 응답과 동일

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/bands/1/posts/create/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "새 게시글",
    "content": "게시글 내용입니다",
    "post_type": "general"
  }'
```

---

### 11. 밴드 게시글 수정

밴드 게시글을 수정합니다. (작성자 또는 관리자만 가능)

**엔드포인트:** `PUT /api/band/bands/<band_id>/posts/<post_id>/update/` 또는 `PATCH /api/band/bands/<band_id>/posts/<post_id>/update/`

**인증:** 필요 (JWT, 작성자 또는 관리자만)

**요청 본문:**
게시글 생성과 동일 (모든 필드 선택사항)

**성공 응답 (200 OK):**
게시글 상세 응답과 동일

**테스트 예시 (cURL):**
```bash
curl -X PUT "http://localhost/api/band/bands/1/posts/1/update/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "수정된 제목",
    "content": "수정된 내용"
  }'
```

---

### 12. 밴드 게시글 삭제

밴드 게시글을 삭제합니다. (작성자 또는 관리자만 가능)

**엔드포인트:** `DELETE /api/band/bands/<band_id>/posts/<post_id>/delete/`

**인증:** 필요 (JWT, 작성자 또는 관리자만)

**성공 응답 (200 OK):**
```json
{
  "message": "게시글이 삭제되었습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X DELETE "http://localhost/api/band/bands/1/posts/1/delete/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 13. 밴드 게시글 좋아요

밴드 게시글에 좋아요를 추가하거나 취소합니다.

**엔드포인트:** `POST /api/band/bands/<band_id>/posts/<post_id>/like/`

**인증:** 필요 (JWT)

**성공 응답 (200 OK):**
```json
{
  "message": "좋아요가 추가되었습니다.",
  "is_liked": true
}
```

또는

```json
{
  "message": "좋아요가 취소되었습니다.",
  "is_liked": false
}
```

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/bands/1/posts/1/like/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 14. 밴드 댓글 목록

밴드 게시글의 댓글 목록을 조회합니다.

**엔드포인트:** `GET /api/band/bands/<band_id>/posts/<post_id>/comments/`

**인증:** 불필요 (공개 밴드 또는 멤버인 경우)

**성공 응답 (200 OK):**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "content": "댓글 내용",
      "author": {
        "id": 1,
        "email": "user@example.com",
        "activity_name": "사용자명",
        "auth_provider": "email",
        "profile_image_url": "/static/images/userprofile/user.png",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "parent": null,
      "replies": [
        {
          "id": 2,
          "content": "대댓글 내용",
          "author": {...},
          "parent": 1,
          "replies": [],
          "like_count": 5,
          "is_liked": false,
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-01T00:00:00Z"
        }
      ],
      "like_count": 10,
      "is_liked": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/band/bands/1/posts/1/comments/"
```

---

### 15. 밴드 댓글 생성

밴드 게시글에 댓글을 작성합니다. (멤버만 가능)

**엔드포인트:** `POST /api/band/bands/<band_id>/posts/<post_id>/comments/create/`

**인증:** 필요 (JWT, 멤버만)

**요청 본문:**
```json
{
  "content": "댓글 내용",
  "parent": null
}
```

대댓글인 경우:
```json
{
  "content": "대댓글 내용",
  "parent": 1
}
```

**성공 응답 (201 Created):**
댓글 객체 (댓글 목록 응답의 결과 항목과 동일)

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/bands/1/posts/1/comments/create/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "댓글 내용입니다"
  }'
```

---

### 16. 밴드 댓글 수정

밴드 댓글을 수정합니다. (작성자만 가능)

**엔드포인트:** `PUT /api/band/comments/<comment_id>/` 또는 `PATCH /api/band/comments/<comment_id>/`

**인증:** 필요 (JWT, 작성자만)

**요청 본문:**
```json
{
  "content": "수정된 댓글 내용"
}
```

**성공 응답 (200 OK):**
댓글 객체

**테스트 예시 (cURL):**
```bash
curl -X PUT "http://localhost/api/band/comments/1/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "수정된 댓글"
  }'
```

---

### 17. 밴드 댓글 삭제

밴드 댓글을 삭제합니다. (작성자 또는 관리자만 가능)

**엔드포인트:** `DELETE /api/band/comments/<comment_id>/delete/`

**인증:** 필요 (JWT, 작성자 또는 관리자만)

**성공 응답 (200 OK):**
```json
{
  "message": "댓글이 삭제되었습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X DELETE "http://localhost/api/band/comments/1/delete/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 18. 밴드 댓글 좋아요

밴드 댓글에 좋아요를 추가하거나 취소합니다.

**엔드포인트:** `POST /api/band/comments/<comment_id>/like/`

**인증:** 필요 (JWT)

**성공 응답 (200 OK):**
```json
{
  "message": "좋아요가 추가되었습니다.",
  "is_liked": true
}
```

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost/api/band/comments/1/like/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 테스트 방법

### 1. Postman 사용

1. Postman을 열고 새 요청을 생성합니다.
2. HTTP 메서드와 URL을 입력합니다.
3. 인증이 필요한 경우 Headers에 `Authorization: Bearer {token}` 추가
4. Body에 JSON 데이터 입력 (필요한 경우)
5. Send 버튼 클릭

### 2. cURL 사용

터미널에서 cURL 명령어를 사용하여 API를 테스트할 수 있습니다.

### 3. Django REST Framework Browsable API

브라우저에서 다음 URL을 방문하여 Browsable API를 사용할 수 있습니다:
```
http://localhost/api/band/
```

---

## 오류 응답

### 400 Bad Request
```json
{
  "error": "요청 데이터가 올바르지 않습니다.",
  "detail": {
    "field_name": ["에러 메시지"]
  }
}
```

### 401 Unauthorized
```json
{
  "detail": "인증 정보가 제공되지 않았습니다."
}
```

### 403 Forbidden
```json
{
  "error": "밴드를 수정할 권한이 없습니다."
}
```

### 404 Not Found
```json
{
  "detail": "찾을 수 없습니다."
}
```

### 500 Internal Server Error
```json
{
  "error": "서버 오류가 발생했습니다."
}
```

---

## 주의사항

1. **인증 토큰**: 밴드 생성, 수정, 삭제, 가입, 게시글 작성 등은 JWT 토큰이 필요합니다. Accounts API를 통해 로그인하여 토큰을 받으세요.

2. **권한**: 
   - 밴드 수정/삭제: 모임장 또는 관리자만 가능
   - 게시글/댓글 수정/삭제: 작성자 또는 관리자만 가능
   - 게시글/댓글 작성: 밴드 멤버만 가능

3. **밴드 타입**: 
   - `flash`: 번개 (승인 없이 바로 생성 가능)
   - `group`: 모임 (관리자 승인 필요)
   - `club`: 동호회 (관리자 승인 필요)

4. **멤버 역할**:
   - `owner`: 모임장
   - `admin`: 관리자
   - `member`: 멤버

5. **파일 업로드**: 이미지 업로드는 `multipart/form-data` 형식을 사용합니다.

6. **페이지네이션**: 목록 API는 기본적으로 20개씩 페이지네이션됩니다. `page`와 `page_size` 파라미터로 조정 가능합니다.

---

## 추가 정보

- Accounts API 가이드: `API_GUIDE.md` 참고
- Badmintok API 가이드: `BADMINTOK_API_GUIDE.md` 참고
- Community API 가이드: `COMMUNITY_API_GUIDE.md` 참고
