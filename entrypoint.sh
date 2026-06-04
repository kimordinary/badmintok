#!/bin/sh
set -e

echo "=== Badmintok Production Entrypoint ==="

# 데이터베이스 연결 대기
echo "Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0

while ! python -c "
import os
import pymysql
try:
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'badmintok')
    )
    conn.close()
    print('Database connection successful')
    exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "Error: Database connection timeout after $MAX_RETRIES retries"
        exit 1
    fi
    echo "Database not ready, waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "Database is ready!"

# 미디어 디렉토리 생성 및 권한 설정
echo "Creating media directory..."
mkdir -p /app/media
chmod 755 /app/media

# 마이그레이션은 entrypoint에서 실행하지 않는다.
# 이유: 대용량 테이블 ALTER(예: VisitorLog status_code)가 gunicorn 기동/헬스체크를 막아
#       컨테이너 unhealthy → 배포 실패 → 사이트 다운을 반복 유발했다.
# 현재 코드는 밀린 마이그레이션 없이도 정상 동작하므로, 마이그레이션은 사이트가 뜬 뒤
# 배포 스크립트(또는 운영자)가 별도로 적용한다. → 사이트는 항상 즉시 기동.
echo "Skipping migrations at startup (applied separately after boot)."

# 정적파일은 Dockerfile 빌드에서 이미 수집됨. 런타임은 비차단(백그라운드)으로만.
( python manage.py collectstatic --noinput >/dev/null 2>&1 || true ) &

# Superuser 생성 (선택사항 - 환경 변수가 있을 경우에만)
# 커스텀 User 모델은 email을 USERNAME_FIELD로 사용하므로, email, activity_name, password 순서
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_ACTIVITY_NAME" ]; then
    echo "Creating superuser if not exists..."
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(
        email='$DJANGO_SUPERUSER_EMAIL',
        activity_name='$DJANGO_SUPERUSER_ACTIVITY_NAME',
        password='$DJANGO_SUPERUSER_PASSWORD'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
fi

echo "Starting Gunicorn server..."

# Gunicorn으로 WSGI 서버 실행 (프로덕션용)
# --workers: CPU 코어 수 * 2 + 1 권장
# --timeout: 요청 처리 타임아웃 (초)
# --access-logfile: 액세스 로그 파일
# --error-logfile: 에러 로그 파일
# --log-level: 로그 레벨
exec gunicorn badmintok.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile - \
    --log-level ${GUNICORN_LOG_LEVEL:-info} \
    --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-50}


# redeploy marker: force fresh build from latest main (0013 제거 반영)
