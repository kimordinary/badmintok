# Accounts API 테스트 가이드

이 문서는 배드민톡 Accounts API를 테스트하는 방법을 안내합니다.

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
http://localhost:8000/api/auth/
```

프로덕션 환경에서는 실제 도메인으로 변경하세요.

### Content-Type
모든 요청은 `application/json` 형식을 사용합니다.

---

## 인증 방식

이 API는 **JWT (JSON Web Token)** 인증 방식을 사용합니다.

### 토큰 종류

1. **Access Token**: API 요청 시 사용 (만료 시간: 1시간)
2. **Refresh Token**: Access Token 갱신 시 사용 (만료 시간: 7일)

### 인증 헤더 형식

인증이 필요한 API 호출 시 다음과 같이 헤더에 토큰을 포함해야 합니다:

```
Authorization: Bearer {access_token}
```

예시:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## API 엔드포인트

### 1. 회원가입

회원가입을 수행하고 JWT 토큰을 발급받습니다.

**엔드포인트:** `POST /api/auth/signup/`

**인증:** 불필요

**요청 본문:**
```json
{
  "email": "user@example.com",
  "activity_name": "홍길동",
  "password": "securepassword123",
  "password2": "securepassword123",
  "terms_agreed": true,
  "privacy_agreed": true
}
```

**성공 응답 (201 Created):**
```json
{
  "message": "회원가입이 완료되었습니다.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "홍길동",
    "auth_provider": null,
    "profile_image_url": "/static/images/userprofile/user.png",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**오류 응답 (400 Bad Request):**
```json
{
  "email": ["이미 사용 중인 이메일입니다."],
  "password2": ["비밀번호와 비밀번호 확인이 일치하지 않습니다."]
}
```

---

### 2. 로그인

이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.

**엔드포인트:** `POST /api/auth/login/`

**인증:** 불필요

**요청 본문:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**성공 응답 (200 OK):**
```json
{
  "message": "로그인되었습니다.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "홍길동",
    "auth_provider": null,
    "profile_image_url": "/static/images/userprofile/user.png",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**오류 응답 (400 Bad Request):**
```json
{
  "error": "이메일 또는 비밀번호가 올바르지 않습니다."
}
```

---

### 3. 로그아웃

로그아웃합니다. (클라이언트에서 토큰 삭제 필요)

**엔드포인트:** `POST /api/auth/logout/`

**인증:** 필요 (Bearer Token)

**요청 본문:**
없음 (또는 빈 객체 `{}`)

**성공 응답 (200 OK):**
```json
{
  "message": "로그아웃되었습니다. 토큰을 삭제해주세요."
}
```

---

### 4. 토큰 갱신

만료된 Access Token을 Refresh Token으로 갱신합니다.

**엔드포인트:** `POST /api/auth/refresh/`

**인증:** 불필요

**요청 본문:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**성공 응답 (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**오류 응답 (400 Bad Request):**
```json
{
  "error": "유효하지 않은 토큰입니다."
}
```

---

### 5. 현재 사용자 정보 조회

현재 로그인한 사용자의 정보를 조회합니다.

**엔드포인트:** `GET /api/auth/user/`

**인증:** 필요 (Bearer Token)

**요청 본문:** 없음

**성공 응답 (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "activity_name": "홍길동",
  "auth_provider": null,
  "profile_image_url": "/static/images/userprofile/user.png",
  "date_joined": "2024-01-01T00:00:00Z"
}
```

**오류 응답 (401 Unauthorized):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

### 6. 카카오 소셜 로그인

카카오 액세스 토큰으로 로그인합니다.

**엔드포인트:** `POST /api/auth/kakao/`

**인증:** 불필요

**요청 본문:**
```json
{
  "access_token": "카카오에서_발급받은_액세스_토큰"
}
```

**성공 응답 (200 OK):**
```json
{
  "message": "카카오 계정으로 로그인되었습니다.",
  "user": {
    "id": 1,
    "email": "kakao@example.com",
    "activity_name": "카카오사용자",
    "auth_provider": "kakao",
    "profile_image_url": "/media/images/userprofile/kakao_1.jpg",
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**오류 응답 (400 Bad Request):**
```json
{
  "error": "카카오 사용자 정보를 가져오는 데 실패했습니다."
}
```

---

## 테스트 방법

### 1. cURL 사용

#### 회원가입
```bash
curl -X POST http://localhost:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "activity_name": "테스트사용자",
    "password": "testpassword123",
    "password2": "testpassword123",
    "terms_agreed": true,
    "privacy_agreed": true
  }'
```

#### 로그인
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

#### 사용자 정보 조회 (인증 필요)
```bash
curl -X GET http://localhost:8000/api/auth/user/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 토큰 갱신
```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

---

### 2. Postman 사용

#### 설정 방법

1. **새 요청 생성**
   - Method: POST/GET 선택
   - URL: `http://localhost:8000/api/auth/{endpoint}/`

2. **Headers 설정**
   - `Content-Type`: `application/json`
   - 인증이 필요한 경우: `Authorization`: `Bearer {access_token}`

3. **Body 설정 (POST 요청)**
   - Body 탭 선택
   - `raw` 선택
   - JSON 형식 선택
   - 요청 본문 입력

#### 환경 변수 설정 (선택사항)

Postman에서 환경 변수를 설정하면 토큰을 재사용할 수 있습니다:

1. 환경 변수 생성:
   - `base_url`: `http://localhost:8000/api/auth`
   - `access_token`: (로그인 후 설정)
   - `refresh_token`: (로그인 후 설정)

2. URL에서 사용:
   - `{{base_url}}/login/`

3. Authorization에서 사용:
   - Type: Bearer Token
   - Token: `{{access_token}}`

---

