"""Application settings loaded from environment / .env.

All configuration goes through this module — no module reaches into
os.environ directly. This keeps tests trivially overridable and makes
the surface area of "what is configurable" obvious.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for SpoofVane."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── Run mode ──────────────────────────────────────────────────────
    mock_mode: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    environment: Literal["dev", "staging", "prod"] = "dev"

    # ─── Storage ───────────────────────────────────────────────────────
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'spoofvane.db'}"
    evidence_dir: Path = REPO_ROOT / "data" / "evidence"
    reports_dir: Path = REPO_ROOT / "data" / "reports"
    canonical_dir: Path = REPO_ROOT / "data" / "canonical"

    # ─── Anthropic ─────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ─── LLM ensemble providers (v07 D4 — GPT + Gemini diversity) ──────
    # Naming mirrors the sibling projects (Verixa/Forensa/ATRIO) so one dev
    # .env can back several repos. Blank key => that provider's verdict stays
    # on the deterministic replay/mock lane (live call is BLOCKED-ENV).
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro-latest"

    # ─── Bright Data ───────────────────────────────────────────────────
    brightdata_api_key: str = ""
    brightdata_cdp_endpoint: str = "wss://brd.superproxy.io:9222"
    brightdata_proxy_host: str = "brd.superproxy.io"
    brightdata_proxy_port: int = 22225
    brightdata_proxy_user: str = ""
    brightdata_proxy_pass: str = ""
    brightdata_serp_host: str = "brd.superproxy.io:33335"
    brightdata_unlocker_zone: str = "unlocker"
    # v06 §D — monthly spend envelope; back-pressure kill-switch trips at 80%.
    brightdata_monthly_usd: float = Field(default=500.0, gt=0.0)

    # ─── Webhooks ──────────────────────────────────────────────────────
    slack_webhook_url: str = ""
    splunk_hec_url: str = ""
    splunk_hec_token: str = ""
    sentinel_workspace_id: str = ""
    sentinel_shared_key: str = ""

    # ─── Enterprise integrations (added in v0.2) ───────────────────────
    servicenow_instance: str = ""  # e.g. acme.service-now.com
    servicenow_user: str = ""
    servicenow_pass: str = ""
    pagerduty_routing_key: str = ""
    pagerduty_service_url: str = "https://events.pagerduty.com/v2/enqueue"
    taxii_collection_url: str = ""
    taxii_username: str = ""
    taxii_password: str = ""
    webhook_signing_secret: str = ""  # for HMAC-SHA256 outbound signatures
    generic_webhook_url: str = ""  # generic JSON receiver (e.g. a customer's SIEM bridge)

    # ─── Takedown automation (added in v0.2) ───────────────────────────
    cloudflare_abuse_email: str = ""
    cloudflare_api_token: str = ""
    namecheap_api_user: str = ""
    namecheap_api_key: str = ""
    godaddy_api_key: str = ""
    godaddy_api_secret: str = ""

    # ─── Scoring ───────────────────────────────────────────────────────
    score_threshold_composite: float = Field(default=0.65, ge=0.0, le=1.0)
    score_weight_phash: float = Field(default=0.35, ge=0.0, le=1.0)
    score_weight_dom: float = Field(default=0.25, ge=0.0, le=1.0)
    score_weight_logo: float = Field(default=0.30, ge=0.0, le=1.0)
    score_weight_favicon: float = Field(default=0.10, ge=0.0, le=1.0)

    # ─── Multi-region inspection (v0.2) ────────────────────────────────
    geo_cloaking_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    multi_region_enabled: bool = False  # off by default — costs more BD spend
    multi_region_countries: str = "US,GB,DE,BR,IN"  # comma-separated ISO codes

    # ─── Auth (v0.2) ───────────────────────────────────────────────────
    require_auth: bool = False  # when True, every API call requires an API key

    # ─── Identity & sessions (v0.3) ────────────────────────────────────
    # secret_key signs JWTs and session cookies. MUST be overridden in prod.
    secret_key: str = "dev-only-insecure-key-change-me-in-production-0123456789"
    session_cookie_name: str = "dd_session"
    session_max_age_hours: int = 12
    password_min_length: int = 8
    # When True, unauthenticated browser hits redirect to /login. Off in dev
    # so the existing demo dashboard still works without a login.
    web_login_required: bool = False

    # ─── OIDC / SSO (v0.3) ─────────────────────────────────────────────
    # Generic OIDC; works with Okta, Entra ID, Auth0, Google Workspace, etc.
    oidc_enabled: bool = False
    oidc_issuer: str = ""              # e.g. https://accounts.google.com
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_url: str = "http://127.0.0.1:8000/auth/oidc/callback"
    oidc_scopes: str = "openid email profile"

    # ─── Email / SMTP (v0.3) ───────────────────────────────────────────
    email_enabled: bool = False        # when False, emails are logged not sent
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = "SpoofVane Alerts <alerts@spoofvane.example>"
    app_base_url: str = "http://127.0.0.1:8000"

    # ─── Active learning (v0.2) ────────────────────────────────────────
    active_learning_enabled: bool = True
    active_learning_min_samples: int = 20  # need this many triage outcomes before adjusting

    # ─── Cost attribution (v0.2) ───────────────────────────────────────
    cost_per_serp_call_usd: float = 0.0015
    cost_per_unlocker_call_usd: float = 0.0030
    cost_per_browser_minute_usd: float = 0.0050
    cost_alert_per_tenant_per_day_usd: float = 50.0

    # ─── Observability (v0.2) ──────────────────────────────────────────
    prometheus_enabled: bool = True
    otel_endpoint: str = ""  # e.g. http://localhost:4317

    def ensure_dirs(self) -> None:
        """Create runtime directories if missing."""
        for d in (self.evidence_dir, self.reports_dir, self.canonical_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached)."""
    s = Settings()
    s.ensure_dirs()
    return s
