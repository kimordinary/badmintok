# Community API 테스트 가이드

이 문서는 배드민톡 Community (동호인톡) API를 테스트하는 방법을 안내합니다.

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
http://localhost/api/community/
```

프로덕션 환경에서는 실제 도메인으로 변경하세요.

### Content-Type
모든 요청은 `application/json` 형식을 사용합니다. (이미지 업로드 제외)

### 인증
대부분의 엔드포인트는 인증이 필요하지 않지만, 생성/수정/삭제/좋아요 기능은 JWT 인증이 필요합니다.

---

## 인증 방식

게시물 생성, 수정, 삭제, 좋아요 등 일부 기능은 **JWT (JSON Web Token)** 인증이 필요합니다.

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

### 1. 게시물 목록

동호인톡 게시물 목록을 조회합니다.

**엔드포인트:** `GET /api/community/posts/`

**인증:** 불필요

**쿼리 파라미터:**
- `page` (선택): 페이지 번호 (기본값: 1)
- `page_size` (선택): 페이지당 항목 수 (기본값: 10, 최대: 100)
- `tab` (선택): 탭 필터 (`hot`, `reviews`, 또는 카테고리 slug)
- `category` (선택): 카테고리 slug
- `search` (선택): 검색어 (제목/내용 검색)

**성공 응답 (200 OK):**
```json
{
  "count": 100,
  "page_size": 10,
  "current_page": 1,
  "total_pages": 10,
  "results": [
    {
      "id": 1,
      "title": "게시글 제목",
      "slug": "post-slug",
      "category": {
        "id": 1,
        "name": "카테고리명",
        "slug": "category-slug"
      },
      "categories": [
        {
          "id": 1,
          "name": "카테고리명",
          "slug": "category-slug",
          "parent": null
        }
      ],
      "author": {
        "id": 1,
        "email": "user@example.com",
        "activity_name": "사용자명",
        "auth_provider": "email",
        "profile_image_url": "/static/images/userprofile/user.png",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "thumbnail_url": "http://localhost:8000/media/community/thumbnails/...",
      "content_image_url": "http://localhost:8000/media/community/post_images/...",
      "excerpt": "게시글 요약 내용...",
      "view_count": 100,
      "like_count": 50,
      "comment_count": 20,
      "is_pinned": false,
      "is_liked": false,
      "created_at": "2024-01-01T00:00:00Z",
      "published_at": "2024-01-01T00:00:00Z"
    }
  ],
  "next": 2,
  "previous": null
}
```

**테스트 예시 (cURL):**
```bash
# 기본 목록
curl -X GET "http://localhost:8000/api/community/posts/"

# Hot 탭
curl -X GET "http://localhost:8000/api/community/posts/?tab=hot"

# 리뷰 탭
curl -X GET "http://localhost:8000/api/community/posts/?tab=reviews"

# 카테고리 필터
curl -X GET "http://localhost:8000/api/community/posts/?category=community-racket"

# 검색
curl -X GET "http://localhost:8000/api/community/posts/?search=라켓"

# 페이지네이션
curl -X GET "http://localhost:8000/api/community/posts/?page=2&page_size=20"
```

---

### 2. 게시물 상세

동호인톡 게시물 상세 정보를 조회합니다.

**엔드포인트:** `GET /api/community/posts/<slug>/`

**인증:** 불필요

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "title": "게시글 제목",
  "slug": "post-slug",
  "content": "<p>게시글 내용...</p>",
  "category": {
    "id": 1,
    "name": "카테고리명",
    "slug": "category-slug",
    "parent": null
  },
  "categories": [...],
  "author": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "auth_provider": "email",
    "profile_image_url": "/static/images/userprofile/user.png",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "thumbnail_url": "http://localhost/media/...",
  "thumbnail_alt": "썸네일 설명",
  "images": [
    {
      "id": 1,
      "image_url": "http://localhost:8000/media/...",
      "order": 0
    }
  ],
  "view_count": 101,
  "like_count": 50,
  "comment_count": 20,
  "is_pinned": false,
  "is_liked": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "published_at": "2024-01-01T00:00:00Z",
  "source": "community"
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost:8000/api/community/posts/post-slug/"
```

---

### 3. 게시물 생성

새로운 동호인톡 게시물을 생성합니다.

**엔드포인트:** `POST /api/community/posts/create/`

**인증:** 필요 (JWT)

**요청 본문:**
```json
{
  "title": "게시글 제목",
  "content": "<p>게시글 내용...</p>",
  "category_id": 1,
  "category_ids": [1, 2],
  "slug": "post-slug",
  "thumbnail_alt": "썸네일 설명",
  "published_at": "2024-01-01T00:00:00Z",
  "is_pinned": false,
  "is_draft": false
}
```

**파일 업로드 (multipart/form-data):**
```
title: 게시글 제목
content: <p>게시글 내용...</p>
category_id: 1
category_ids[]: 1
category_ids[]: 2
thumbnail: (파일)
```

**성공 응답 (201 Created):**
게시물 상세 응답과 동일

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost:8000/api/community/posts/create/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "새 게시글",
    "content": "<p>내용입니다</p>",
    "category_id": 1
  }'
