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
    """Runtime configuration for DoppelDomain."""

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
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'doppeldomain.db'}"
    evidence_dir: Path = REPO_ROOT / "data" / "evidence"
    reports_dir: Path = REPO_ROOT / "data" / "reports"
    canonical_dir: Path = REPO_ROOT / "data" / "canonical"

    # ─── Anthropic ─────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ─── Bright Data ───────────────────────────────────────────────────
    brightdata_api_key: str = ""
    brightdata_cdp_endpoint: str = "wss://brd.superproxy.io:9222"
    brightdata_proxy_host: str = "brd.superproxy.io"
    brightdata_proxy_port: int = 22225
    brightdata_proxy_user: str = ""
    brightdata_proxy_pass: str = ""
    brightdata_serp_host: str = "brd.superproxy.io:33335"
    brightdata_unlocker_zone: str = "unlocker"

    # ─── Webhooks ──────────────────────────────────────────────────────
    slack_webhook_url: str = ""
    splunk_hec_url: str = ""
    splunk_hec_token: str = ""
    sentinel_workspace_id: str = ""
    sentinel_shared_key: str = ""

    # ─── Scoring ───────────────────────────────────────────────────────
    score_threshold_composite: float = Field(default=0.65, ge=0.0, le=1.0)
    score_weight_phash: float = Field(default=0.35, ge=0.0, le=1.0)
    score_weight_dom: float = Field(default=0.25, ge=0.0, le=1.0)
    score_weight_logo: float = Field(default=0.30, ge=0.0, le=1.0)
    score_weight_favicon: float = Field(default=0.10, ge=0.0, le=1.0)

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
