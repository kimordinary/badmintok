# GitHub Secrets 설정 가이드

이 문서는 GitHub Actions를 통한 자동 배포를 위해 필요한 GitHub Secrets 설정 방법을 설명합니다.

## 📋 목차

1. [GitHub Secrets 접근 방법](#github-secrets-접근-방법)
2. [필수 Secrets 목록](#필수-secrets-목록)
3. [Secrets 설정 방법](#secrets-설정-방법)
4. [Django Secret Key 생성](#django-secret-key-생성)
5. [보안 주의사항](#보안-주의사항)

---

## 🔐 GitHub Secrets 접근 방법

1. GitHub 저장소로 이동
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 버튼 클릭하여 각 Secret 추가

---

## ✅ 필수 Secrets 목록

### 1. 서버 연결 정보

| Secret 이름 | 설명 | 예시 | 필수 |
|------------|------|------|------|
| `LIGHTSAIL_HOST` | Lightsail 서버 IP 주소 | `52.79.209.4` | ✅ |
| `LIGHTSAIL_USER` | SSH 사용자 이름 | `ec2-user` | ✅ |
| `LIGHTSAIL_SSH_KEY` | SSH 개인 키 전체 내용 | `-----BEGIN RSA...` | ✅ |
| `LIGHTSAIL_SSH_PORT` | SSH 포트 | `22` | ❌ (기본값: 22) |

### 2. Django 설정

| Secret 이름 | 설명 | 예시 | 필수 |
|------------|------|------|------|
| `DJANGO_SECRET_KEY` | Django Secret Key | `django-insecure-...` | ✅ |
| `DJANGO_DEBUG` | 디버그 모드 | `False` | ❌ (기본값: False) |
| `DJANGO_ALLOWED_HOSTS` | 허용된 호스트 (쉼표로 구분) | `badmintok.com,www.badmintok.com,52.79.209.4` | ✅ |

### 3. 데이터베이스 설정

| Secret 이름 | 설명 | 예시 | 필수 |
|------------|------|------|------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 비밀번호 | `강력한-비밀번호` | ✅ |
| `MYSQL_DATABASE` | 데이터베이스 이름 | `badmintok` | ❌ (기본값: badmintok) |
| `MYSQL_USER` | 데이터베이스 사용자 | `badmintok_user` | ❌ (기본값: badmintok_user) |
| `MYSQL_PASSWORD` | 데이터베이스 비밀번호 | `강력한-비밀번호` | ✅ |
| `DB_HOST` | 데이터베이스 호스트 | `db` | ❌ (기본값: db) |
| `DB_PORT` | 데이터베이스 포트 | `3306` | ❌ (기본값: 3306) |
| `DB_NAME` | 데이터베이스 이름 | `badmintok` | ❌ (기본값: badmintok) |
| `DB_USER` | 데이터베이스 사용자 | `badmintok_user` | ❌ (기본값: badmintok_user) |
| `DB_PASSWORD` | 데이터베이스 비밀번호 | `강력한-비밀번호` | ✅ |

**참고**: `MYSQL_PASSWORD`와 `DB_PASSWORD`는 동일한 값으로 설정하세요.

### 4. 카카오 OAuth 설정

| Secret 이름 | 설명 | 예시 | 필수 |
|------------|------|------|------|
| `KAKAO_REST_API_KEY` | 카카오 REST API 키 | `카카오-개발자-센터에서-발급` | ✅ |
| `KAKAO_REDIRECT_URI` | 카카오 리다이렉트 URI | `https://badmintok.com/accounts/kakao` | ✅ |

### 5. 서버 설정 (선택사항)

| Secret 이름 | 설명 | 기본값 | 필수 |
|------------|------|--------|------|
| `NGINX_HTTP_PORT` | Nginx HTTP 포트 | `80` | ❌ |
| `GUNICORN_WORKERS` | Gunicorn 워커 수 | `3` | ❌ |
| `GUNICORN_TIMEOUT` | Gunicorn 타임아웃 (초) | `120` | ❌ |
| `GUNICORN_LOG_LEVEL` | Gunicorn 로그 레벨 | `info` | ❌ |
| `GUNICORN_MAX_REQUESTS` | Gunicorn 최대 요청 수 | `1000` | ❌ |
| `GUNICORN_MAX_REQUESTS_JITTER` | Gunicorn 요청 지터 | `50` | ❌ |
| `TZ` | 시간대 | `Asia/Seoul` | ❌ |

---

## 📝 Secrets 설정 방법

### 1. Django Secret Key 생성

로컬 컴퓨터에서 다음 명령어 실행:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

생성된 키를 복사하여 `DJANGO_SECRET_KEY` Secret에 추가합니다.

### 2. 데이터베이스 비밀번호 생성

강력한 비밀번호를 생성하여 다음 Secrets에 설정:
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `DB_PASSWORD` (위와 동일한 값)

**비밀번호 생성 예시**:
```bash
# Linux/Mac
openssl rand -base64 32

# 또는 온라인 비밀번호 생성기 사용
```

### 3. 카카오 OAuth 설정

1. [카카오 개발자 센터](https://developers.kakao.com/) 접속
2. 애플리케이션 생성 및 설정
3. REST API 키 복사하여 `KAKAO_REST_API_KEY`에 추가
4. 리다이렉트 URI 설정: `https://badmintok.com/accounts/kakao`
5. `KAKAO_REDIRECT_URI` Secret에 동일한 URI 추가

### 4. SSH 키 설정

로컬 컴퓨터에서:

```bash
# SSH 키 생성 (없는 경우)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 공개 키를 서버에 추가
ssh-copy-id ec2-user@52.79.209.4

# 개인 키 내용 확인 (전체 내용 복사)
cat ~/.ssh/id_rsa
```

개인 키의 **전체 내용**을 복사하여 `LIGHTSAIL_SSH_KEY` Secret에 추가합니다.

---

## 🔒 보안 주의사항

### ✅ 권장 사항

1. **강력한 비밀번호 사용**
   - 최소 16자 이상
   - 대소문자, 숫자, 특수문자 포함
   - 예측 불가능한 랜덤 문자열

2. **Secret Key 보안**
   - Django Secret Key는 절대 공개하지 않음
   - Git 저장소에 커밋하지 않음
   - 정기적으로 변경 (선택사항)

3. **SSH 키 보안**
   - 개인 키는 절대 공유하지 않음
   - 비밀번호로 SSH 키 보호 (선택사항)
   - 정기적으로 키 로테이션

4. **데이터베이스 비밀번호**
   - 각 환경별로 다른 비밀번호 사용
   - 정기적으로 변경

### ❌ 하지 말아야 할 것

- ❌ Secrets를 코드에 하드코딩
- ❌ Secrets를 Git에 커밋
- ❌ Secrets를 로그에 출력
- ❌ 약한 비밀번호 사용
- ❌ 동일한 비밀번호 재사용

---

## 📋 설정 체크리스트

배포 전 다음 항목들을 확인하세요:

- [ ] `LIGHTSAIL_HOST` 설정 완료
- [ ] `LIGHTSAIL_USER` 설정 완료
- [ ] `LIGHTSAIL_SSH_KEY` 설정 완료 (전체 내용)
- [ ] `DJANGO_SECRET_KEY` 생성 및 설정 완료
- [ ] `DJANGO_DEBUG`를 `False`로 설정
- [ ] `DJANGO_ALLOWED_HOSTS` 정확히 설정
- [ ] `MYSQL_ROOT_PASSWORD` 강력한 비밀번호로 설정
- [ ] `MYSQL_PASSWORD` 강력한 비밀번호로 설정
- [ ] `DB_PASSWORD` 강력한 비밀번호로 설정 (위와 동일)
- [ ] `KAKAO_REST_API_KEY` 설정 완료
- [ ] `KAKAO_REDIRECT_URI` 정확히 설정
- [ ] SSH 키가 서버에 추가되었는지 확인

---

## 🚀 설정 완료 후

모든 Secrets를 설정한 후:

1. GitHub Actions 워크플로우 실행
2. 배포 로그에서 `.env.prod` 파일 생성 확인
3. 서버에서 `.env.prod` 파일 확인 (선택사항)

```bash
# 서버에서 확인 (선택사항)
ssh ec2-user@52.79.209.4
cat ~/badmintok/.env.prod
```

---

## 🔄 Secrets 업데이트

Secrets를 업데이트하려면:

1. GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions**
2. 업데이트할 Secret 클릭
3. **Update** 버튼 클릭
4. 새 값 입력 및 저장
5. 다음 배포 시 자동으로 적용됨

---

## 📞 문제 해결

### Secret이 적용되지 않는 경우

1. Secret 이름이 정확한지 확인 (대소문자 구분)
2. Secret 값에 공백이나 특수문자가 없는지 확인
3. GitHub Actions 로그에서 오류 확인
4. 워크플로우를 다시 실행

### 배포 실패 시

1. GitHub Actions 로그 확인
2. `.env.prod` 파일 생성 여부 확인
3. 필수 Secrets가 모두 설정되었는지 확인
4. Secret 값의 형식이 올바른지 확인

---

**모든 Secrets 설정이 완료되면 자동 배포가 가능합니다!** 🎉

