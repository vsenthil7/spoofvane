# SpoofVane — Vultr deployment playbook

From an Ubuntu 24.04 VM to a public demo URL where a judge can open the console
and run a live multi-LLM scan. Mirrors the proven ATRIO deploy pattern (Docker
Compose + Caddy + Let's Encrypt), trimmed for SpoofVane's lean stack
(FastAPI + SQLite + a static Flutter web bundle).

## Stack that gets deployed

| Service | Container | Internal port | Public |
|---|---|---|---|
| API (FastAPI/uvicorn, the real backend) | `spoofvane-api` | 8000 | none (internal only) |
| Console (Caddy serving the Flutter SPA + proxying /api) | `spoofvane-web` | 8080 | **host :8081 (pre-TLS), then 443** |

The browser calls the **same origin** (`/api/...`), which Caddy proxies to the
api container — no CORS, no separate API domain. SQLite lives on a named Docker
volume (`spoofvane_data`) so the demo data survives restarts.

## IMPORTANT — this box may already run another product

You said a sibling product ($36 + $100/mo) is already on Vultr. Two safe paths:

- **Safest: a fresh, separate Vultr instance** for SpoofVane. Zero risk to the
  running product. (~$24/mo for 2 vCPU / 4 GB, billed hourly; halt it when not
  demoing.)
- **Same box (co-located):** the scripts are written to be polite about this —
  `01-bootstrap.sh` only **adds** ufw rules (never `ufw --force reset`), skips
  Docker install if it's already there, and SpoofVane's web container publishes
  **host port 8081** (not 8080) to avoid clashing. Still: before running, paste
  me the output of `sudo ss -tlnp` and `docker ps` so I confirm 8081/8000 are
  free and nothing collides.

## What you (human) do

### 1. (If fresh box) create the VM
Vultr → Cloud Compute → Regular Performance (NOT GPU). Ubuntu 24.04 LTS x64,
2 vCPU / 4 GB is plenty. Add your SSH key before creating.

### 2. Send me three things
1. Public IPv4.
2. `ssh root@<IP> "echo connected; uname -a"` output.
3. (For HTTPS) a subdomain A-record pointed at the IP, e.g. `spoofvane.<domain>`.
   No domain → we stay on `http://<IP>:8081` (fine for a demo; TLS needs a name).

Also for the same-box case: `sudo ss -tlnp` and `docker ps` output.

## What I do (after IP + the port check)

### 3. Bootstrap
```bash
ssh root@<IP> bash -s < deploy/01-bootstrap.sh
```
Adds ufw rules (22/80/443/8081), installs Docker if missing, fail2ban.

### 4. Deploy (pass the API keys inline so they never hit git)
```bash
ssh root@<IP> \
  ANTHROPIC_API_KEY=sk-ant-... \
  OPENAI_API_KEY=sk-... \
  BRIGHTDATA_API_TOKEN=... BRIGHTDATA_API_KEY=... BRIGHTDATA_CUSTOMER_ID=hl_... \
  GEMINI_API_KEY=...   # optional; omit while the key is suspended \
  bash -s < deploy/02-deploy.sh
```
Clones the repo, writes `.env` from `prod.env.example`, injects the keys,
auto-generates `SECRET_KEY`, builds + starts the stack, seeds the demo DB,
waits for `/healthz`. Public at `http://<IP>:8081`.

### 5. TLS (if you have a domain)
```bash
ssh root@<IP> DOMAIN=spoofvane.<yourdomain> bash -s < deploy/03-tls.sh
```
Swaps in a production Caddyfile + opens 80/443 with automatic Let's Encrypt.

### 6. Verify
```bash
curl -s https://spoofvane.<yourdomain>/healthz        # {"status":"ok",...}
# Open the URL, go to "Live Scan", paste a URL, watch the live ensemble run.
```

## Cost
2 vCPU / 4 GB ≈ $0.036/hr (~$24/mo), billed hourly. A 1-week demo window ≈ $6.
Pause when idle: `vultr-cli instance halt <id>` (or halt in the dashboard).
Live scans also spend real Anthropic/OpenAI + Bright Data per scan (~$0.01/scan).

## Files
| File | Purpose |
|---|---|
| `01-bootstrap.sh` | OS prep + Docker (polite to an existing product) |
| `02-deploy.sh` | Clone + .env + key injection + build + seed + healthcheck |
| `03-tls.sh` | Caddy + Let's Encrypt once a DOMAIN points at the box |
| `Dockerfile.api` | FastAPI/uvicorn image |
| `Dockerfile.web` | Build Flutter web → serve via Caddy |
| `docker-compose.yml` | api + web (Caddy is the only public entrypoint) |
| `caddy/Caddyfile` | pre-TLS :8080 (mapped to host :8081) |
| `prod.env.example` | production env template (no secrets committed) |
