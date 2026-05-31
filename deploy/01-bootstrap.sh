#!/usr/bin/env bash
# SpoofVane · Vultr bootstrap (01-bootstrap.sh)
# Run on a fresh Ubuntu 24.04 LTS x64 VM via:
#   ssh root@<IP> bash -s < deploy/01-bootstrap.sh
# Idempotent: safe to re-run.
#
# IMPORTANT: if this box ALREADY runs another product, do NOT reset ufw blindly.
# This script only ADDS the rules SpoofVane needs and never removes existing
# ones (no `ufw --force reset`). Review `ufw status` after running.

set -euo pipefail
exec > >(tee -a /var/log/spoofvane-bootstrap.log) 2>&1
echo "[bootstrap] start $(date -u +%FT%TZ)"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release ufw fail2ban git jq

timedatectl set-timezone Europe/London || true

# ----- ufw: ADD SpoofVane's ports without disturbing existing rules -----
# (No reset — protects any product already running on this box.)
ufw allow 22/tcp  comment 'ssh' || true
ufw allow 80/tcp  comment 'http (caddy le-challenge + redirect)' || true
ufw allow 443/tcp comment 'https (caddy)' || true
ufw allow 8081/tcp comment 'spoofvane http demo until tls' || true
yes | ufw enable || true

# ----- fail2ban (harmless if already present) -----
systemctl enable --now fail2ban || true

# ----- Docker (skip if already installed by the other product) -----
if ! command -v docker >/dev/null 2>&1; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
else
    echo "[bootstrap] docker already present: $(docker --version)"
fi

mkdir -p /srv/spoofvane
echo "[bootstrap] docker: $(docker --version)"
echo "[bootstrap] compose: $(docker compose version)"
ufw status verbose || true
echo "[bootstrap] done $(date -u +%FT%TZ)"
echo "Next: ssh root@<IP> ANTHROPIC_API_KEY=... OPENAI_API_KEY=... BRIGHTDATA_API_TOKEN=... bash -s < deploy/02-deploy.sh"
