#!/bin/bash
# SSL 인증서 초기 발급 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== SSL 인증서 초기 발급 스크립트 ===${NC}"

# 환경 변수 확인
if [ -z "$DOMAIN" ]; then
    echo -e "${YELLOW}DOMAIN 환경 변수가 설정되지 않았습니다.${NC}"
    read -p "도메인 이름을 입력하세요 (예: badmintok.com): " DOMAIN
fi

if [ -z "$EMAIL" ]; then
    echo -e "${YELLOW}EMAIL 환경 변수가 설정되지 않았습니다.${NC}"
    read -p "이메일 주소를 입력하세요: " EMAIL
fi

echo -e "${GREEN}도메인: $DOMAIN${NC}"
echo -e "${GREEN}이메일: $EMAIL${NC}"

# 확인
read -p "계속하시겠습니까? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}취소되었습니다.${NC}"
    exit 1
fi

# certbot으로 SSL 인증서 발급
echo -e "${GREEN}SSL 인증서 발급 중...${NC}"
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SSL 인증서 발급 완료!${NC}"
    echo -e "${GREEN}nginx를 재시작합니다...${NC}"
    docker compose -f docker-compose.prod.yml restart nginx
    echo -e "${GREEN}완료! https://$DOMAIN 으로 접속 가능합니다.${NC}"
else
    echo -e "${RED}SSL 인증서 발급 실패${NC}"
    exit 1
fi
