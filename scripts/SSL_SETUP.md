# SSL 인증서 자동화 가이드

이 프로젝트는 Let's Encrypt를 사용한 SSL 인증서 자동 발급 및 갱신을 지원합니다.

## 구성 요소

1. **docker-compose.prod.yml**
   - `certbot` 서비스: 12시간마다 인증서 자동 갱신
   - `nginx` 서비스: 6시간마다 설정 리로드

2. **scripts/init-ssl.sh**
   - 최초 SSL 인증서 발급 스크립트

3. **nginx/conf.d/badmintok-prod.conf**
   - HTTP 서버: certbot webroot 방식 지원
   - HTTPS 서버: SSL 인증서 설정 (초기엔 주석 처리)

## 초기 설정 (서버에서 1회만 실행)

### 1. 서버에 접속
```bash
ssh your-server
cd ~/badmintok
```

### 2. 코드 업데이트
```bash
git pull origin main
```

### 3. Docker Compose 시작 (HTTP만)
```bash
sudo docker compose -f docker-compose.prod.yml up -d
```

### 4. SSL 인증서 발급
```bash
chmod +x scripts/init-ssl.sh
DOMAIN=badmintok.com EMAIL=your-email@example.com ./scripts/init-ssl.sh
```

또는 인터랙티브 모드:
```bash
./scripts/init-ssl.sh
# 도메인과 이메일을 입력
```

### 5. nginx 설정 파일 수정
인증서 발급이 완료되면, `nginx/conf.d/badmintok-prod.conf` 파일을 열어:

1. **HTTPS 서버 블록 주석 해제** (59-177번 라인)
2. **HTTP 서버 블록 수정**:
   - 임시 location 블록 주석 처리 (25-49번 라인)
   - HTTPS 리다이렉트 주석 해제 (20-22번 라인)

### 6. nginx 재시작
```bash
sudo docker compose -f docker-compose.prod.yml restart nginx
```

### 7. HTTPS 접속 확인
```bash
curl -I https://badmintok.com
```

## 자동 갱신

인증서 발급 후에는 certbot 컨테이너가 12시간마다 자동으로 갱신을 시도합니다.
nginx는 6시간마다 설정을 리로드하여 갱신된 인증서를 적용합니다.

## GitHub Actions 통합

GitHub Actions에서 자동 배포 시:
1. 초기 SSL 설정만 수동으로 1회 실행
2. 이후 배포는 자동으로 진행
3. certbot이 백그라운드에서 자동 갱신

## 트러블슈팅

### 인증서 발급 실패
```bash
# certbot 로그 확인
sudo docker logs badmintok-certbot-prod

# DNS 확인
dig badmintok.com
ping badmintok.com

# 80 포트 확인
curl -I http://badmintok.com/.well-known/acme-challenge/test
```

### 인증서 갱신 확인
```bash
# 인증서 만료일 확인
sudo docker exec badmintok-certbot-prod certbot certificates

# 수동 갱신 테스트
sudo docker compose -f docker-compose.prod.yml run --rm certbot renew --dry-run
```

### nginx 설정 확인
```bash
# nginx 설정 테스트
sudo docker exec badmintok-nginx-prod nginx -t

# nginx 로그 확인
sudo docker logs badmintok-nginx-prod
```
