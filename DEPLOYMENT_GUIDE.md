# Badmintok AWS Lightsail 배포 가이드

이 문서는 GitHub Actions를 사용하여 AWS Lightsail 서버에 자동 배포하는 방법을 설명합니다.

## 📋 목차

1. [사전 준비사항](#사전-준비사항)
2. [서버 초기 설정](#서버-초기-설정)
3. [GitHub Secrets 설정](#github-secrets-설정)
4. [도메인 및 DNS 설정](#도메인-및-dns-설정)
5. [첫 배포 실행](#첫-배포-실행)
6. [배포 확인](#배포-확인)
7. [트러블슈팅](#트러블슈팅)

---

## 🚀 사전 준비사항

### 1. 필수 소프트웨어 및 계정

- [ ] AWS Lightsail 인스턴스 생성 완료 (IP: 52.79.209.4)
- [ ] GitHub 저장소 접근 권한
- [ ] 도메인 등록 완료 (badmintok.com)
- [ ] AWS IAM 사용자 생성 및 액세스 키 발급 (선택사항, S3 사용 시)

### 2. 서버 요구사항

- **최소**: CPU 2코어, RAM 2GB, 디스크 20GB
- **권장**: CPU 4코어, RAM 4GB, 디스크 50GB
- OS: Amazon Linux 2023

---

## 🖥️ 서버 초기 설정

### 1. SSH로 서버 접속

```bash
ssh ec2-user@52.79.209.4
# 또는
ssh -i your-key.pem ec2-user@52.79.209.4
```

### 2. 시스템 업데이트

```bash
sudo dnf update -y
```

### 3. Docker 및 Docker Compose 설치

```bash
# Docker 설치 (Amazon Linux 2023)
sudo dnf install docker -y

# Docker 서비스 시작 및 자동 시작 설정
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker ec2-user

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 설치 확인
docker --version
docker-compose --version

# 재로그인하여 그룹 변경사항 적용
exit
# 다시 SSH 접속
```

### 4. 프로젝트 디렉토리 생성

```bash
mkdir -p ~/badmintok
cd ~/badmintok
```

### 6. 방화벽 설정 (AWS Security Groups 권장)

**참고**: AWS Lightsail은 Security Groups를 통해 방화벽을 관리하는 것이 권장됩니다. Lightsail 콘솔에서 다음 포트를 허용하세요:
- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)

로컬 방화벽을 사용하려면 firewalld를 사용할 수 있습니다:

```bash
# firewalld 설치 및 시작
sudo dnf install firewalld -y
sudo systemctl start firewalld
sudo systemctl enable firewalld

# 필요한 포트 허용
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# 방화벽 규칙 적용
sudo firewall-cmd --reload

# 현재 규칙 확인
sudo firewall-cmd --list-all
```

---

## 🔐 GitHub Secrets 설정

GitHub 저장소에서 다음 Secrets를 설정해야 합니다:

1. GitHub 저장소로 이동
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭하여 다음 항목들을 추가:

### 필수 Secrets

| Secret 이름 | 설명 | 예시 |
|------------|------|------|
| `LIGHTSAIL_HOST` | Lightsail 서버 IP 주소 | `52.79.209.4` |
| `LIGHTSAIL_USER` | SSH 사용자 이름 | `ec2-user` |
| `LIGHTSAIL_SSH_KEY` | SSH 개인 키 전체 내용 | `-----BEGIN RSA PRIVATE KEY-----...` |
| `LIGHTSAIL_SSH_PORT` | SSH 포트 (선택사항, 기본값: 22) | `22` |

### 선택적 Secrets (S3 사용 시)

| Secret 이름 | 설명 |
|------------|------|
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 ID |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 액세스 키 |
| `S3_BUCKET_NAME` | S3 버킷 이름 |

### SSH 키 생성 방법

로컬 컴퓨터에서:

```bash
# SSH 키 생성 (없는 경우)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 공개 키를 서버에 추가
ssh-copy-id ec2-user@52.79.209.4

# 또는 수동으로
cat ~/.ssh/id_rsa.pub
# 출력된 내용을 서버의 ~/.ssh/authorized_keys에 추가

# 개인 키 내용 확인 (GitHub Secret에 추가)
cat ~/.ssh/id_rsa
# 전체 내용을 복사하여 LIGHTSAIL_SSH_KEY에 추가
```

---

## 📝 GitHub Secrets 설정

**중요**: 환경 변수 파일은 GitHub Actions에서 자동으로 생성됩니다. 서버에서 수동으로 생성할 필요가 없습니다.

### 1. GitHub Secrets 설정

GitHub 저장소에서 다음 Secrets를 설정해야 합니다:

1. **Settings** → **Secrets and variables** → **Actions** 클릭
2. **New repository secret** 버튼으로 각 Secret 추가

자세한 설정 방법은 **[GITHUB_SECRETS_GUIDE.md](./GITHUB_SECRETS_GUIDE.md)** 문서를 참고하세요.

### 2. 필수 Secrets 목록

#### 서버 연결 정보
- `LIGHTSAIL_HOST`: `52.79.209.4`
- `LIGHTSAIL_USER`: `ec2-user`
- `LIGHTSAIL_SSH_KEY`: SSH 개인 키 전체 내용

#### Django 설정
- `DJANGO_SECRET_KEY`: Django Secret Key (생성 필요)
- `DJANGO_DEBUG`: `False`
- `DJANGO_ALLOWED_HOSTS`: `badmintok.com,www.badmintok.com,52.79.209.4`

#### 데이터베이스 설정
- `MYSQL_ROOT_PASSWORD`: MySQL root 비밀번호
- `MYSQL_PASSWORD`: MySQL 사용자 비밀번호
- `DB_PASSWORD`: 데이터베이스 비밀번호 (위와 동일)

#### 카카오 OAuth 설정
- `KAKAO_REST_API_KEY`: 카카오 REST API 키
- `KAKAO_REDIRECT_URI`: `https://badmintok.com/accounts/kakao`

### 3. Django Secret Key 생성

로컬 컴퓨터에서:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

생성된 키를 `DJANGO_SECRET_KEY` Secret에 추가합니다.

### 4. .env.prod 파일 자동 생성

GitHub Actions가 배포 시 자동으로 `.env.prod` 파일을 생성합니다. 서버에서 수동으로 생성할 필요가 없습니다.

---

## 🌐 도메인 및 DNS 설정

### 1. DNS 레코드 설정

도메인 관리 패널에서 다음 A 레코드를 추가:

| 타입 | 호스트 | 값 | TTL |
|------|--------|-----|-----|
| A | @ | 52.79.209.4 | 3600 |
| A | www | 52.79.209.4 | 3600 |

### 2. DNS 전파 확인

```bash
# 로컬에서 확인
nslookup badmintok.com
dig badmintok.com
```

---

## 🚢 첫 배포 실행

### 방법 1: GitHub Actions를 통한 자동 배포 (권장)

1. **main** 또는 **master** 브랜치에 코드 푸시:

```bash
git add .
git commit -m "Initial deployment setup"
git push origin main
```

2. GitHub에서 Actions 탭 확인:
   - GitHub 저장소 → **Actions** 탭
   - 워크플로우 실행 상태 확인

3. 수동 트리거 (필요한 경우):
   - **Actions** → **Deploy to AWS Lightsail** → **Run workflow**

### 방법 2: 수동 배포

서버에서 직접 실행:

```bash
cd ~/badmintok

# Git에서 최신 코드 가져오기
git pull origin main

# Docker 이미지 빌드
docker-compose -f docker-compose.prod.yml build

# 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
```

---

## ✅ 배포 확인

### 1. 컨테이너 상태 확인

```bash
cd ~/badmintok
docker-compose -f docker-compose.prod.yml ps
```

모든 컨테이너가 `Up (healthy)` 상태여야 합니다.

### 2. 웹사이트 접속 확인

```bash
# 서버에서 확인
curl http://localhost/health/

# 브라우저에서 확인
http://52.79.209.4
http://badmintok.com
```

### 3. 로그 확인

```bash
# 전체 로그
docker-compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f db
```

### 4. Admin 페이지 확인

```bash
http://badmintok.com/admin/
```

### 5. Superuser 생성 (처음 배포 시)

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

또는 GitHub Secrets에 다음을 추가하고 재배포:

```bash
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@badmintok.com
DJANGO_SUPERUSER_PASSWORD=your-password
```

그리고 `entrypoint.sh`에서 이 변수들을 사용하도록 이미 설정되어 있습니다.

---

## 🔄 자동 배포 프로세스

GitHub Actions가 설정되면:

1. **main** 또는 **master** 브랜치에 푸시할 때마다 자동 배포
2. 배포 프로세스:
   - 코드 체크아웃
   - Docker 이미지 빌드
   - 서버에 SSH 연결
   - 기존 컨테이너 중지
   - Git에서 최신 코드 가져오기
   - Docker 이미지 빌드
   - 컨테이너 시작
   - 데이터베이스 마이그레이션 실행
   - 정적 파일 수집
   - 헬스체크 확인

---

## 🐛 트러블슈팅

### 1. 컨테이너가 시작되지 않는 경우

```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml logs

# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 특정 컨테이너 재시작
docker-compose -f docker-compose.prod.yml restart web
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
# 정적 파일 재수집
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput --clear

# Nginx 재시작
docker-compose -f docker-compose.prod.yml restart nginx
```

### 4. 500 Internal Server Error

```bash
# Django 로그 확인
docker-compose -f docker-compose.prod.yml logs -f web

# DEBUG 모드로 임시 변경 (프로덕션에서는 권장하지 않음)
# GitHub Secrets에서 DJANGO_DEBUG=True로 변경 후 재배포
```

### 5. GitHub Actions 배포 실패

1. **Actions** 탭에서 실패한 워크플로우 확인
2. 로그에서 오류 메시지 확인
3. 일반적인 원인:
   - SSH 키 설정 오류
   - 서버 접근 불가
   - GitHub Secrets 누락 또는 잘못된 설정
   - Docker 설치 문제

### 6. 포트 충돌

```bash
# 사용 중인 포트 확인
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :3306
# 또는 ss 명령어 사용 (Amazon Linux 2023)
sudo ss -tulpn | grep :80
sudo ss -tulpn | grep :3306

# 기존 서비스 중지 (필요한 경우)
# Amazon Linux 2023에서는 기본적으로 웹 서버가 실행 중이지 않을 수 있습니다
sudo systemctl stop httpd 2>/dev/null || true  # Apache (있는 경우)
sudo systemctl stop nginx 2>/dev/null || true  # Nginx (있는 경우)
```

### 7. 디스크 공간 부족

```bash
# 디스크 사용량 확인
df -h

# 불필요한 Docker 이미지/컨테이너 정리
docker system prune -a
docker volume prune
```

---

## 🔒 보안 체크리스트

배포 전 필수 확인 사항:

- [ ] `DJANGO_DEBUG=False` 설정 확인
- [ ] `DJANGO_SECRET_KEY` 변경 확인
- [ ] `DJANGO_ALLOWED_HOSTS` 정확히 설정
- [ ] Database 비밀번호 강력하게 설정
- [ ] GitHub Secrets가 모두 올바르게 설정되었는지 확인
- [ ] Database 포트(3306) 외부 노출 차단 확인
- [ ] Nginx 보안 헤더 설정 확인
- [ ] 방화벽 설정 확인 (80, 443 포트만 허용)
- [ ] SSH 키 기반 인증 설정
- [ ] 정기적인 백업 계획 수립

---

## 📊 모니터링 및 유지보수

### 로그 확인

```bash
# 실시간 로그
docker-compose -f docker-compose.prod.yml logs -f

# 특정 시간의 로그
docker-compose -f docker-compose.prod.yml logs --since 1h
```

### 백업

```bash
# Database 백업
docker-compose -f docker-compose.prod.yml exec db mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ${MYSQL_DATABASE} > backup_$(date +%Y%m%d_%H%M%S).sql

# Media 파일 백업
docker cp badmintok-web-prod:/app/media ./media_backup_$(date +%Y%m%d_%H%M%S)
```

### 업데이트 및 재배포

```bash
# GitHub Actions를 통한 자동 배포 (권장)
git push origin main

# 또는 수동 배포
cd ~/badmintok
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. Docker 및 Docker Compose 버전
2. 서버 리소스 (CPU, 메모리, 디스크)
3. 로그 파일
4. 환경 변수 설정
5. GitHub Actions 로그

---

## 📝 체크리스트 요약

### 서버 초기 설정
- [ ] 시스템 업데이트 완료
- [ ] Docker 설치 완료
- [ ] Docker Compose 설치 완료
- [ ] Git 설치 완료
- [ ] 방화벽 설정 완료
- [ ] 프로젝트 디렉토리 생성 완료

### GitHub 설정
- [ ] GitHub Secrets 설정 완료
- [ ] SSH 키 서버에 추가 완료
- [ ] GitHub Actions 워크플로우 파일 확인 완료

### 환경 설정
- [ ] GitHub Secrets에 모든 필수 환경 변수 설정 완료
- [ ] Django Secret Key 생성 및 설정 완료
- [ ] 데이터베이스 비밀번호 생성 및 설정 완료

### 도메인 설정
- [ ] DNS A 레코드 설정 완료
- [ ] DNS 전파 확인 완료

### 배포
- [ ] 첫 배포 실행 완료
- [ ] 컨테이너 상태 확인 완료
- [ ] 웹사이트 접속 확인 완료
- [ ] Admin 페이지 접속 확인 완료
- [ ] Superuser 생성 완료

---

**배포 완료!** 🎉

