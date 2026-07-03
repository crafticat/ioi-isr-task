#!/usr/bin/env bash
# Bring up an ISOLATED local dev CMS for integration tests and seed a test admin.
# Usage: scripts/testcms_up.sh /path/to/cms-fork-checkout
set -euo pipefail
FORK="${1:?path to the ioi-isr/cms checkout (e.g. /Users/crafti/PycharmProjects/cms)}"
PROJECT="cmsops-test"
cd "$FORK"
# Unique project name = isolated containers/volumes/network; override file remaps AWS to 18889.
docker compose -p "$PROJECT" \
  -f docker/docker-compose.dev.yml \
  -f "$OLDPWD/docker/docker-compose.test-ports.yml" up -d devdb devcms
# Wait for AdminWebServer.
for i in $(seq 1 60); do
  if curl -sS -o /dev/null "http://localhost:18889/login"; then break; fi
  sleep 2
done
# Seed a throwaway full-permission admin used by the integration tests.
docker compose -p "$PROJECT" -f docker/docker-compose.dev.yml exec -T devcms \
  bash -lc 'cmsAddAdmin testadmin -p testpass --all 2>/dev/null || true'
echo "CMS_DEV_URL=http://localhost:18889"
echo "CMS_USERNAME=testadmin"
echo "CMS_PASSWORD=testpass"
