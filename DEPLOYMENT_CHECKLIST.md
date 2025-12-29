# 배포 체크리스트 - 사용자 작업 순서

이 문서는 배포를 위해 **사용자가 직접 처리해야 할 작업들**을 순서대로 정리한 것입니다.

---

## ✅ 1단계: 서버 초기 설정

### 1.1 SSH로 서버 접속

```bash
ssh ec2-user@52.79.209.4
# 또는 키 파일 사용
ssh -i your-key.pem ec2-user@52.79.209.4
```

### 1.2 시스템 업데이트

```bash
sudo dnf update -y
```

### 1.3 Docker 설치

```bash
# Docker 설치
sudo dnf install docker -y

# Docker 서비스 시작 및 자동 시작 설정
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker ec2-user
```

### 1.4 Docker Compose 설치

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 1.5 설치 확인 및 재로그인

```bash
docker --version
docker-compose --version
exit
# 다시 SSH 접속하여 그룹 변경사항 적용
```

### 1.6 방화벽 설정

**AWS Lightsail Security Groups 사용 (권장)**:
- Lightsail 콘솔 → 네트워킹 → 방화벽 규칙에서 다음 포트 허용:
  - 22 (SSH)
  - 80 (HTTP)
  - 443 (HTTPS)

**또는 로컬 firewalld 사용**:

```bash
sudo dnf install firewalld -y
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

### 1.6 프로젝트 디렉토리 생성

```bash
mkdir -p ~/badmintok
cd ~/badmintok
```

---

## ✅ 2단계: SSH 키 설정

### 2.1 로컬 컴퓨터에서 SSH 키 생성 (없는 경우)

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
# Enter를 눌러 기본 경로 사용
# 비밀번호 설정 (선택사항)
```

### 2.2 공개 키를 서버에 추가

```bash
# 방법 1: ssh-copy-id 사용 (권장)
ssh-copy-id ec2-user@52.79.209.4

# 방법 2: 수동으로
cat ~/.ssh/id_rsa.pub
# 출력된 내용을 복사하여 서버의 ~/.ssh/authorized_keys에 추가
```

### 2.3 개인 키 내용 확인 (GitHub Secret에 사용)

```bash
cat ~/.ssh/id_rsa
# 전체 내용을 복사 (-----BEGIN RSA PRIVATE KEY----- 부터 -----END RSA PRIVATE KEY----- 까지)
```

---

## ✅ 3단계: GitHub Secrets 설정

### 3.1 GitHub 저장소 접속

1. GitHub 저장소로 이동
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭

### 3.2 서버 연결 Secrets 추가

| Secret 이름 | 값 | 비고 |
|------------|-----|------|
| `LIGHTSAIL_HOST` | `52.79.209.4` | 서버 IP 주소 |
| `LIGHTSAIL_USER` | `ec2-user` | SSH 사용자 이름 |
| `LIGHTSAIL_SSH_KEY` | `-----BEGIN RSA...` | 2.3에서 복사한 전체 개인 키 |
| `LIGHTSAIL_SSH_PORT` | `22` | SSH 포트 (선택사항, 기본값: 22) |

**중요**: `LIGHTSAIL_SSH_KEY`는 개인 키의 **전체 내용**을 복사해야 합니다 (줄바꿈 포함).

### 3.3 Django 설정 Secrets 추가

| Secret 이름 | 값 | 비고 |
|------------|-----|------|
| `DJANGO_SECRET_KEY` | `django-insecure-...` | Django Secret Key (생성 필요) |
| `DJANGO_DEBUG` | `False` | 디버그 모드 |
| `DJANGO_ALLOWED_HOSTS` | `badmintok.com,www.badmintok.com,52.79.209.4` | 허용된 호스트 |

**Django Secret Key 생성**:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 3.4 데이터베이스 설정 Secrets 추가

| Secret 이름 | 값 | 비고 |
|------------|-----|------|
| `MYSQL_ROOT_PASSWORD` | `강력한-비밀번호` | MySQL root 비밀번호 |
| `MYSQL_PASSWORD` | `강력한-비밀번호` | MySQL 사용자 비밀번호 |
| `DB_PASSWORD` | `강력한-비밀번호` | 데이터베이스 비밀번호 (위와 동일) |

**비밀번호 생성**:
```bash
# Linux/Mac
openssl rand -base64 32
```

### 3.5 카카오 OAuth 설정 Secrets 추가

| Secret 이름 | 값 | 비고 |
|------------|-----|------|
| `KAKAO_REST_API_KEY` | `카카오-API-키` | 카카오 개발자 센터에서 발급 |
| `KAKAO_REDIRECT_URI` | `https://badmintok.com/accounts/kakao` | 카카오 리다이렉트 URI |

### 3.6 선택적 Secrets (기본값 사용 가능)

다음 Secrets는 선택사항이며, 설정하지 않으면 기본값이 사용됩니다:

