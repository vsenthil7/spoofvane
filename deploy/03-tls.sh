#!/usr/bin/env bash
# SpoofVane · TLS via Caddy + Let's Encrypt (03-tls.sh)
#   DOMAIN=spoofvane.example.com ssh root@<IP> bash -s < deploy/03-tls.sh
#
# Writes a production Caddyfile that serves the SPA + proxies the API on 443
# with automatic Let's Encrypt for DOMAIN, and a compose override that publishes
# 80/443. Falls back with a clear message if DOMAIN is unset (stays on :8081).

set -euo pipefail
exec > >(tee -a /var/log/spoofvane-tls.log) 2>&1

TARGET_DIR="/srv/spoofvane/spoofvane"
cd "$TARGET_DIR"

if [ -z "${DOMAIN:-}" ]; then
    echo "[tls] DOMAIN not set; staying on http://<IP>:8081 (no TLS)." >&2
    echo "[tls] Re-run with: DOMAIN=spoofvane.example.com bash -s < deploy/03-tls.sh"
    exit 0
fi
echo "[tls] domain: $DOMAIN"

PUBLIC_IP=$(curl -fsS https://api.ipify.org || echo unknown)
RESOLVED=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -n1 || echo unknown)
if [ "$RESOLVED" != "$PUBLIC_IP" ]; then
    echo "[tls] WARNING: $DOMAIN resolves to $RESOLVED but this box is $PUBLIC_IP." >&2
    echo "[tls]          Let's Encrypt will fail until DNS propagates. Continuing..."
fi

# Production Caddyfile (TLS).
cat > deploy/caddy/Caddyfile.prod <<EOF
{
    email admin@${DOMAIN#*.}
    auto_https on
}

http://$DOMAIN {
    redir https://$DOMAIN{uri} permanent
}

https://$DOMAIN {
    encode zstd gzip
    handle /api/* { reverse_proxy api:8000 }
    handle /healthz { reverse_proxy api:8000 }
    handle {
        root * /srv/app
        try_files {path} /index.html
        file_server
    }
    log { output stdout; format json }
}
EOF
echo "[tls] wrote deploy/caddy/Caddyfile.prod"

# Compose override: mount the prod Caddyfile + publish 80/443.
cat > deploy/docker-compose.prod.yml <<EOF
services:
  web:
    ports:
      - "80:80"
      - "443:443"
      - "8081:8080"
    volumes:
      - ./deploy/caddy/Caddyfile.prod:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
EOF
echo "[tls] wrote deploy/docker-compose.prod.yml"

docker compose \
    -f deploy/docker-compose.yml \
    -f deploy/docker-compose.prod.yml \
    --env-file .env \
    up -d web

echo "[tls] waiting 30s for Let's Encrypt issuance..."
sleep 30
if curl -fsS "https://$DOMAIN/healthz" >/dev/null 2>&1; then
    echo "[tls] TLS up at https://$DOMAIN"
    curl -s "https://$DOMAIN/healthz" | jq . || true
else
    echo "[tls] HTTPS not responding yet; check 'docker logs spoofvane-web' + DNS." >&2
fi
