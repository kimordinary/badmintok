# Badmintok Production Deployment Guide

## 📋 목차
1. [준비사항](#준비사항)
2. [환경 변수 설정](#환경-변수-설정)
3. [Django Settings 수정](#django-settings-수정)
4. [배포 실행](#배포-실행)
5. [배포 후 확인](#배포-후-확인)
6. [트러블슈팅](#트러블슈팅)
7. [보안 체크리스트](#보안-체크리스트)

---

## 🚀 준비사항

### 1. 필수 소프트웨어
- Docker (20.10 이상)
- Docker Compose (2.0 이상)

### 2. 서버 요구사항
- **최소**: CPU 2코어, RAM 2GB, 디스크 20GB
- **권장**: CPU 4코어, RAM 4GB, 디스크 50GB
- OS: Ubuntu 20.04 LTS 이상 또는 다른 Linux 배포판

---

## 🔧 환경 변수 설정

### 1. `.env.prod` 파일 생성

```bash
# .env.prod.example을 복사하여 .env.prod 생성
cp .env.prod.example .env.prod
```

### 2. 중요 환경 변수 수정

#### **반드시 변경해야 할 항목:**

```bash
# Django Secret Key 생성 (새로운 키 생성)
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# .env.prod 파일 수정
DJANGO_SECRET_KEY=<생성된-새로운-키>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database 비밀번호 (강력한 비밀번호로 변경)
MYSQL_ROOT_PASSWORD=<강력한-비밀번호>
MYSQL_PASSWORD=<강력한-비밀번호>
DB_PASSWORD=<강력한-비밀번호>

# Kakao OAuth
KAKAO_REST_API_KEY=<실제-API-키>
KAKAO_REDIRECT_URI=https://yourdomain.com/accounts/kakao
```

---

## ⚙️ Django Settings 수정

### `badmintok/settings.py` 파일에서 수정이 필요한 항목:

```python
import os

# SECRET_KEY를 환경 변수에서 가져오도록 수정
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key')

# DEBUG를 환경 변수에서 가져오도록 수정
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# ALLOWED_HOSTS를 환경 변수에서 가져오도록 수정
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# CSRF 설정 (HTTPS 사용 시)
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False  # Nginx에서 처리하므로 False
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTPS 관련 설정 (SSL 사용 시)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1년
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'

# 로깅 설정 추가
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
```

---

## 🚢 배포 실행

### 1. 프로젝트 디렉토리로 이동

```bash
cd /path/to/badmintok_sever/badmintok
```

### 2. Docker 이미지 빌드 및 컨테이너 실행

```bash
# 백그라운드에서 실행
docker-compose -f docker-compose.prod.yml up -d --build

# 또는 포그라운드에서 로그 확인하며 실행
docker-compose -f docker-compose.prod.yml up --build
```

### 3. 로그 확인

```bash
# 전체 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그만 확인
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f db
```

---

## ✅ 배포 후 확인

### 1. 서비스 상태 확인

```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 모든 컨테이너가 'Up (healthy)' 상태여야 함
```

### 2. 웹사이트 접속 확인

```bash
# 로컬에서 테스트
curl http://localhost

# 또는 브라우저에서
http://your-server-ip
```

### 3. Admin 페이지 접속

```bash
# Admin 페이지 확인
http://your-server-ip/admin/
```

### 4. 정적 파일 확인

```bash
# 정적 파일이 제대로 로드되는지 확인
http://your-server-ip/static/css/style.css
```

### 5. Database 마이그레이션 확인

```bash
# Django 컨테이너 내부에서 확인
docker-compose -f docker-compose.prod.yml exec web python manage.py showmigrations
```

### 6. Superuser 생성 (처음 배포 시)

```bash
# 수동으로 superuser 생성
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# 또는 .env.prod에 환경 변수 설정 후 재시작
# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_EMAIL=admin@example.com
# DJANGO_SUPERUSER_PASSWORD=your-password
```

---

## 🔄 업데이트 및 재배포

### 코드 업데이트 후 재배포

```bash
# Git에서 최신 코드 가져오기
git pull origin main

# 컨테이너 재빌드 및 재시작
docker-compose -f docker-compose.prod.yml up -d --build

# 또는 다운타임 최소화를 위해
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Database 마이그레이션만 실행

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 정적 파일만 다시 수집

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

---

## 🛑 서비스 중지 및 제거

### 서비스 중지

```bash
# 컨테이너 중지
docker-compose -f docker-compose.prod.yml stop

# 컨테이너 중지 및 제거
docker-compose -f docker-compose.prod.yml down

# 컨테이너, 볼륨, 네트워크 모두 제거 (주의: 데이터 삭제됨)
docker-compose -f docker-compose.prod.yml down -v
```

---

## 🐛 트러블슈팅

### 1. 컨테이너가 시작되지 않는 경우

```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml logs

# 특정 컨테이너 로그 확인
docker-compose -f docker-compose.prod.yml logs web
```

### 2. Database 연결 오류

```bash
# Database 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps db

# Database 로그 확인
docker-compose -f docker-compose.prod.yml logs db

# Database 연결 테스트
docker-compose -f docker-compose.prod.yml exec web python manage.py dbshell
```

### 3. 정적 파일이 로드되지 않는 경우

```bash
# 정적 파일 볼륨 확인
docker volume ls | grep static

# 정적 파일 재수집
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput --clear

# Nginx 재시작
docker-compose -f docker-compose.prod.yml restart nginx
```

### 4. 500 Internal Server Error

```bash
# Django 로그 확인
docker-compose -f docker-compose.prod.yml logs -f web

# DEBUG=True로 임시 변경하여 에러 확인 (프로덕션에서는 권장하지 않음)
# .env.prod에서 DJANGO_DEBUG=True로 변경 후 재시작
```

### 5. 성능 문제

```bash
# Gunicorn worker 수 증가
# .env.prod에서 GUNICORN_WORKERS=5 (CPU 코어 수 * 2 + 1)

# 컨테이너 리소스 사용량 확인
docker stats
```

---

## 🔒 보안 체크리스트

### 배포 전 필수 체크

- [ ] `DJANGO_DEBUG=False` 설정 확인
- [ ] `DJANGO_SECRET_KEY` 변경 확인
- [ ] `DJANGO_ALLOWED_HOSTS` 정확히 설정
- [ ] Database 비밀번호 강력하게 설정
- [ ] `.env.prod` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] Database 포트(3306) 외부 노출 차단 확인
- [ ] Nginx 보안 헤더 설정 확인
- [ ] SSL/TLS 인증서 설정 (HTTPS)
- [ ] 정기적인 백업 계획 수립
- [ ] 방화벽 설정 (80, 443 포트만 허용)

### HTTPS 설정 (Let's Encrypt 사용)

```bash
# Certbot 설치 (Ubuntu)
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# nginx/conf.d/badmintok.conf에서 HTTPS 서버 블록 주석 해제
# docker-compose.prod.yml에서 HTTPS 포트 주석 해제
```

---

## 📊 모니터링 및 로그

### 로그 확인

```bash
# 실시간 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 특정 시간의 로그만 확인
docker-compose -f docker-compose.prod.yml logs --since 1h

# 로그 파일 위치
# Nginx: nginx_logs 볼륨
# Django: 컨테이너 stdout/stderr
```

### 백업

```bash
# Database 백업
docker-compose -f docker-compose.prod.yml exec db mysqldump -u root -p badmintok > backup_$(date +%Y%m%d_%H%M%S).sql

# Media 파일 백업
docker cp badmintok-web-prod:/app/media ./media_backup_$(date +%Y%m%d_%H%M%S)
```

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. Docker 및 Docker Compose 버전
2. 서버 리소스 (CPU, 메모리, 디스크)
3. 로그 파일
4. 환경 변수 설정

추가 도움이 필요하면 프로젝트 이슈 트래커를 확인하세요.
