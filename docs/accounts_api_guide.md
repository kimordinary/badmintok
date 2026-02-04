# Accounts API 가이드

## 목차
1. [개요](#개요)
2. [인증 방식](#인증-방식)
3. [모바일 소셜 로그인 API](#모바일-소셜-로그인-api)
4. [프로필 REST API](#프로필-rest-api)
5. [마이페이지 요약 REST API](#마이페이지-요약-rest-api)
6. [사용자 차단 REST API](#사용자-차단-rest-api)
7. [신고 REST API](#신고-rest-api)
8. [문의 REST API](#문의-rest-api)
9. [계정 삭제 REST API](#계정-삭제-rest-api)
10. [웹 인증 엔드포인트](#웹-인증-엔드포인트)
11. [마이페이지 웹 API](#마이페이지-웹-api)
12. [모델 구조](#모델-구조)
13. [에러 처리](#에러-처리)

---

## 개요

Badmintok 계정 시스템은 일반 이메일 가입과 소셜 로그인(카카오, 네이버, 구글)을 지원합니다. 모바일 앱을 위한 JSON API와 웹을 위한 전통적인 Django 뷰를 모두 제공합니다.

**Base URL**: `/accounts/`

---

## 인증 방식

### 세션 기반 인증
- 로그인 성공 시 Django 세션 생성
- 모바일 API는 `session_id`를 반환하여 이후 요청에 사용

### 소셜 인증 제공자
| 제공자 | auth_provider 값 |
|--------|-----------------|
| 카카오 | `kakao` |
| 네이버 | `naver` |
| 구글 | `google` |
| 일반 가입 | `""` (빈 문자열) |

---

## 모바일 소셜 로그인 API

모바일 앱에서 소셜 로그인을 처리하기 위한 JSON API 엔드포인트입니다.

### 카카오 모바일 로그인

**POST** `/accounts/api/kakao/mobile/`

모바일 앱에서 카카오 SDK로 받은 access_token을 서버에 전송하여 로그인합니다.

#### Request
```json
{
  "access_token": "카카오에서 받은 access_token"
}
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "profile_image_url": "https://example.com/profile.jpg"
  },
  "session_id": "세션_ID",
  "requires_real_name": false
}
```

#### Response (실패 - 400/500)
```json
{
  "success": false,
  "error": "access_token이 필요합니다"
}
```

#### 처리 흐름
1. 클라이언트에서 카카오 access_token 전송
2. 서버에서 카카오 API로 사용자 정보 조회
3. 사용자 생성 또는 기존 사용자 조회
4. 프로필 이미지 다운로드 (최초 로그인 시)
5. 세션 생성 및 응답 반환

---

### 네이버 모바일 로그인

**POST** `/accounts/api/naver/mobile/`

#### Request
```json
{
  "access_token": "네이버에서 받은 access_token"
}
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "profile_image_url": "https://example.com/profile.jpg"
  },
  "session_id": "세션_ID",
  "requires_real_name": false
}
```

#### 네이버 API 필드 매핑
| 네이버 필드 | 서버 필드 |
|------------|----------|
| `email` | `email` |
| `nickname` | `activity_name` |
| `profile_image` | `profile_image` |
| `gender` ("M"/"F") | `gender` ("male"/"female") |
| `birthyear` | `birth_year` |

---

### 구글 모바일 로그인

**POST** `/accounts/api/google/mobile/`

#### Request
```json
{
  "access_token": "구글에서 받은 access_token"
}
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "profile_image_url": "https://example.com/profile.jpg"
  },
  "session_id": "세션_ID",
  "requires_real_name": false
}
```

#### 주의사항
- Google은 `verified_email` 필드로 이메일 인증 여부 확인
- 인증되지 않은 이메일은 로그인 거부

---

## 프로필 REST API

모바일 앱에서 사용자 프로필을 조회하고 수정하기 위한 JSON API 엔드포인트입니다.

### 프로필 조회

**GET** `/accounts/api/profile/`

로그인한 사용자의 프로필 정보를 조회합니다.

#### Request Headers
```
Cookie: sessionid=<session_id>
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "activity_name": "사용자명",
      "auth_provider": "kakao",
      "is_social_auth": true,
      "date_joined": "2024-01-15T10:30:00+09:00"
    },
    "profile": {
      "name": "홍길동",
      "profile_image_url": "https://example.com/media/images/userprofile/abc123.jpg",
      "badminton_level": "c",
      "badminton_level_display": "C",
      "gender": "male",
      "gender_display": "남성",
      "age_range": "30대",
      "birthday": "1990-05-15",
      "birth_year": 1990,
      "phone_number": "010-1234-5678",
      "shipping_receiver": "홍길동",
      "shipping_phone_number": "010-1234-5678",
      "shipping_address": "서울시 강남구 테헤란로 123",
      "created_at": "2024-01-15T10:30:00+09:00",
      "updated_at": "2024-01-20T15:45:00+09:00"
    }
  }
}
```

#### Response (실패 - 401)
```json
{
  "success": false,
  "error": "로그인이 필요합니다"
}
```

---

### 프로필 수정

**PUT** `/accounts/api/profile/`

로그인한 사용자의 프로필 정보를 수정합니다.

#### Request Headers
```
Content-Type: application/json
Cookie: sessionid=<session_id>
```

#### Request Body (JSON)
```json
{
  "activity_name": "새로운활동명",
  "name": "홍길동",
  "badminton_level": "b",
  "gender": "male",
  "age_range": "30대",
  "birthday": "1990-05-15",
  "birth_year": 1990,
  "phone_number": "010-1234-5678",
  "shipping_receiver": "홍길동",
  "shipping_phone_number": "010-1234-5678",
  "shipping_address": "서울시 강남구 테헤란로 123"
}
```

> **참고**: 모든 필드는 선택적입니다. 수정하려는 필드만 전송하면 됩니다.

#### 프로필 이미지 업로드

프로필 이미지를 업로드하려면 `multipart/form-data` 형식을 사용합니다.

```
Content-Type: multipart/form-data
```

| 필드 | 타입 | 설명 |
|-----|------|------|
| `profile_image` | File | 프로필 이미지 파일 |
| `activity_name` | String | 활동명 (선택) |
| `name` | String | 실명 (선택) |
| ... | ... | 기타 필드들 |

#### Response (성공 - 200)
```json
{
  "success": true,
  "message": "프로필이 수정되었습니다",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "activity_name": "새로운활동명"
    },
    "profile": {
      "name": "홍길동",
      "profile_image_url": "https://example.com/media/images/userprofile/abc123.jpg",
      "badminton_level": "b",
      "badminton_level_display": "B",
      "gender": "male",
      "gender_display": "남성",
      "age_range": "30대",
      "birthday": "1990-05-15",
      "birth_year": 1990,
      "phone_number": "010-1234-5678",
      "shipping_receiver": "홍길동",
      "shipping_phone_number": "010-1234-5678",
      "shipping_address": "서울시 강남구 테헤란로 123",
      "updated_at": "2024-01-20T15:45:00+09:00"
    }
  }
}
```

#### Response (실패)

| HTTP 상태 | 에러 메시지 |
|----------|------------|
| 401 | "로그인이 필요합니다" |
| 400 | "잘못된 JSON 형식입니다" |
| 400 | "생일 형식이 올바르지 않습니다 (YYYY-MM-DD)" |
| 400 | "출생연도는 숫자여야 합니다" |

#### 수정 가능한 필드

| 필드 | 타입 | 설명 | 유효값 |
|-----|------|------|--------|
| `activity_name` | String | 활동명 (User 모델) | - |
| `name` | String | 실명 | - |
| `badminton_level` | String | 배드민턴 급수 | `beginner`, `d`, `c`, `b`, `a`, `s`, `master`, `""` |
| `gender` | String | 성별 | `male`, `female`, `other`, `unknown` |
| `age_range` | String | 연령대 | - |
| `birthday` | String | 생일 | `YYYY-MM-DD` 형식 |
| `birth_year` | Integer | 출생연도 | 숫자 |
| `phone_number` | String | 전화번호 | - |
| `shipping_receiver` | String | 배송 수령인 | - |
| `shipping_phone_number` | String | 배송지 전화번호 | - |
| `shipping_address` | String | 배송지 주소 | - |
| `profile_image` | File | 프로필 이미지 | 이미지 파일 (multipart/form-data) |

---

## 마이페이지 요약 REST API

모바일 앱에서 마이페이지 요약 정보를 조회하기 위한 API입니다.

### 마이페이지 요약 조회

**GET** `/accounts/api/mypage/summary/`

#### Request Headers
```
Cookie: sessionid=<session_id>
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "activity_name": "사용자명",
      "profile_image_url": "https://example.com/media/images/userprofile/abc123.jpg"
    },
    "counts": {
      "my_bands": 5,
      "created_bands": 2,
      "bookmarked_bands": 3,
      "band_posts": 10,
      "band_comments": 25,
      "liked_band_posts": 15,
      "schedule_applications": 8,
      "vote_choices": 12,
      "community_posts": 7,
      "liked_posts": 20,
      "comments": 30,
      "shared_posts": 5,
      "liked_contests": 3
    }
  }
}
```

---

## 사용자 차단 REST API

사용자 차단 관리를 위한 API입니다.

### 차단 목록 조회

**GET** `/accounts/api/block/`

#### Response (성공 - 200)
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "blocked_user": {
        "id": 2,
        "activity_name": "차단된사용자",
        "profile_image_url": "https://example.com/profile.jpg"
      },
      "created_at": "2024-01-15T10:30:00+09:00"
    }
  ]
}
```

### 사용자 차단

**POST** `/accounts/api/block/`

#### Request Body
```json
{
  "user_id": 2
}
```

#### Response (성공 - 201)
```json
{
  "success": true,
  "message": "홍길동님을 차단했습니다",
  "data": {
    "id": 1,
    "blocked_user_id": 2,
    "created_at": "2024-01-15T10:30:00+09:00"
  }
}
```

#### Response (실패)
| HTTP 상태 | 에러 메시지 |
|----------|------------|
| 400 | "user_id가 필요합니다" |
| 400 | "자기 자신을 차단할 수 없습니다" |
| 400 | "이미 차단한 사용자입니다" |
| 404 | "사용자를 찾을 수 없습니다" |

### 차단 해제

**DELETE** `/accounts/api/block/`

#### Request Body
```json
{
  "user_id": 2
}
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "message": "홍길동님의 차단을 해제했습니다"
}
```

---

## 신고 REST API

신고 기능을 위한 API입니다.

### 내 신고 목록 조회

**GET** `/accounts/api/report/`

#### Response (성공 - 200)
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "report_type": "user",
      "report_type_display": "사용자",
      "target_id": 5,
      "reason": "부적절한 행동",
      "status": "pending",
      "status_display": "대기중",
      "created_at": "2024-01-15T10:30:00+09:00"
    }
  ]
}
```

### 신고 생성

**POST** `/accounts/api/report/`

#### Request Body
```json
{
  "report_type": "user",
  "target_id": 5,
  "reason": "부적절한 행동입니다"
}
```

#### 신고 유형 (report_type)
| 값 | 설명 |
|----|------|
| `user` | 사용자 |
| `post` | 게시글 |
| `comment` | 댓글 |
| `band` | 모임 |
| `other` | 기타 |

#### Response (성공 - 201)
```json
{
  "success": true,
  "message": "신고가 접수되었습니다",
  "data": {
    "id": 1,
    "report_type": "user",
    "target_id": 5,
    "status": "pending",
    "created_at": "2024-01-15T10:30:00+09:00"
  }
}
```

---

## 문의 REST API

문의하기 기능을 위한 API입니다.

### 내 문의 목록 조회

**GET** `/accounts/api/inquiry/`

#### Response (성공 - 200)
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "category": "general",
      "category_display": "일반 문의",
      "title": "앱 사용 관련 문의",
      "status": "pending",
      "status_display": "대기중",
      "created_at": "2024-01-15T10:30:00+09:00",
      "answered_at": null
    }
  ]
}
```

### 문의 상세 조회

**GET** `/accounts/api/inquiry/?id=1`

#### Response (성공 - 200)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "category": "general",
    "category_display": "일반 문의",
    "title": "앱 사용 관련 문의",
    "content": "문의 내용입니다...",
    "status": "answered",
    "status_display": "답변완료",
    "admin_response": "관리자 답변입니다...",
    "created_at": "2024-01-15T10:30:00+09:00",
    "answered_at": "2024-01-16T14:00:00+09:00"
  }
}
```

### 문의 생성

**POST** `/accounts/api/inquiry/`

#### Request Body
```json
{
  "category": "general",
  "title": "앱 사용 관련 문의",
  "content": "문의 내용입니다..."
}
```

#### 문의 카테고리 (category)
| 값 | 설명 |
|----|------|
| `general` | 일반 문의 (기본값) |
| `technical` | 기술 문의 |
| `bug` | 버그 신고 |
| `suggestion` | 건의사항 |
| `other` | 기타 |

#### Response (성공 - 201)
```json
{
  "success": true,
  "message": "문의가 등록되었습니다",
  "data": {
    "id": 1,
    "category": "general",
    "title": "앱 사용 관련 문의",
    "status": "pending",
    "created_at": "2024-01-15T10:30:00+09:00"
  }
}
```

---

## 계정 삭제 REST API

계정 탈퇴를 위한 API입니다.

### 계정 탈퇴

**POST** `/accounts/api/account/delete/`

#### Request Headers
```
Cookie: sessionid=<session_id>
```

#### Response (성공 - 200)
```json
{
  "success": true,
  "message": "계정이 탈퇴 처리되었습니다"
}
```

> **주의**: 계정 삭제 후 세션이 무효화됩니다. 실제 데이터는 삭제되지 않고 `is_active`가 `False`로 변경됩니다.

---

## 웹 인증 엔드포인트

웹 브라우저에서 사용하는 전통적인 Django 뷰 기반 엔드포인트입니다.

### 회원가입

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/accounts/signup/` | 회원가입 폼 |
| GET | `/accounts/signup/success/` | 가입 성공 페이지 |

### 로그인/로그아웃

| Method | URL | 설명 |
|--------|-----|------|
| GET/POST | `/accounts/login/` | 이메일 로그인 |
| GET | `/accounts/logout/` | 로그아웃 |

### 소셜 로그인 (OAuth 플로우)

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/accounts/login/kakao/` | 카카오 OAuth 시작 |
| GET | `/accounts/kakao/` | 카카오 콜백 |
| GET | `/accounts/login/naver/` | 네이버 OAuth 시작 |
| GET | `/accounts/naver/` | 네이버 콜백 |
| GET | `/accounts/login/google/` | 구글 OAuth 시작 |
| GET | `/accounts/google/` | 구글 콜백 |

### 실명 입력

| Method | URL | 설명 |
|--------|-----|------|
| GET/POST | `/accounts/enter-real-name/` | 소셜 로그인 후 실명 입력 |

---

## 마이페이지 웹 API

웹 브라우저용 마이페이지 엔드포인트입니다. 로그인 필수(`@login_required`). 페이지네이션: 20개/페이지

### 대시보드

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET | `/accounts/mypage/` | mypage | 마이페이지 요약 |

### 밴드 관련

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET | `/accounts/mypage/bands/` | mypage_bands | 내 밴드 목록 |
| GET | `/accounts/mypage/created-bands/` | mypage_created_bands | 내가 만든 밴드 |
| GET | `/accounts/mypage/bookmarked-bands/` | mypage_bookmarked_bands | 북마크한 밴드 |
| GET | `/accounts/mypage/band-posts/` | mypage_band_posts | 내 밴드 게시글 |
| GET | `/accounts/mypage/band-comments/` | mypage_band_comments | 내 밴드 댓글 |
| GET | `/accounts/mypage/liked-band-posts/` | mypage_liked_band_posts | 좋아요한 밴드 게시글 |

### 활동 관련

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET | `/accounts/mypage/schedule-applications/` | mypage_schedule_applications | 일정 신청 내역 |
| GET | `/accounts/mypage/vote-choices/` | mypage_vote_choices | 참여한 투표 |
| GET | `/accounts/mypage/community-posts/` | mypage_community_posts | 커뮤니티 게시글 |
| GET | `/accounts/mypage/liked-posts/` | mypage_liked_posts | 좋아요한 게시글 |
| GET | `/accounts/mypage/comments/` | mypage_comments | 내 댓글 |
| GET | `/accounts/mypage/shared-posts/` | mypage_shared_posts | 공유한 게시글 |
| GET | `/accounts/mypage/liked-contests/` | mypage_liked_contests | 좋아요한 대회 |

---

## 계정 관리 웹 API

웹 브라우저용 계정 관리 엔드포인트입니다.

### 프로필

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET/POST | `/accounts/profile/edit/` | profile_edit | 프로필 수정 |

### 설정

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET | `/accounts/mypage/notifications/` | notification_settings | 알림 설정 |
| GET/POST | `/accounts/mypage/password-change/` | password_change | 비밀번호 변경 |
| GET/POST | `/accounts/mypage/account-delete/` | account_delete | 계정 삭제 |

### 차단/신고

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET/POST | `/accounts/mypage/blocked-users/` | blocked_users | 차단 사용자 관리 |
| GET | `/accounts/mypage/reports/` | report_list | 신고 내역 |

### 문의

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET/POST | `/accounts/mypage/inquiry/` | inquiry_create | 문의 작성 |
| GET | `/accounts/mypage/inquiries/` | inquiry_list | 문의 내역 |

### 약관

| Method | URL | Name | 설명 |
|--------|-----|------|------|
| GET | `/accounts/mypage/privacy-policy/` | privacy_policy | 개인정보처리방침 |
| GET | `/accounts/mypage/terms/` | terms_of_service | 이용약관 |

---

## 모델 구조

### User (사용자)

| 필드 | 타입 | 설명 |
|-----|------|------|
| `email` | EmailField | 이메일 (고유값, 로그인 ID) |
| `activity_name` | CharField | 활동명 (표시 이름) |
| `auth_provider` | CharField | 인증 제공자 (kakao/naver/google/"") |
| `band_creation_blocked_until` | DateTimeField | 밴드 생성 제한 해제일 |
| `is_active` | BooleanField | 활성 상태 |
| `date_joined` | DateTimeField | 가입일 |

#### 주요 속성/메서드
- `is_social_auth`: 소셜 로그인 여부
- `real_name`: 실명 (프로필의 name 또는 activity_name)
- `profile_image_url`: 프로필 이미지 URL

---

### UserProfile (프로필)

| 필드 | 타입 | 설명 |
|-----|------|------|
| `user` | OneToOneField | 사용자 연결 |
| `profile_image` | ImageField | 프로필 이미지 |
| `name` | CharField | 실명 |
| `badminton_level` | CharField | 배드민턴 레벨 (beginner/D-S/master) |
| `gender` | CharField | 성별 (male/female/other/unknown) |
| `age_range` | CharField | 연령대 |
| `birthday` | DateField | 생일 |
| `birth_year` | PositiveIntegerField | 출생년도 |
| `phone_number` | CharField | 연락처 |
| `shipping_receiver` | CharField | 배송 수령인 |
| `shipping_phone_number` | CharField | 배송 연락처 |
| `shipping_address` | TextField | 배송 주소 |

---

### UserBlock (차단)

| 필드 | 타입 | 설명 |
|-----|------|------|
| `blocker` | ForeignKey | 차단한 사용자 |
| `blocked` | ForeignKey | 차단된 사용자 |
| `created_at` | DateTimeField | 차단 일시 |

---

### Report (신고)

| 필드 | 타입 | 설명 |
|-----|------|------|
| `reporter` | ForeignKey | 신고자 |
| `report_type` | CharField | 신고 유형 (user/post/comment/band/other) |
| `target_id` | PositiveIntegerField | 신고 대상 ID |
| `reason` | TextField | 신고 사유 |
| `status` | CharField | 상태 (pending/reviewing/resolved/rejected) |
| `admin_note` | TextField | 관리자 메모 |
| `processed_by` | ForeignKey | 처리 관리자 |

---

### Inquiry (문의)

| 필드 | 타입 | 설명 |
|-----|------|------|
| `user` | ForeignKey | 문의자 |
| `category` | CharField | 카테고리 (general/technical/bug/suggestion/other) |
| `title` | CharField | 제목 |
| `content` | TextField | 내용 |
| `status` | CharField | 상태 (pending/answered/closed) |
| `admin_response` | TextField | 관리자 답변 |
| `answered_by` | ForeignKey | 답변 관리자 |

---

## 에러 처리

### 공통 에러 응답 형식

```json
{
  "success": false,
  "error": "에러 메시지"
}
```

### 에러 코드

#### 소셜 로그인 API

| 상황 | HTTP 상태 | 에러 메시지 |
|------|----------|------------|
| access_token 누락 | 400 | "access_token이 필요합니다" |
| 소셜 API 오류 | 500 | "카카오 사용자 정보를 가져오는데 실패했습니다" |
| 이메일 미인증 (Google) | 400 | "인증되지 않은 이메일입니다" |
| 서버 오류 | 500 | "서버 오류가 발생했습니다: {상세내용}" |

#### 프로필 API

| 상황 | HTTP 상태 | 에러 메시지 |
|------|----------|------------|
| 미로그인 | 401 | "로그인이 필요합니다" |
| JSON 파싱 실패 | 400 | "잘못된 JSON 형식입니다" |
| 생일 형식 오류 | 400 | "생일 형식이 올바르지 않습니다 (YYYY-MM-DD)" |
| 출생연도 형식 오류 | 400 | "출생연도는 숫자여야 합니다" |

#### 사용자 차단 API

| 상황 | HTTP 상태 | 에러 메시지 |
|------|----------|------------|
| 미로그인 | 401 | "로그인이 필요합니다" |
| user_id 누락 | 400 | "user_id가 필요합니다" |
| 자기 자신 차단 시도 | 400 | "자기 자신을 차단할 수 없습니다" |
| 이미 차단됨 | 400 | "이미 차단한 사용자입니다" |
| 사용자 없음 | 404 | "사용자를 찾을 수 없습니다" |
| 차단 정보 없음 | 404 | "차단 정보를 찾을 수 없습니다" |

#### 신고 API

| 상황 | HTTP 상태 | 에러 메시지 |
|------|----------|------------|
| 미로그인 | 401 | "로그인이 필요합니다" |
| 필수 필드 누락 | 400 | "report_type, target_id, reason이 필요합니다" |
| 잘못된 신고 유형 | 400 | "유효하지 않은 신고 유형입니다" |

#### 문의 API

| 상황 | HTTP 상태 | 에러 메시지 |
|------|----------|------------|
| 미로그인 | 401 | "로그인이 필요합니다" |
| 필수 필드 누락 | 400 | "title과 content가 필요합니다" |
| 잘못된 카테고리 | 400 | "유효하지 않은 카테고리입니다" |
| 문의 없음 | 404 | "문의를 찾을 수 없습니다" |

---

## 보안 고려사항

1. **CSRF 보호**: 모바일 API 엔드포인트는 `@csrf_exempt` 적용
2. **OAuth State**: 웹 OAuth 플로우에서 CSRF 방지를 위한 state 파라미터 사용
3. **비밀번호**: 소셜 로그인 사용자는 `set_unusable_password()` 적용
4. **이메일 기반 인증**: username 대신 email을 고유 식별자로 사용

---

## 예제 코드

### Flutter에서 카카오 로그인

```dart
Future<Map<String, dynamic>> kakaoMobileLogin(String accessToken) async {
  final response = await http.post(
    Uri.parse('$baseUrl/accounts/api/kakao/mobile/'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'access_token': accessToken}),
  );

  return jsonDecode(response.body);
}
```

### JavaScript에서 세션 유지

```javascript
async function loginWithKakao(accessToken) {
  const response = await fetch('/accounts/api/kakao/mobile/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ access_token: accessToken }),
    credentials: 'include'  // 세션 쿠키 포함
  });

  return response.json();
}
```

### Flutter에서 프로필 조회

```dart
Future<Map<String, dynamic>> getProfile(String sessionId) async {
  final response = await http.get(
    Uri.parse('$baseUrl/accounts/api/profile/'),
    headers: {'Cookie': 'sessionid=$sessionId'},
  );

  return jsonDecode(response.body);
}
```

### Flutter에서 프로필 수정

```dart
Future<Map<String, dynamic>> updateProfile({
  required String sessionId,
  String? activityName,
  String? name,
  String? badmintonLevel,
  String? gender,
}) async {
  final body = <String, dynamic>{};
  if (activityName != null) body['activity_name'] = activityName;
  if (name != null) body['name'] = name;
  if (badmintonLevel != null) body['badminton_level'] = badmintonLevel;
  if (gender != null) body['gender'] = gender;

  final response = await http.put(
    Uri.parse('$baseUrl/accounts/api/profile/'),
    headers: {
      'Content-Type': 'application/json',
      'Cookie': 'sessionid=$sessionId',
    },
    body: jsonEncode(body),
  );

  return jsonDecode(response.body);
}
```

### Flutter에서 프로필 이미지 업로드

```dart
Future<Map<String, dynamic>> uploadProfileImage({
  required String sessionId,
  required File imageFile,
}) async {
  final request = http.MultipartRequest(
    'PUT',
    Uri.parse('$baseUrl/accounts/api/profile/'),
  );

  request.headers['Cookie'] = 'sessionid=$sessionId';
  request.files.add(await http.MultipartFile.fromPath(
    'profile_image',
    imageFile.path,
  ));

  final streamedResponse = await request.send();
  final response = await http.Response.fromStream(streamedResponse);

  return jsonDecode(response.body);
}
```

### JavaScript에서 프로필 조회/수정

```javascript
// 프로필 조회
async function getProfile() {
  const response = await fetch('/accounts/api/profile/', {
    method: 'GET',
    credentials: 'include'
  });
  return response.json();
}

// 프로필 수정
async function updateProfile(data) {
  const response = await fetch('/accounts/api/profile/', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    credentials: 'include'
  });
  return response.json();
}

// 프로필 이미지 업로드
async function uploadProfileImage(file) {
  const formData = new FormData();
  formData.append('profile_image', file);

  const response = await fetch('/accounts/api/profile/', {
    method: 'PUT',
    body: formData,
    credentials: 'include'
  });
  return response.json();
}
```
