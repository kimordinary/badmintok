# 로컬 개발 환경 가이드

## 로컬 PC에서 테스트하기

로컬 개발 환경에서는 `docker-compose.yml` 파일을 사용합니다.

### 1. 사전 준비

#### 필수 요구사항
- Docker Desktop 설치 및 실행
- 기존 MySQL 컨테이너 (`mysql8`) 실행 중

#### MySQL 컨테이너 확인
```bash
docker ps | findstr mysql8
```

MySQL 컨테이너가 실행 중이지 않다면:
```bash
docker start mysql8
```

### 2. 환경 변수 설정

`.env` 파일이 있는지 확인하세요. 없으면 생성:

```bash
# .env 파일 예시
DB_HOST=mysql8
DB_PORT=3306
DB_NAME=badmintok
DB_USER=root
DB_PASSWORD=1234

# Django 개발 환경 설정
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*

# Nginx 포트
NGINX_HTTP_PORT=80

# Gunicorn 설정 (개발 환경)
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=120
GUNICORN_LOG_LEVEL=debug
```

### 3. 네트워크 설정

기존 MySQL 컨테이너를 docker-compose 네트워크에 연결:

```bash
# 네트워크 생성 (이미 있으면 무시됨)
docker network create badmintok_badmintok-net 2>$null

# MySQL 컨테이너를 네트워크에 연결
docker network connect badmintok_badmintok-net mysql8
```

### 4. 서비스 시작

```bash
# 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f web
docker-compose logs -f nginx
```

### 5. 개발 워크플로우

#### 코드 변경 시
- 코드는 자동으로 마운트되어 있으므로 변경사항이 즉시 반영됩니다
- Python 파일 변경 시: Gunicorn이 자동으로 재시작됩니다 (--reload 옵션 필요 시 추가)
- 정적 파일 변경 시: `collectstatic` 실행 필요

#### 정적 파일 수집
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

#### 데이터베이스 마이그레이션
```bash
docker-compose exec web python manage.py migrate
```

#### Django 관리 명령어 실행
```bash
# Shell 접속
docker-compose exec web python manage.py shell

# Superuser 생성
docker-compose exec web python manage.py createsuperuser

# 특정 명령어 실행
docker-compose exec web python manage.py <command>
```

### 6. 서비스 관리

#### 서비스 시작
```bash
docker-compose up -d
```

#### 서비스 중지
```bash
docker-compose down
```

#### 서비스 재시작
```bash
docker-compose restart

# 특정 서비스만 재시작
docker-compose restart web
docker-compose restart nginx
```

#### 서비스 재빌드 (코드 변경 후)
```bash
docker-compose up -d --build
```

### 7. 접속 확인

- 웹 애플리케이션: http://localhost
- Admin 페이지: http://localhost/admin

### 8. 문제 해결

#### 컨테이너가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose logs

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 재생성
docker-compose up -d --force-recreate
```

#### MySQL 연결 문제
```bash
# MySQL 컨테이너가 네트워크에 연결되어 있는지 확인
docker network inspect badmintok_badmintok-net

# 네트워크에 연결
docker network connect badmintok_badmintok-net mysql8
```

#### 정적 파일이 보이지 않는 경우
```bash
# 정적 파일 재수집
docker-compose exec web python manage.py collectstatic --noinput --clear

# nginx 재시작
docker-compose restart nginx
```

#### 코드 변경이 반영되지 않는 경우
```bash
# 컨테이너 재시작
docker-compose restart web

# 또는 재빌드
docker-compose up -d --build web
```

### 9. 개발 vs 프로덕션 차이점

| 항목 | 개발 환경 (docker-compose.yml) | 프로덕션 환경 (docker-compose.prod.yml) |
|------|-------------------------------|----------------------------------------|
| 코드 마운트 | ✅ 자동 마운트 (즉시 반영) | ❌ 이미지에 포함 |
| DEBUG 모드 | True (기본값) | False |
| Gunicorn 워커 | 2개 (기본값) | 3개 (기본값) |
| 로그 레벨 | debug | info |
| MySQL 컨테이너 | 기존 mysql8 사용 | 새로 생성 (db) |
| 포트 노출 | 80 (nginx) | 80 (nginx) |

### 10. 유용한 명령어

```bash
# 실행 중인 컨테이너 확인
docker-compose ps

# 컨테이너 내부 접속
docker-compose exec web bash
docker-compose exec nginx sh

# 볼륨 확인
docker volume ls

# 네트워크 확인
docker network ls
docker network inspect badmintok_badmintok-net

# 리소스 사용량 확인
docker stats

# 모든 컨테이너 및 볼륨 정리 (주의: 데이터 삭제됨)
docker-compose down -v
```

### 11. 빠른 시작 스크립트

Windows PowerShell에서 사용할 수 있는 스크립트:

```powershell
# start-dev.ps1
Write-Host "Starting development environment..."

# MySQL 컨테이너 확인 및 시작
$mysql = docker ps -a --filter "name=mysql8" --format "{{.Names}}"
if (-not $mysql) {
    Write-Host "MySQL container not found. Please start it first."
    exit 1
}

# 네트워크 연결 확인
docker network connect badmintok_badmintok-net mysql8 2>$null

# 서비스 시작
docker-compose up -d --build

Write-Host "Development environment started!"
Write-Host "Access: http://localhost"
```

### 12. 주의사항

1. **포트 충돌**: 80번 포트가 이미 사용 중이면 `.env` 파일에서 `NGINX_HTTP_PORT`를 변경하세요
2. **MySQL 연결**: MySQL 컨테이너가 실행 중이고 네트워크에 연결되어 있어야 합니다
3. **코드 변경**: Python 파일 변경 시 Gunicorn이 자동으로 재시작되지 않을 수 있으므로, 필요시 컨테이너를 재시작하세요
4. **정적 파일**: 개발 중 정적 파일을 변경했다면 `collectstatic`을 실행하거나 nginx를 재시작하세요
