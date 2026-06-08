#!/bin/bash
set -euo pipefail

IMAGE=$1
SLOT_FILE=/tmp/naengo-slot
CURRENT=$(cat "$SLOT_FILE" 2>/dev/null || echo "blue")

if [ "$CURRENT" = "blue" ]; then
  NEXT=green; NEXT_PORT=8002; NEXT_SVC=naengo-ai-green; CURR_SVC=naengo-ai-blue
else
  NEXT=blue;  NEXT_PORT=8001; NEXT_SVC=naengo-ai-blue;  CURR_SVC=naengo-ai-green
fi

echo "[deploy] current=$CURRENT → next=$NEXT (port $NEXT_PORT)"

# 새 컨테이너 기동
NAENGO_AI_IMAGE="$IMAGE" docker-compose -f docker-compose.prod.yml up -d --no-deps --force-recreate "$NEXT_SVC"

# 헬스체크 (2초 간격 × 30회 = 최대 60초)
echo "[deploy] waiting for health check..."
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$NEXT_PORT/" > /dev/null 2>&1; then
    echo "[deploy] health check passed (attempt $i)"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[deploy] health check failed — rolling back" >&2
    docker-compose -f docker-compose.prod.yml stop "$NEXT_SVC"
    docker-compose -f docker-compose.prod.yml rm -f "$NEXT_SVC"
    exit 1
  fi
  sleep 2
done

# Nginx upstream 전환 (파일 덮어쓰기 + 그레이스풀 리로드)
echo "upstream naengo_ai { server 127.0.0.1:$NEXT_PORT; }" \
  | sudo tee /etc/nginx/conf.d/naengo-upstream.conf > /dev/null
sudo nginx -s reload
echo "[deploy] nginx reloaded → upstream=127.0.0.1:$NEXT_PORT"

# 슬롯 갱신
echo "$NEXT" > "$SLOT_FILE"

# 기존 컨테이너 정리
docker-compose -f docker-compose.prod.yml stop "$CURR_SVC"
docker-compose -f docker-compose.prod.yml rm -f "$CURR_SVC"

# 미사용 이미지만 정리 (실행 중 컨테이너 이미지는 보존)
docker image prune -af

echo "[deploy] done: active=$NEXT"
