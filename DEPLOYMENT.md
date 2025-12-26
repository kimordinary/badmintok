# 배포 가이드

## 프로덕션 배포 준비

### 1. 환경 변수 파일 생성

`env.prod.example` 파일을 참고하여 `.env.prod` 파일을 생성하세요:

```bash
cp env.prod.example .env.prod
```

`.env.prod` 파일을 편집하여 다음 항목들을 설정하세요:

- `DJANGO_SECRET_KEY`: 강력한 시크릿 키로 변경 (Django secret key generator 사용)
- `DJANGO_DEBUG`: `False`로 설정
- `DJANGO_ALLOWED_HOSTS`: 서버 IP 주소 및 도메인 설정 (예: `54.180.247.3,yourdomain.com`)
- 데이터베이스 비밀번호 설정
- 카카오 로그인 API 키 및 리다이렉트 URI 설정

### 2. 서버 준비

#### 필수 요구사항
- Docker 및 Docker Compose 설치
- 최소 2GB RAM
- 최소 10GB 디스크 공간

#### 포트 확인
- 80번 포트 (HTTP) - Nginx
- 443번 포트 (HTTPS, 선택사항) - Nginx
- 3306번 포트는 외부에 노출되지 않음 (보안)

### 3. 배포 실행

```bash
# 프로덕션 환경으로 빌드 및 실행
docker-compose -f docker-compose.prod.yml up -d --build

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps
```

### 4. 초기 설정

#### 데이터베이스 마이그레이션
마이그레이션은 자동으로 실행됩니다. 수동으로 실행하려면:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

#### 관리자 계정 생성
`.env.prod` 파일에 다음 환경 변수를 추가하거나, 직접 생성:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

또는 `.env.prod`에 다음 변수 추가:
```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=your-password
```

### 5. 정적 파일 수집

정적 파일은 이미지 빌드 시 자동으로 수집됩니다. 수동으로 실행하려면:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 6. 서비스 관리

#### 서비스 시작
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 서비스 중지
```bash
docker-compose -f docker-compose.prod.yml down
```

#### 서비스 재시작
```bash
docker-compose -f docker-compose.prod.yml restart
```

#### 특정 서비스 재시작
```bash
docker-compose -f docker-compose.prod.yml restart web
docker-compose -f docker-compose.prod.yml restart nginx
```

### 7. 로그 확인

```bash
# 모든 서비스 로그
docker-compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f db
```

### 8. 백업

#### 데이터베이스 백업
```bash
docker-compose -f docker-compose.prod.yml exec db mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ${MYSQL_DATABASE} > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 볼륨 백업
```bash
# 미디어 파일 백업
docker run --rm -v badmintok_media_data:/data -v $(pwd):/backup alpine tar czf /backup/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### 9. 보안 체크리스트

- [ ] `DJANGO_SECRET_KEY`가 강력한 값으로 설정되었는지 확인
- [ ] `DJANGO_DEBUG=False`로 설정되었는지 확인
- [ ] `ALLOWED_HOSTS`에 올바른 도메인/IP가 설정되었는지 확인
- [ ] 데이터베이스 비밀번호가 강력한 값으로 설정되었는지 확인
- [ ] MySQL 포트가 외부에 노출되지 않았는지 확인
- [ ] 방화벽 설정 확인 (필요한 포트만 열기)
- [ ] SSL 인증서 설정 (HTTPS 사용 시)

### 10. 모니터링

#### 헬스체크
```bash
# 웹 서비스 헬스체크
curl http://54.180.247.3/health/

# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps
```

#### 리소스 사용량 확인
```bash
docker stats
```

### 11. 문제 해결

#### 컨테이너가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml logs

# 컨테이너 재생성
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

#### 데이터베이스 연결 문제
```bash
# 데이터베이스 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps db

# 데이터베이스 로그 확인
docker-compose -f docker-compose.prod.yml logs db
```

#### 정적 파일이 보이지 않는 경우
```bash
# 정적 파일 재수집
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput --clear

# nginx 재시작
docker-compose -f docker-compose.prod.yml restart nginx
```

### 12. 업데이트

코드 업데이트 시:

```bash
# 코드 업데이트 후
git pull

# 이미지 재빌드 및 재시작
docker-compose -f docker-compose.prod.yml up -d --build

# 마이그레이션 실행 (필요한 경우)
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```
