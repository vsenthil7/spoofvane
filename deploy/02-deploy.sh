#!/usr/bin/env bash
# SpoofVane · Vultr deploy (02-deploy.sh)
#   ssh root@<IP> ANTHROPIC_API_KEY=... OPENAI_API_KEY=... \
#       BRIGHTDATA_API_TOKEN=... BRIGHTDATA_API_KEY=... \
#       bash -s < deploy/02-deploy.sh
#
# Clones (or pulls) the repo, generates .env from the prod template, injects the
# API keys passed in the invoking environment, builds + starts the stack
# (api + caddy web) on :8081, waits for /healthz, seeds the demo DB.
# Idempotent.

set -euo pipefail
exec > >(tee -a /var/log/spoofvane-deploy.log) 2>&1

REPO_URL="${REPO_URL:-https://github.com/vsenthil7/spoofvane.git}"
TARGET_DIR="/srv/spoofvane/spoofvane"
BRANCH="${BRANCH:-main}"
echo "[deploy] start $(date -u +%FT%TZ)  repo=$REPO_URL  branch=$BRANCH"

# ----- Clone or pull -----
if [ -d "$TARGET_DIR/.git" ]; then
    cd "$TARGET_DIR"
    git fetch --all --tags
    git checkout "$BRANCH"
    git reset --hard "origin/$BRANCH"
else
    mkdir -p "$(dirname "$TARGET_DIR")"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
fi
cd "$TARGET_DIR"

# ----- .env from the prod template -----
if [ ! -f .env ]; then
    cp deploy/prod.env.example .env
    # Auto-generate the app secret in-place.
    sed -i "s|__SECRET_KEY__|$(openssl rand -base64 48 | tr -d '+/=' | head -c 48)|g" .env
fi

# ----- Inject keys passed in the invoking environment (never committed) -----
set_env() {
    local key="$1" val="$2"
    [ -z "$val" ] && return 0
    if grep -q "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${val}|" .env
    else
        echo "${key}=${val}" >> .env
    fi
    echo "[deploy]   set ${key}"
}
set_env "ANTHROPIC_API_KEY"      "${ANTHROPIC_API_KEY:-}"
set_env "OPENAI_API_KEY"         "${OPENAI_API_KEY:-}"
set_env "GEMINI_API_KEY"         "${GEMINI_API_KEY:-}"
set_env "BRIGHTDATA_API_KEY"     "${BRIGHTDATA_API_KEY:-}"
set_env "BRIGHTDATA_API_TOKEN"   "${BRIGHTDATA_API_TOKEN:-}"
set_env "BRIGHTDATA_CUSTOMER_ID" "${BRIGHTDATA_CUSTOMER_ID:-}"
set_env "MOCK_MODE"              "${MOCK_MODE:-false}"
set_env "SPOOFVANE_BD_MODE"      "${SPOOFVANE_BD_MODE:-live}"

echo "[deploy] inference config in final .env (secrets redacted):"
grep -E '^(MOCK_MODE|SPOOFVANE_BD_MODE|ANTHROPIC_MODEL|OPENAI_MODEL|GEMINI_MODEL)=' .env || true
grep -E '^(ANTHROPIC_API_KEY|OPENAI_API_KEY|GEMINI_API_KEY|BRIGHTDATA_API_TOKEN)=' .env \
    | sed -E 's|(=).{6,}|\1***REDACTED***|' || true

# ----- Build + start the stack -----
echo "[deploy] docker compose up -d --build"
docker compose -f deploy/docker-compose.yml --env-file .env up -d --build

# ----- Seed the demo DB inside the api container -----
echo "[deploy] seeding demo data..."
docker compose -f deploy/docker-compose.yml exec -T api \
    python -m scripts.seed_demo || echo "[deploy] seed step returned non-zero (may already be seeded)"

# ----- Wait for the public health endpoint via Caddy -----
echo "[deploy] waiting for /healthz via the web container (:8081)..."
for i in $(seq 1 60); do
    if curl -fsS http://localhost:8081/healthz >/dev/null 2>&1; then
        echo "[deploy] healthz OK after ${i}s"
        break
    fi
    sleep 1
done
curl -s http://localhost:8081/healthz | jq . || true

echo
docker compose -f deploy/docker-compose.yml ps
PUBLIC_IP=$(curl -fsS https://api.ipify.org || echo SERVER_IP)
echo
echo "[deploy] done. Public demo (pre-TLS): http://${PUBLIC_IP}:8081"
echo "Next (TLS): ssh root@<IP> DOMAIN=spoofvane.<yourdomain> bash -s < deploy/03-tls.sh"
