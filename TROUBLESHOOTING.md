# 문제 해결 가이드

## 문제 1: Nginx가 실행됐다 안됐다 반복되는 문제

### 원인
nginx 설정 디렉토리에 `badmintok.conf` (개발용)와 `badmintok-prod.conf` (프로덕션용) 두 파일이 모두 있었고, nginx가 두 파일을 모두 읽으려고 했습니다. 프로덕션 설정 파일이 먼저 로드되면서 `badmintok-web-prod` 컨테이너를 찾으려 했지만, 개발 환경에서는 `badmintok-web` 컨테이너만 실행 중이어서 오류가 발생했습니다.

### 해결 방법
`docker-compose.yml`에서 nginx 설정을 특정 파일만 마운트하도록 수정했습니다:

```yaml
volumes:
  # Nginx 설정 (개발 환경용 badmintok.conf만 마운트)
  - ./nginx/conf.d/badmintok.conf:/etc/nginx/conf.d/badmintok.conf:ro
```

이제 개발 환경에서는 `badmintok.conf`만 사용하고, 프로덕션 환경에서는 `badmintok-prod.conf`를 사용합니다.

## 문제 2: MySQL 컨테이너를 실행하지 않으면 데이터를 불러오지 못함

### 원인
1. **네트워크 연결 문제**: `mysql8` 컨테이너가 `badmintok_badmintok-net` 네트워크에 연결되어 있지 않으면, `badmintok-web` 컨테이너가 MySQL에 접근할 수 없습니다.

2. **의존성 문제**: `entrypoint.sh`에서 데이터베이스 연결을 확인하는데, MySQL이 실행되지 않으면 연결 실패로 인해 컨테이너가 시작되지 않거나 계속 재시도합니다.

3. **Healthcheck 실패**: web 컨테이너의 healthcheck가 실패하면 nginx가 시작되지 않습니다.

### 해결 방법

#### 1. MySQL 컨테이너 확인 및 시작
```bash
# MySQL 컨테이너 상태 확인
docker ps -a | findstr mysql8

# MySQL 컨테이너 시작 (중지된 경우)
docker start mysql8

# MySQL 컨테이너가 실행 중인지 확인
docker ps | findstr mysql8
```

#### 2. 네트워크 연결 확인 및 연결
```bash
# 네트워크 생성 (없는 경우)
docker network create badmintok_badmintok-net 2>$null

# MySQL 컨테이너를 네트워크에 연결
docker network connect badmintok_badmintok-net mysql8

# 연결 확인
docker network inspect badmintok_badmintok-net
```

#### 3. 서비스 시작 순서
```bash
# 1. MySQL 컨테이너 시작
docker start mysql8

# 2. MySQL이 네트워크에 연결되어 있는지 확인
docker network connect badmintok_badmintok-net mysql8 2>$null

# 3. Docker Compose 서비스 시작
docker-compose up -d
```

### 자동화 스크립트

Windows PowerShell에서 사용할 수 있는 시작 스크립트:

```powershell
# start-dev.ps1
Write-Host "=== Badmintok 개발 환경 시작 ===" -ForegroundColor Green

# 1. MySQL 컨테이너 확인 및 시작
Write-Host "`n[1/4] MySQL 컨테이너 확인 중..." -ForegroundColor Yellow
$mysql = docker ps -a --filter "name=mysql8" --format "{{.Names}}"
if (-not $mysql) {
    Write-Host "❌ MySQL 컨테이너(mysql8)를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "MySQL 컨테이너를 먼저 생성하거나 시작해주세요." -ForegroundColor Red
    exit 1
}

$mysqlStatus = docker ps --filter "name=mysql8" --format "{{.Status}}"
if (-not $mysqlStatus) {
    Write-Host "MySQL 컨테이너가 중지되어 있습니다. 시작 중..." -ForegroundColor Yellow
    docker start mysql8
    Start-Sleep -Seconds 3
}