```

---

### 4. 게시물 수정

동호인톡 게시물을 수정합니다. (작성자만 가능)

**엔드포인트:** `PUT /api/community/posts/<slug>/update/` 또는 `PATCH /api/community/posts/<slug>/update/`

**인증:** 필요 (JWT, 작성자만)

**요청 본문:**
게시물 생성과 동일 (모든 필드 선택사항)

**성공 응답 (200 OK):**
게시물 상세 응답과 동일

**테스트 예시 (cURL):**
```bash
curl -X PUT "http://localhost:8000/api/community/posts/post-slug/update/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "수정된 제목",
    "content": "<p>수정된 내용</p>"
  }'
```

---

### 5. 게시물 삭제

동호인톡 게시물을 삭제합니다. (작성자만 가능)

**엔드포인트:** `DELETE /api/community/posts/<slug>/delete/`

**인증:** 필요 (JWT, 작성자만)

**성공 응답 (200 OK):**
```json
{
  "message": "게시글이 삭제되었습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X DELETE "http://localhost:8000/api/community/posts/post-slug/delete/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 6. 게시물 좋아요

게시물에 좋아요를 추가하거나 취소합니다.

**엔드포인트:** `POST /api/community/posts/<slug>/like/`

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
curl -X POST "http://localhost:8000/api/community/posts/post-slug/like/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. 댓글 목록

게시물의 댓글 목록을 조회합니다.

**엔드포인트:** `GET /api/community/posts/<slug>/comments/`

**인증:** 불필요

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
curl -X GET "http://localhost:8000/api/community/posts/post-slug/comments/"
```

---

### 8. 댓글 생성

게시물에 댓글을 작성합니다.

**엔드포인트:** `POST /api/community/posts/<slug>/comments/create/`

**인증:** 필요 (JWT)

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
curl -X POST "http://localhost:8000/api/community/posts/post-slug/comments/create/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "댓글 내용입니다"
  }'
```

---

### 9. 댓글 수정

댓글을 수정합니다. (작성자만 가능)

**엔드포인트:** `PUT /api/community/comments/<comment_id>/` 또는 `PATCH /api/community/comments/<comment_id>/`

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
curl -X PUT "http://localhost:8000/api/community/comments/1/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "수정된 댓글"
  }'
```

---

### 10. 댓글 삭제

댓글을 삭제합니다. (작성자만 가능)

**엔드포인트:** `DELETE /api/community/comments/<comment_id>/delete/`

**인증:** 필요 (JWT, 작성자만)

**성공 응답 (200 OK):**
```json
{
  "message": "댓글이 삭제되었습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X DELETE "http://localhost:8000/api/community/comments/1/delete/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 11. 댓글 좋아요

댓글에 좋아요를 추가하거나 취소합니다.

**엔드포인트:** `POST /api/community/comments/<comment_id>/like/`

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
curl -X POST "http://localhost:8000/api/community/comments/1/like/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 12. 이미지 업로드

게시물 작성 시 사용할 이미지를 업로드합니다.

**엔드포인트:** `POST /api/community/images/upload/`

**인증:** 필요 (JWT)

**요청 형식:** `multipart/form-data`

**요청 본문:**
```
image: (파일)
```

**제한사항:**
- 최대 파일 크기: 10MB
- 허용 확장자: jpg, jpeg, png, gif, webp

**성공 응답 (201 Created):**
```json
{
  "url": "http://localhost:8000/media/community/post_images/2024/01/01/abc123.jpg",
  "message": "이미지가 업로드되었습니다."
}
```

**테스트 예시 (cURL):**
```bash
curl -X POST "http://localhost:8000/api/community/images/upload/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "image=@/path/to/image.jpg"
```

---

### 13. 카테고리 목록

동호인톡 카테고리 목록을 조회합니다.

**엔드포인트:** `GET /api/community/categories/`

**인증:** 불필요

**성공 응답 (200 OK):**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "카테고리명",
      "slug": "category-slug",
      "parent": null
    },
    {
      "id": 2,
      "name": "하위 카테고리",
      "slug": "subcategory-slug",
      "parent": 1
    }
  ]
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost:8000/api/community/categories/"
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
http://localhost:8000/api/community/
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
  "error": "게시글을 수정할 권한이 없습니다."
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

1. **인증 토큰**: 게시물 생성/수정/삭제/좋아요는 JWT 토큰이 필요합니다. Accounts API를 통해 로그인하여 토큰을 받으세요.

2. **권한**: 게시물과 댓글의 수정/삭제는 작성자만 가능합니다. (관리자 제외)

3. **파일 업로드**: 이미지 업로드는 `multipart/form-data` 형식을 사용합니다.

4. **페이지네이션**: 목록 API는 기본적으로 10개씩 페이지네이션됩니다. `page`와 `page_size` 파라미터로 조정 가능합니다.

5. **슬러그**: 게시물 URL에 사용되는 slug는 한글을 포함할 수 있습니다.

---

## 추가 정보

- Accounts API 가이드: `API_GUIDE.md` 참고
- Badmintok API 가이드: `BADMINTOK_API_GUIDE.md` 참고