- `MYSQL_DATABASE`: `badmintok` (기본값)
- `MYSQL_USER`: `badmintok_user` (기본값)
- `DB_HOST`: `db` (기본값)
- `DB_PORT`: `3306` (기본값)
- `DB_NAME`: `badmintok` (기본값)
- `DB_USER`: `badmintok_user` (기본값)
- `NGINX_HTTP_PORT`: `80` (기본값)
- `GUNICORN_WORKERS`: `3` (기본값)
- `GUNICORN_TIMEOUT`: `120` (기본값)
- `GUNICORN_LOG_LEVEL`: `info` (기본값)
- `GUNICORN_MAX_REQUESTS`: `1000` (기본값)
- `GUNICORN_MAX_REQUESTS_JITTER`: `50` (기본값)
- `TZ`: `Asia/Seoul` (기본값)

**자세한 설정 방법은 [GITHUB_SECRETS_GUIDE.md](./GITHUB_SECRETS_GUIDE.md) 문서를 참고하세요.**

---

## ✅ 4단계: 프로젝트 디렉토리 준비

### 4.1 서버에서 프로젝트 디렉토리 생성

```bash
mkdir -p ~/badmintok
cd ~/badmintok

# GitHub Actions가 자동으로 파일을 배포하므로 수동으로 클론할 필요 없음
# 첫 배포 전에는 디렉토리만 생성하면 됨
```

**참고**: `.env.prod` 파일은 GitHub Actions가 자동으로 생성하므로 서버에서 수동으로 생성할 필요가 없습니다.

---

## ✅ 5단계: 도메인 및 DNS 설정

### 5.1 DNS 레코드 추가

도메인 관리 패널(예: Route 53, Cloudflare, 네임서버 등)에서:

| 타입 | 호스트 | 값 | TTL |
|------|--------|-----|-----|
| A | @ | 52.79.209.4 | 3600 |
| A | www | 52.79.209.4 | 3600 |

### 5.2 DNS 전파 확인

```bash
# 로컬에서 확인 (몇 분~몇 시간 소요)
nslookup badmintok.com
dig badmintok.com
```

---

## ✅ 6단계: 첫 배포 실행

### 6.1 GitHub Actions를 통한 자동 배포 (권장)

1. 로컬에서 코드 푸시:

```bash
git add .
git commit -m "Initial deployment setup"
git push origin main
```

2. GitHub에서 확인:
   - 저장소 → **Actions** 탭
   - "Deploy to AWS Lightsail" 워크플로우 실행 확인
   - 성공 여부 확인

3. 수동 트리거 (필요한 경우):
   - **Actions** → **Deploy to AWS Lightsail** → **Run workflow** → **Run workflow**

### 6.2 수동 배포 (대안)

서버에서 직접 실행:

```bash
cd ~/badmintok
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

---

## ✅ 7단계: 배포 확인

### 7.1 컨테이너 상태 확인

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml ps
```

모든 컨테이너가 `Up (healthy)` 상태여야 합니다.

### 7.2 웹사이트 접속 확인

브라우저에서:
- http://52.79.209.4
- http://badmintok.com
- http://www.badmintok.com

### 7.3 Admin 페이지 확인

- http://badmintok.com/admin/

### 7.4 Superuser 생성

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

또는 `.env.prod`에 다음 추가 후 재시작:

```bash
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@badmintok.com
DJANGO_SUPERUSER_PASSWORD=your-password
```

---

## ✅ 8단계: 추가 설정 (선택사항)

### 8.1 SSL 인증서 설정 (HTTPS)

```bash
# Certbot 설치 (Amazon Linux 2023)
sudo dnf install certbot python3-certbot-nginx -y

# SSL 인증서 발급
sudo certbot --nginx -d badmintok.com -d www.badmintok.com

# docker-compose.prod.yml에서 HTTPS 포트 주석 해제
# nginx/conf.d/badmintok-prod.conf에서 HTTPS 서버 블록 주석 해제
```

### 8.2 정기 백업 설정

```bash
# 백업 스크립트 생성
nano ~/backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cd ~/badmintok

# Database 백업
docker-compose -f docker-compose.prod.yml exec -T db mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ${MYSQL_DATABASE} > ~/backups/db_${DATE}.sql

# Media 파일 백업
docker cp badmintok-web-prod:/app/media ~/backups/media_${DATE}

# 오래된 백업 삭제 (30일 이상)
find ~/backups -name "*.sql" -mtime +30 -delete
find ~/backups -name "media_*" -mtime +30 -exec rm -rf {} \;
```

```bash
chmod +x ~/backup.sh
mkdir -p ~/backups

# Crontab에 추가 (매일 새벽 2시)
crontab -e
# 다음 줄 추가:
0 2 * * * /home/ec2-user/backup.sh
```

---

## 🚨 문제 발생 시

### 로그 확인

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml logs -f
```

### 컨테이너 재시작

```bash
docker-compose -f docker-compose.prod.yml restart
```

### 전체 재배포

```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 📋 최종 체크리스트

배포 전 모든 항목 확인:

- [ ] 서버 초기 설정 완료
- [ ] Docker 및 Docker Compose 설치 완료
- [ ] SSH 키 설정 완료
- [ ] GitHub Secrets 설정 완료 (모든 필수 Secrets)
- [ ] DNS 설정 완료
- [ ] 첫 배포 실행 완료
- [ ] 웹사이트 접속 확인 완료
- [ ] Admin 페이지 접속 확인 완료
- [ ] Superuser 생성 완료

---

**모든 작업이 완료되면 배포가 성공적으로 완료된 것입니다!** 🎉

추가 도움이 필요하면 `DEPLOYMENT_GUIDE.md`를 참고하세요.

