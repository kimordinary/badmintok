#!/bin/bash
# Badmintok Production Deployment Script

set -e

echo "=== Badmintok Production Deployment ==="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env.prod exists
if [ ! -f .env.prod ]; then
    echo -e "${RED}Error: .env.prod file not found!${NC}"
    echo "Please create .env.prod file from .env.prod.example"
    echo "  cp .env.prod.example .env.prod"
    echo "  # Edit .env.prod with your production values"
    exit 1
fi

echo -e "${GREEN}✓ .env.prod file found${NC}"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ docker-compose is installed${NC}"

# Ask for confirmation
echo ""
echo -e "${YELLOW}This will deploy the application to production.${NC}"
echo "Are you sure you want to continue? (y/n)"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "=== Building Docker images ==="
docker-compose -f docker-compose.prod.yml build

echo ""
echo "=== Starting services ==="
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "=== Waiting for services to be healthy ==="
sleep 10

# Check service status
echo ""
echo "=== Service Status ==="
docker-compose -f docker-compose.prod.yml ps

echo ""
echo -e "${GREEN}=== Deployment completed! ===${NC}"
echo ""
echo "You can check the logs with:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "Access your application at:"
echo "  http://localhost"
echo ""
echo "Access admin panel at:"
echo "  http://localhost/admin/"
echo ""
