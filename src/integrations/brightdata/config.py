"""Bright Data configuration and execution-mode resolution."""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


class BDMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    MOCK = "mock"


@dataclass(frozen=True)
class BrightDataConfig:
    mode: BDMode
    customer_id: str | None
    zone_serp: str
    zone_unlocker: str
    zone_residential: str
    zone_scraping_browser: str
    api_token: str | None
    cdp_endpoint: str
    mcp_endpoint: str
    fixtures_dir: str
    default_country: str

    @property
    def is_live(self) -> bool:
        return self.mode == BDMode.LIVE

    def require_credentials(self) -> None:
        if self.is_live and not self.api_token:
            raise RuntimeError(
                "SPOOFVANE_BD_MODE=live requires BRIGHTDATA_API_TOKEN. "
                "Use replay mode for credential-free reproducible builds."
            )


@lru_cache(maxsize=1)
def get_bd_config() -> BrightDataConfig:
    mode = BDMode(os.getenv("SPOOFVANE_BD_MODE", "replay").lower())
    fixtures = os.getenv(
        "SPOOFVANE_BD_FIXTURES",
        os.path.join(os.path.dirname(__file__), "fixtures"),
    )
    cid = os.getenv("BRIGHTDATA_CUSTOMER_ID")
    token = os.getenv("BRIGHTDATA_API_TOKEN")
    return BrightDataConfig(
        mode=mode,
        customer_id=cid,
        zone_serp=os.getenv("BRIGHTDATA_ZONE_SERP", "spoofvane_serp"),
        zone_unlocker=os.getenv("BRIGHTDATA_ZONE_UNLOCKER", "spoofvane_unlocker"),
        zone_residential=os.getenv("BRIGHTDATA_ZONE_RESIDENTIAL", "spoofvane_res"),
        zone_scraping_browser=os.getenv("BRIGHTDATA_ZONE_SB", "spoofvane_sb"),
        api_token=token,
        cdp_endpoint=os.getenv(
            "BRIGHTDATA_CDP_ENDPOINT",
            "wss://brd.superproxy.io:9222",
        ),
        mcp_endpoint=os.getenv(
            "BRIGHTDATA_MCP_ENDPOINT",
            "https://mcp.brightdata.com/sse",
        ),
        fixtures_dir=fixtures,
        default_country=os.getenv("SPOOFVANE_BD_DEFAULT_COUNTRY", "us"),
    )
