# Contests API 테스트 가이드

이 문서는 배드민톡 Contests (대회) API를 테스트하는 방법을 안내합니다.

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
http://localhost/api/contests/
```

프로덕션 환경에서는 실제 도메인으로 변경하세요.

### Content-Type
모든 요청은 `application/json` 형식을 사용합니다.

### 인증
대부분의 엔드포인트는 인증이 필요하지 않지만, 좋아요 기능은 JWT 인증이 필요합니다.

---

## 인증 방식

대회 좋아요 기능은 **JWT (JSON Web Token)** 인증이 필요합니다.

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

### 1. 대회 목록

대회 목록을 조회합니다.

**엔드포인트:** `GET /api/contests/contests/`

**인증:** 불필요

**쿼리 파라미터:**
- `page` (선택): 페이지 번호 (기본값: 1)
- `page_size` (선택): 페이지당 항목 수 (기본값: 20, 최대: 100)
- `category` (선택): 카테고리 ID
- `search` (선택): 검색어 (대회명/상세 장소 검색)
- `qualifying` (선택): 승급 대회 필터 (`true`, `false` - 여러 개 선택 가능)
- `sponsor` (선택): 스폰서 ID 또는 이름 (여러 개 선택 가능)
- `region` (선택): 지역 필터 (서울, 경기, 인천, 부산, 대구, 광주, 대전, 울산, 강원, 세종, 충북, 충남, 전북, 전남, 경북, 경남, 제주)
- `date_from` (선택): 시작일 필터 (YYYY-MM-DD 형식)
- `date_to` (선택): 종료일 필터 (YYYY-MM-DD 형식)
- `ordering` (선택): 정렬 기준 (`schedule_start`, `-schedule_start`, `created_at`, `-created_at`, `registration_start`, `-registration_start`)

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
      "title": "대회명",
      "slug": "contest-slug",
      "category": {
        "id": 1,
        "name": "분류명",
        "color": "#31AA60",
        "description": "분류 설명"
      },
      "is_qualifying": false,
      "schedule_start": "2024-03-01",
      "schedule_end": "2024-03-03",
      "region": "서울",
      "region_detail": "올림픽공원",
      "period_display": "2024.03.01 ~ 2024.03.03",
      "registration_start": "2024-02-01",
      "registration_end": "2024-02-20",
      "registration_period_display": "2024.02.01 ~ 2024.02.20",
      "d_day_display": "D-30",
      "location_display": "[서울] 올림픽공원",
      "sponsor": {
        "id": 1,
        "name": "스폰서명"
      },
      "like_count": 50,
      "is_liked": false,
      "thumbnail_image_url": "http://localhost/media/contest_images/...",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "next": 2,
  "previous": null
}
```

**테스트 예시 (cURL):**
```bash
# 기본 목록
curl -X GET "http://localhost/api/contests/contests/"

# 카테고리 필터
curl -X GET "http://localhost/api/contests/contests/?category=1"

# 검색
curl -X GET "http://localhost/api/contests/contests/?search=서울"

# 승급 대회만
curl -X GET "http://localhost/api/contests/contests/?qualifying=true"

# 스폰서 필터
curl -X GET "http://localhost/api/contests/contests/?sponsor=1"

# 지역 필터
curl -X GET "http://localhost/api/contests/contests/?region=서울"

# 날짜 범위 필터
curl -X GET "http://localhost/api/contests/contests/?date_from=2024-03-01&date_to=2024-03-31"

# 정렬
curl -X GET "http://localhost/api/contests/contests/?ordering=-schedule_start"

# 페이지네이션
curl -X GET "http://localhost/api/contests/contests/?page=2&page_size=20"
```

---

### 2. 대회 상세

대회 상세 정보를 조회합니다.

**엔드포인트:** `GET /api/contests/contests/<slug>/`

