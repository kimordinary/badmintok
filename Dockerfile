FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=badmintok.settings

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Copy application code
COPY . .

# collectstatic: Docker 이미지 빌드 시 정적 파일 수집
RUN python manage.py collectstatic --noinput || true

EXPOSE 8080

# Copy and set executable permission for entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]