### 3. Python Requests 사용

```python
import requests

BASE_URL = "http://localhost:8000/api/auth"

# 1. 회원가입
signup_data = {
    "email": "test@example.com",
    "activity_name": "테스트사용자",
    "password": "testpassword123",
    "password2": "testpassword123",
    "terms_agreed": True,
    "privacy_agreed": True
}

response = requests.post(f"{BASE_URL}/signup/", json=signup_data)
print(response.json())

# 2. 로그인
login_data = {
    "email": "test@example.com",
    "password": "testpassword123"
}

response = requests.post(f"{BASE_URL}/login/", json=login_data)
data = response.json()
access_token = data["tokens"]["access"]
refresh_token = data["tokens"]["refresh"]

# 3. 사용자 정보 조회
headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(f"{BASE_URL}/user/", headers=headers)
print(response.json())

# 4. 토큰 갱신
refresh_data = {
    "refresh": refresh_token
}

response = requests.post(f"{BASE_URL}/refresh/", json=refresh_data)
new_access_token = response.json()["access"]
```

---

### 4. JavaScript (Fetch API) 사용

```javascript
const BASE_URL = 'http://localhost:8000/api/auth';

// 1. 회원가입
async function signup() {
  const response = await fetch(`${BASE_URL}/signup/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'test@example.com',
      activity_name: '테스트사용자',
      password: 'testpassword123',
      password2: 'testpassword123',
      terms_agreed: true,
      privacy_agreed: true,
    }),
  });
  
  const data = await response.json();
  console.log(data);
  
  // 토큰 저장 (로컬 스토리지 등)
  if (data.tokens) {
    localStorage.setItem('access_token', data.tokens.access);
    localStorage.setItem('refresh_token', data.tokens.refresh);
  }
}

// 2. 로그인
async function login() {
  const response = await fetch(`${BASE_URL}/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'test@example.com',
      password: 'testpassword123',
    }),
  });
  
  const data = await response.json();
  console.log(data);
  
  if (data.tokens) {
    localStorage.setItem('access_token', data.tokens.access);
    localStorage.setItem('refresh_token', data.tokens.refresh);
  }
}

// 3. 사용자 정보 조회
async function getUserInfo() {
  const accessToken = localStorage.getItem('access_token');
  
  const response = await fetch(`${BASE_URL}/user/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  const data = await response.json();
  console.log(data);
}

// 4. 토큰 갱신
async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch(`${BASE_URL}/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh: refreshToken,
    }),
  });
  
  const data = await response.json();
  
  if (data.access) {
    localStorage.setItem('access_token', data.access);
  }
}
```

---

## 오류 응답

### 공통 오류 코드

| 상태 코드 | 의미 | 설명 |
|---------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 생성 성공 (회원가입) |
| 400 | Bad Request | 잘못된 요청 (입력값 오류 등) |
| 401 | Unauthorized | 인증 필요 또는 인증 실패 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 오류 |

### 오류 응답 예시

#### 400 Bad Request
```json
{
  "email": ["이 필드는 필수입니다."],
  "password": ["이 필드는 필수입니다."]
}
```

#### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

또는

```json
{
  "detail": "Given token not valid for any token type"
}
```

---

## 테스트 시나리오

### 시나리오 1: 정상적인 회원가입 및 로그인 플로우

1. **회원가입**
   ```bash
   POST /api/auth/signup/
   ```
   - 응답에서 `access_token`과 `refresh_token` 저장

2. **사용자 정보 조회**
   ```bash
   GET /api/auth/user/
   Authorization: Bearer {access_token}
   ```

3. **토큰 갱신 (Access Token 만료 시)**
   ```bash
   POST /api/auth/refresh/
   ```
   - 새로운 `access_token` 받아서 저장

4. **로그아웃**
   ```bash
   POST /api/auth/logout/
   Authorization: Bearer {access_token}
   ```
   - 클라이언트에서 토큰 삭제

### 시나리오 2: 오류 케이스 테스트

1. **중복 이메일로 회원가입 시도**
   - 기존 사용자와 동일한 이메일로 회원가입
   - 400 오류 및 오류 메시지 확인

2. **잘못된 비밀번호로 로그인 시도**
   - 존재하지 않는 이메일 또는 잘못된 비밀번호
   - 400 오류 및 오류 메시지 확인

3. **만료된 토큰으로 API 호출**
   - 만료된 Access Token 사용
   - 401 오류 확인

4. **토큰 없이 인증 필요한 API 호출**
   - Authorization 헤더 없이 `/api/auth/user/` 호출
   - 401 오류 확인

---

## 주의사항

1. **비밀번호 정책**
   - 최소 8자 이상
   - Django의 기본 비밀번호 검증 규칙 적용

2. **토큰 저장**
   - Access Token과 Refresh Token을 안전하게 저장하세요 (모바일: Keychain/Keystore, 웹: Secure Cookie)
   - Access Token은 만료 시간이 짧으므로 (1시간) 만료 시 Refresh Token으로 갱신

3. **CORS 설정**
   - 개발 환경에서는 모든 origin 허용
   - 프로덕션 환경에서는 특정 도메인만 허용하도록 설정 필요

4. **카카오 로그인**
   - 카카오 개발자 콘솔에서 앱 설정 필요
   - Redirect URI 설정 필요 (웹용과 API용 구분)

---

## 추가 정보

### 환경 변수

필요한 환경 변수:
- `KAKAO_REST_API_KEY`: 카카오 REST API 키
- `KAKAO_CLIENT_SECRET`: 카카오 Client Secret (선택)
- `KAKAO_REDIRECT_URI`: 카카오 리다이렉트 URI

### 지원 문의

API 관련 문의사항이 있으시면 관리자에게 문의하세요.

