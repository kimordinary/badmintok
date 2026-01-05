# Badmintok API 테스트 가이드

이 문서는 배드민톡 메인 페이지 관련 API를 테스트하는 방법을 안내합니다.

## 목차

1. [기본 정보](#기본-정보)
2. [API 엔드포인트](#api-엔드포인트)
3. [테스트 방법](#테스트-방법)
4. [오류 응답](#오류-응답)

---

## 기본 정보

### Base URL
```
http://localhost:8000/api/badmintok/
```

프로덕션 환경에서는 실제 도메인으로 변경하세요.

### Content-Type
모든 요청은 `application/json` 형식을 사용합니다.

### 인증
모든 엔드포인트는 **인증이 필요하지 않습니다** (공개 API).

---

## API 엔드포인트

### 1. 홈 페이지 (최신 게시물)

홈 페이지에 표시할 최신 배드민톡 게시물 5개를 조회합니다.

**엔드포인트:** `GET /api/badmintok/home/`

**인증:** 불필요

**쿼리 파라미터:** 없음

**성공 응답 (200 OK):**
```json
{
  "latest_posts": [
    {
      "id": 1,
      "title": "게시글 제목",
      "slug": "post-slug",
      "author_name": "작성자명",
      "author_image_url": "/static/images/userprofile/user.png",
      "category_name": "카테고리명",
      "category_slug": "category-slug",
      "thumbnail_url": null,
      "excerpt": "게시글 발췌문...",
      "content_image_url": "/media/community/post_images/2024/01/01/image.jpg",
      "view_count": 100,
      "like_count": 10,
      "comment_count": 5,
      "is_pinned": false,
      "created_at": "2024-01-01T00:00:00Z",
      "published_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### 2. 게시글 목록

배드민톡 게시글 목록을 조회합니다. 페이지네이션, 필터링, 검색을 지원합니다.

**엔드포인트:** `GET /api/badmintok/posts/`

**인증:** 불필요

**쿼리 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `tab` | string | 아니오 | 탭 필터 (news, reviews, brand 등) |
| `category` | string | 아니오 | 카테고리 slug 필터 |
| `search` | string | 아니오 | 검색어 (제목, 내용 검색) |
| `page` | integer | 아니오 | 페이지 번호 (기본값: 1) |
| `page_size` | integer | 아니오 | 페이지당 항목 수 (기본값: 10, 최대: 100) |

**예시 요청:**
```
GET /api/badmintok/posts/?tab=news&category=tournament&page=1&page_size=20
```

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
      "title": "게시글 제목",
      "slug": "post-slug",
      "author_name": "작성자명",
      "author_image_url": "/static/images/userprofile/user.png",
      "category_name": "대회소식",
      "category_slug": "tournament",
      "thumbnail_url": null,
      "excerpt": "게시글 발췌문...",
      "content_image_url": "/media/community/post_images/2024/01/01/image.jpg",
      "view_count": 100,
      "like_count": 10,
      "comment_count": 5,
      "is_pinned": false,
      "created_at": "2024-01-01T00:00:00Z",
      "published_at": "2024-01-01T00:00:00Z"
    }
  ],
  "next": 2,
  "previous": null
}
```

---

### 3. 게시글 상세

특정 배드민톡 게시글의 상세 정보를 조회합니다.

**엔드포인트:** `GET /api/badmintok/posts/{slug}/`

**인증:** 불필요 (작성자/관리자는 임시저장 글도 조회 가능)

**URL 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `slug` | string | 예 | 게시글 slug |

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "title": "게시글 제목",
  "slug": "post-slug",
  "content": "<p>게시글 내용 (HTML)</p>",
  "author": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "작성자명",
    "auth_provider": null,
    "profile_image_url": "/static/images/userprofile/user.png",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "category_name": "대회소식",
  "category_slug": "tournament",
  "categories": [
    {
      "id": 1,
      "name": "대회소식",
      "slug": "tournament"
    }
  ],
  "thumbnail_url": null,
  "images": [
    {
      "image_url": "/media/community/post_images/2024/01/01/image.jpg",
      "order": 0
    }
  ],
  "view_count": 101,
  "like_count": 10,
  "comment_count": 5,
  "is_pinned": false,
  "is_liked": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "published_at": "2024-01-01T00:00:00Z"
}
```

**오류 응답 (404 Not Found):**
```json
{
  "detail": "Not found."
}
```

---

### 4. 인기 게시글 (Hot)

최근 30일 내 인기 게시글을 조회합니다. (복합 점수 기반)

**엔드포인트:** `GET /api/badmintok/posts/hot/`

**인증:** 불필요

**쿼리 파라미터:** 없음

**성공 응답 (200 OK):**
```json
{
  "hot_posts": [
    {
      "id": 1,
      "title": "인기 게시글 제목",
      "slug": "hot-post-slug",
      "author_name": "작성자명",
      "author_image_url": "/static/images/userprofile/user.png",
      "category_name": "대회소식",
      "category_slug": "tournament",
      "thumbnail_url": null,
      "excerpt": "게시글 발췌문...",
      "content_image_url": "/media/community/post_images/2024/01/01/image.jpg",
      "view_count": 500,
      "like_count": 50,
      "comment_count": 30,
      "is_pinned": false,
      "created_at": "2024-01-01T00:00:00Z",
      "published_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**인기 점수 계산 방식:**
- 기본 점수: (조회수 × 1) + (좋아요 × 2) + (댓글 × 3)
- 시간 가중치: 최근 7일 내 글은 1.5배, 그 외는 1.0배
- 최종 점수 = 기본 점수 × 시간 가중치

---

### 5. 배너 목록

활성화된 배너 목록을 조회합니다.

**엔드포인트:** `GET /api/badmintok/banners/`

**인증:** 불필요

**쿼리 파라미터:** 없음

**성공 응답 (200 OK):**
```json
{
  "banners": [
    {
      "id": 1,
      "title": "배너 제목",
      "image_url": "http://localhost:8000/media/badmintok_banners/banner.jpg",
      "link_url": "https://example.com",
      "alt_text": "배너 대체 텍스트",
      "display_order": 0
    }
  ]
}
```

---

### 6. 공지사항 목록

공지사항 목록을 조회합니다.

**엔드포인트:** `GET /api/badmintok/notices/`

**인증:** 불필요

**쿼리 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `page` | integer | 아니오 | 페이지 번호 (기본값: 1) |
| `page_size` | integer | 아니오 | 페이지당 항목 수 (기본값: 20, 최대: 100) |

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
      "title": "공지사항 제목",
      "author_name": "관리자",
      "is_pinned": true,
      "view_count": 100,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "next": 2,
  "previous": null
}
```

---

### 7. 공지사항 상세

특정 공지사항의 상세 정보를 조회합니다.

**엔드포인트:** `GET /api/badmintok/notices/{notice_id}/`

**인증:** 불필요

**URL 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `notice_id` | integer | 예 | 공지사항 ID |

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "title": "공지사항 제목",
  "content": "공지사항 내용",
  "author_name": "관리자",
  "is_pinned": true,
  "view_count": 101,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**오류 응답 (404 Not Found):**
```json
{
  "detail": "Not found."
}
```

---

## 테스트 방법

### 1. cURL 사용

#### 홈 페이지 (최신 게시물)
```bash
curl -X GET http://localhost:8000/api/badmintok/home/
```

#### 게시글 목록
```bash
# 기본 목록
curl -X GET http://localhost:8000/api/badmintok/posts/

# 뉴스 탭 필터
curl -X GET "http://localhost:8000/api/badmintok/posts/?tab=news"

# 검색
curl -X GET "http://localhost:8000/api/badmintok/posts/?search=배드민턴"

# 페이지네이션
curl -X GET "http://localhost:8000/api/badmintok/posts/?page=2&page_size=20"
```

#### 게시글 상세
```bash
curl -X GET http://localhost:8000/api/badmintok/posts/post-slug/
```

#### 인기 게시글
```bash
curl -X GET http://localhost:8000/api/badmintok/posts/hot/
```

#### 배너 목록
```bash
curl -X GET http://localhost:8000/api/badmintok/banners/
```

#### 공지사항 목록
```bash
curl -X GET http://localhost:8000/api/badmintok/notices/
```

#### 공지사항 상세
```bash
curl -X GET http://localhost:8000/api/badmintok/notices/1/
```

---

### 2. Postman 사용

#### 설정 방법

1. **새 요청 생성**
   - Method: GET
   - URL: `http://localhost:8000/api/badmintok/{endpoint}/`

2. **쿼리 파라미터 설정**
   - Params 탭에서 쿼리 파라미터 추가
   - 예: `tab=news`, `page=1`, `page_size=20`

3. **환경 변수 설정 (선택사항)**
   - `base_url`: `http://localhost:8000/api/badmintok`
   - URL에서 `{{base_url}}/posts/` 형식으로 사용

---

### 3. Python Requests 사용

```python
import requests

BASE_URL = "http://localhost:8000/api/badmintok"

# 1. 홈 페이지
response = requests.get(f"{BASE_URL}/home/")
print(response.json())

# 2. 게시글 목록
params = {
    'tab': 'news',
    'page': 1,
    'page_size': 20
}
response = requests.get(f"{BASE_URL}/posts/", params=params)
data = response.json()
print(f"총 {data['count']}개 게시글")
print(data['results'])

# 3. 게시글 상세
slug = "post-slug"
response = requests.get(f"{BASE_URL}/posts/{slug}/")
print(response.json())

# 4. 인기 게시글
response = requests.get(f"{BASE_URL}/posts/hot/")
print(response.json())

# 5. 배너 목록
response = requests.get(f"{BASE_URL}/banners/")
print(response.json())

# 6. 공지사항 목록
response = requests.get(f"{BASE_URL}/notices/", params={'page': 1})
print(response.json())

# 7. 공지사항 상세
notice_id = 1
response = requests.get(f"{BASE_URL}/notices/{notice_id}/")
print(response.json())
```

---

### 4. JavaScript (Fetch API) 사용

```javascript
const BASE_URL = 'http://localhost:8000/api/badmintok';

// 1. 홈 페이지
async function getHome() {
  const response = await fetch(`${BASE_URL}/home/`);
  const data = await response.json();
  console.log(data.latest_posts);
}

// 2. 게시글 목록
async function getPosts(tab = '', page = 1) {
  const params = new URLSearchParams({
    tab: tab,
    page: page,
    page_size: 20
  });
  
  const response = await fetch(`${BASE_URL}/posts/?${params}`);
  const data = await response.json();
  console.log(data);
  
  return data;
}

// 3. 게시글 상세
async function getPostDetail(slug) {
  const response = await fetch(`${BASE_URL}/posts/${slug}/`);
  const data = await response.json();
  console.log(data);
  
  return data;
}

// 4. 인기 게시글
async function getHotPosts() {
  const response = await fetch(`${BASE_URL}/posts/hot/`);
  const data = await response.json();
  console.log(data.hot_posts);
}

// 5. 배너 목록
async function getBanners() {
  const response = await fetch(`${BASE_URL}/banners/`);
  const data = await response.json();
  console.log(data.banners);
}

// 6. 공지사항 목록
async function getNotices(page = 1) {
  const params = new URLSearchParams({
    page: page,
    page_size: 20
  });
  
  const response = await fetch(`${BASE_URL}/notices/?${params}`);
  const data = await response.json();
  console.log(data);
  
  return data;
}

// 7. 공지사항 상세
async function getNoticeDetail(noticeId) {
  const response = await fetch(`${BASE_URL}/notices/${noticeId}/`);
  const data = await response.json();
  console.log(data);
  
  return data;
}
```

---

## 오류 응답

### 공통 오류 코드

| 상태 코드 | 의미 | 설명 |
|---------|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 오류 |

### 오류 응답 예시

#### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## 탭 및 카테고리 필터

### 탭 목록

게시글 목록 API의 `tab` 파라미터에 사용할 수 있는 값:

- `news`: 뉴스 탭 (대회소식, 선수소식, 용품, 커뮤니티)
- `reviews`: 리뷰 탭 (라켓, 신발, 의류, 셔틀콕, 보호용품, 액세서리)
- `brand`: 브랜드관 탭 (요넥스, 리닝, 빅터 등)
- 기타: 카테고리 slug (상위 카테고리)

### 카테고리 필터

`category` 파라미터에 하위 카테고리 slug를 지정하면 해당 카테고리의 게시글만 필터링됩니다.

**예시:**
```
GET /api/badmintok/posts/?tab=news&category=tournament
```

---

## 데이터 구조 설명

### 게시글 (Post)

- `id`: 게시글 ID
- `title`: 제목
- `slug`: URL slug
- `author_name`: 작성자 활동명
- `author_image_url`: 작성자 프로필 이미지 URL
- `category_name`: 메인 카테고리 이름
- `category_slug`: 메인 카테고리 slug
- `thumbnail_url`: 썸네일 이미지 URL
- `excerpt`: 발췌문 (HTML 태그 제거, 80자 제한)
- `content_image_url`: 본문에서 추출한 첫 번째 이미지 URL
- `view_count`: 조회수
- `like_count`: 좋아요 수
- `comment_count`: 댓글 수
- `is_pinned`: 고정 여부
- `created_at`: 작성일
- `published_at`: 발행일

### 게시글 상세 (Post Detail)

게시글 목록의 필드 외 추가 필드:

- `content`: 게시글 내용 (HTML)
- `author`: 작성자 정보 객체
- `categories`: 다중 카테고리 목록
- `images`: 게시글 이미지 목록
- `is_liked`: 현재 사용자가 좋아요 했는지 (인증 시)

### 공지사항 (Notice)

- `id`: 공지사항 ID
- `title`: 제목
- `content`: 내용 (상세 조회 시)
- `author_name`: 작성자 이름
- `is_pinned`: 고정 여부
- `view_count`: 조회수
- `created_at`: 작성일
- `updated_at`: 수정일

---

## 주의사항

1. **페이지네이션**
   - 기본 페이지 크기: 게시글 목록 10개, 공지사항 목록 20개
   - 최대 페이지 크기: 100개
   - 페이지 번호는 1부터 시작

2. **조회수 증가**
   - 게시글 상세 조회 시 자동으로 조회수가 증가합니다
   - 공지사항 상세 조회 시에도 조회수가 증가합니다

3. **이미지 URL**
   - 모든 이미지 URL은 절대 경로로 반환됩니다
   - 개발 환경: `http://localhost:8000/media/...`
   - 프로덕션 환경: 실제 도메인 URL

4. **검색 기능**
   - 제목과 내용에서 검색합니다
   - 대소문자를 구분하지 않습니다 (case-insensitive)

5. **인기 게시글**
   - 최근 30일 내 게시글만 포함됩니다
   - 복합 점수 기반으로 정렬됩니다
   - 최대 10개만 반환됩니다

---

## 추가 정보

### 지원 문의

API 관련 문의사항이 있으시면 관리자에게 문의하세요.

