#!/bin/bash
set -e
echo "=== Deploy Selenio Analytics ==="

cd /root/analytics
git pull origin main
docker build -t analytics-app .
docker rm -f analytics-app 2>/dev/null || true
docker run -d \
  --name analytics-app \
  --restart unless-stopped \
  --network easypanel \
  --ip 10.11.0.100 \
  --env-file /root/analytics/.env \
  -e DB_HOST=172.18.0.1 \
  analytics-app

echo "Deploy concluido - $(date)"