# 2. 네트워크 확인 및 생성
Write-Host "`n[2/4] Docker 네트워크 확인 중..." -ForegroundColor Yellow
$network = docker network ls --filter "name=badmintok_badmintok-net" --format "{{.Name}}"
if (-not $network) {
    Write-Host "네트워크 생성 중..." -ForegroundColor Yellow
    docker network create badmintok_badmintok-net
}

# 3. MySQL을 네트워크에 연결
Write-Host "`n[3/4] MySQL 컨테이너를 네트워크에 연결 중..." -ForegroundColor Yellow
docker network connect badmintok_badmintok-net mysql8 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ MySQL 네트워크 연결 완료" -ForegroundColor Green
} else {
    Write-Host "⚠️  MySQL이 이미 네트워크에 연결되어 있거나 연결 중 오류 발생" -ForegroundColor Yellow
}

# 4. Docker Compose 서비스 시작
Write-Host "`n[4/4] Docker Compose 서비스 시작 중..." -ForegroundColor Yellow
docker-compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ 개발 환경이 성공적으로 시작되었습니다!" -ForegroundColor Green
    Write-Host "`n접속 주소:" -ForegroundColor Cyan
    Write-Host "  - 웹 애플리케이션: http://localhost" -ForegroundColor White
    Write-Host "  - Admin 페이지: http://localhost/admin" -ForegroundColor White
    Write-Host "`n로그 확인:" -ForegroundColor Cyan
    Write-Host "  docker-compose logs -f" -ForegroundColor White
} else {
    Write-Host "`n❌ 서비스 시작 중 오류가 발생했습니다." -ForegroundColor Red
    Write-Host "로그를 확인하세요: docker-compose logs" -ForegroundColor Yellow
    exit 1
}
```

### 문제 진단 체크리스트

1. **MySQL 컨테이너 상태 확인**
   ```bash
   docker ps | findstr mysql8
   ```
   - 실행 중이어야 함: `Up X minutes`

2. **네트워크 연결 확인**
   ```bash
   docker network inspect badmintok_badmintok-net
   ```
   - `mysql8`과 `badmintok-web`이 모두 네트워크에 연결되어 있어야 함

3. **Web 컨테이너 로그 확인**
   ```bash
   docker-compose logs web
   ```
   - "Database connection successful" 메시지가 있어야 함
   - "Database connection failed"가 반복되면 MySQL 연결 문제

4. **Nginx 컨테이너 로그 확인**
   ```bash
   docker-compose logs nginx
   ```
   - "host not found in upstream" 오류가 있으면 nginx 설정 문제
   - 정상적으로 시작되면 "Configuration complete; ready for start up" 메시지

5. **컨테이너 상태 확인**
   ```bash
   docker-compose ps
   ```
   - 모든 컨테이너가 `Up` 상태여야 함
   - `Restarting` 상태가 반복되면 문제 있음

### 일반적인 해결 방법

#### 문제: MySQL 연결 실패
```bash
# 1. MySQL 컨테이너 재시작
docker restart mysql8

# 2. 네트워크 재연결
docker network disconnect badmintok_badmintok-net mysql8
docker network connect badmintok_badmintok-net mysql8

# 3. Web 컨테이너 재시작
docker-compose restart web
```

#### 문제: Nginx가 계속 재시작됨
```bash
# 1. Nginx 설정 확인
docker-compose exec nginx nginx -t

# 2. Nginx 로그 확인
docker-compose logs nginx

# 3. Web 컨테이너가 healthy 상태인지 확인
docker-compose ps web

# 4. Nginx 재시작
docker-compose restart nginx
```

#### 문제: 모든 컨테이너 재시작
```bash
# 모든 서비스 중지
docker-compose down

# MySQL 네트워크 연결 확인
docker network connect badmintok_badmintok-net mysql8

# 서비스 재시작
docker-compose up -d
```
