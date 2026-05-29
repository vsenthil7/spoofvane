#!/usr/bin/env bash
# Run the Playwright E2E suite end-to-end.
#
# Prereqs handled here: browser install, demo seed, server start.
# Usage: bash tests/e2e/run_e2e.sh
set -euo pipefail

cd "$(dirname "$0")/../.."

export DATABASE_URL="${DATABASE_URL:-sqlite:///$(pwd)/data/e2e.db}"
export SECRET_KEY="${SECRET_KEY:-e2e-secret-key-0123456789012345678901234567890123}"
export PYTHONPATH="$(pwd)"
export E2E_BASE_URL="${E2E_BASE_URL:-http://127.0.0.1:8099}"

echo "[e2e] installing Playwright Chromium (no-op if cached)…"
python -m playwright install chromium

echo "[e2e] seeding demo user matrix…"
rm -f data/e2e.db
python -m scripts.seed_users >/dev/null

echo "[e2e] starting server on :8099…"
uvicorn src.api.app:app --port 8099 >/tmp/e2e_server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# wait for health
for i in $(seq 1 30); do
  if curl -sf "$E2E_BASE_URL/healthz" >/dev/null 2>&1; then break; fi
  sleep 0.5
done

echo "[e2e] running Playwright tests…"
pytest tests/e2e -q --no-header

echo "[e2e] done."