**인증:** 불필요

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "title": "대회명",
  "slug": "contest-slug",
  "category": {
    "id": 1,
    "name": "분류명",
    "color": "#31AA60",
    "description": "분류 설명"
  },
  "is_qualifying": false,
  "schedule_start": "2024-03-01",
  "schedule_end": "2024-03-03",
  "region": "서울",
  "region_detail": "올림픽공원",
  "event_division": "혼복/여복/남복",
  "period_display": "2024.03.01 ~ 2024.03.03",
  "registration_start": "2024-02-01",
  "registration_end": "2024-02-20",
  "registration_period_display": "2024.02.01 ~ 2024.02.20",
  "entry_fee": "개인 10,000원",
  "competition_type": "개인전",
  "participant_reward": "참가상품",
  "sponsor": {
    "id": 1,
    "name": "스폰서명"
  },
  "award_reward": [
    {
      "division": "혼복",
      "prizes": [
        {
          "rank": "1위",
          "prize": "상품"
        }
      ]
    }
  ],
  "award_reward_text": "입상상품 상세 정보",
  "registration_name": "배드민톡",
  "registration_link": "https://example.com/register",
  "description": "대회 요강 AI 요약",
  "participant_target": "참가 대상 정보",
  "d_day_display": "D-30",
  "location_display": "[서울] 올림픽공원",
  "schedules": [
    {
      "id": 1,
      "date": "2024-03-01",
      "events": ["혼복", "여복"],
      "ages": ["20대", "30대"],
      "events_display": ["혼복", "여복"],
      "age_display": "20대~30대",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "images": [
    {
      "id": 1,
      "image_url": "http://localhost/media/contest_images/...",
      "order": 0
    }
  ],
  "like_count": 50,
  "is_liked": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/contests/contests/contest-slug/"
```

---

### 3. 대회 좋아요

대회에 좋아요를 추가하거나 취소합니다.

**엔드포인트:** `POST /api/contests/contests/<slug>/like/`

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
curl -X POST "http://localhost/api/contests/contests/contest-slug/like/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. 대회 분류 목록

대회 분류 목록을 조회합니다.

**엔드포인트:** `GET /api/contests/categories/`

**인증:** 불필요

**성공 응답 (200 OK):**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "분류명",
      "color": "#31AA60",
      "description": "분류 설명"
    }
  ]
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/contests/categories/"
```

---

### 5. 스폰서 목록

스폰서 목록을 조회합니다.

**엔드포인트:** `GET /api/contests/sponsors/`

**인증:** 불필요

**성공 응답 (200 OK):**
```json
{
  "sponsors": [
    {
      "id": 1,
      "name": "스폰서명"
    }
  ]
}
```

**테스트 예시 (cURL):**
```bash
curl -X GET "http://localhost/api/contests/sponsors/"
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
http://localhost/api/contests/
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

1. **인증 토큰**: 대회 좋아요 기능은 JWT 토큰이 필요합니다. Accounts API를 통해 로그인하여 토큰을 받으세요.

2. **날짜 형식**: `date_from`과 `date_to` 파라미터는 `YYYY-MM-DD` 형식(ISO 8601)을 사용합니다.

3. **필터링**: 여러 필터를 동시에 사용할 수 있으며, AND 조건으로 결합됩니다.

4. **정렬**: `ordering` 파라미터는 보안을 위해 허용된 필드만 사용 가능합니다.

5. **페이지네이션**: 목록 API는 기본적으로 20개씩 페이지네이션됩니다. `page`와 `page_size` 파라미터로 조정 가능합니다.

6. **슬러그**: 대회 URL에 사용되는 slug는 한글을 포함할 수 있습니다.

---

## 추가 정보

- Accounts API 가이드: `API_GUIDE.md` 참고
- Badmintok API 가이드: `BADMINTOK_API_GUIDE.md` 참고
- Community API 가이드: `COMMUNITY_API_GUIDE.md` 참고
- Band API 가이드: `BAND_API_GUIDE.md` 참고
