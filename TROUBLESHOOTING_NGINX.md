# Nginx 컨테이너 문제 해결 가이드

Nginx 컨테이너가 계속 재시작되는 경우 다음을 확인하세요.

## 🔍 문제 진단

### 1. Nginx 로그 확인

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml --env-file .env.prod logs nginx
```

### 2. Nginx 설정 파일 검증

```bash
# Nginx 컨테이너 내부에서 설정 파일 검증
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -t
```

### 3. 포트 80 사용 확인

```bash
# 포트 80이 사용 중인지 확인
sudo netstat -tulpn | grep :80
# 또는
sudo ss -tulpn | grep :80

# 다른 프로세스가 포트 80을 사용 중이면 중지
sudo systemctl stop httpd 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
```

### 4. Nginx 컨테이너 상태 확인

```bash
docker ps -a | grep nginx
docker inspect badmintok-nginx-prod | grep -A 10 "State"
```

## 🛠️ 해결 방법

### 방법 1: Nginx 컨테이너 재시작

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml --env-file .env.prod restart nginx
```

### 방법 2: Nginx 컨테이너 재생성

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate nginx
```

### 방법 3: 모든 컨테이너 재시작

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml --env-file .env.prod down
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

### 방법 4: Nginx 설정 파일 확인

```bash
# 설정 파일이 올바르게 마운트되었는지 확인
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec nginx ls -la /etc/nginx/conf.d/

# 설정 파일 내용 확인
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec nginx cat /etc/nginx/conf.d/badmintok.conf
```

## 🔧 일반적인 문제

### 문제 1: 포트 80 충돌

**증상**: Nginx가 시작되지 않음

**해결**:
```bash
# 포트 80을 사용하는 프로세스 확인 및 중지
sudo lsof -i :80
sudo kill -9 <PID>
```

### 문제 2: Nginx 설정 파일 오류

**증상**: Nginx가 즉시 종료됨

**해결**:
```bash
# 설정 파일 검증
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -t

# 오류가 있으면 nginx/conf.d/badmintok-prod.conf 파일 확인
```

### 문제 3: 볼륨 마운트 문제

**증상**: 정적 파일을 찾을 수 없음

**해결**:
```bash
# 볼륨 확인
docker volume ls | grep static
docker volume ls | grep media

# 볼륨 내용 확인
docker run --rm -v badmintok_static_data:/data alpine ls -la /data
```

### 문제 4: 네트워크 연결 문제

**증상**: Nginx가 웹 컨테이너에 연결할 수 없음

**해결**:
```bash
# 네트워크 확인
docker network ls | grep badmintok
docker network inspect badmintok_badmintok-net

# 웹 컨테이너 연결 테스트
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec nginx ping -c 3 badmintok-web-prod
```

## 📋 체크리스트

- [ ] Nginx 로그 확인 완료
- [ ] 포트 80이 사용 가능한지 확인
- [ ] Nginx 설정 파일이 올바른지 확인
- [ ] 볼륨이 올바르게 마운트되었는지 확인
- [ ] 네트워크가 올바르게 설정되었는지 확인
- [ ] 웹 컨테이너가 healthy 상태인지 확인

## 🚨 긴급 조치

Nginx가 계속 재시작되는 경우:

```bash
# 1. 모든 컨테이너 중지
cd ~/badmintok
docker-compose -f docker-compose.prod.yml --env-file .env.prod down

# 2. Nginx 컨테이너만 제거
docker rm -f badmintok-nginx-prod

# 3. 다시 시작
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 4. 로그 확인
docker-compose -f docker-compose.prod.yml --env-file .env.prod logs -f nginx
```

