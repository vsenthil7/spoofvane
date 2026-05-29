"""
Telegram / paste-site phishing-kit marketplace monitor.

Phishing-as-a-service operators advertise kits on:

* **Telegram channels** with names like `@phishkits24`, `@evilproxy_sales`
* **Pastebin / paste.ee / paste.gg** drops containing kit configs, panel
  URLs, and brand-targeting lists
* **Underground forums** indexed via Tor mirrors

By the time these advertisements appear, the kit is being deployed against
named targets — often before the first phishing URL goes live. Catching the
advertisement is the earliest possible signal we can act on.

This source consumes a curated channel/paste list, pulls recent messages
or paste content via Bright Data Web Unlocker (Telegram public previews,
paste-site rendered pages), and emits a SuspectURL for any channel post
or paste mentioning the brand by name.

Output URLs point at the message/paste itself; the inspection layer fetches
the message body, the verdict layer reasons over the structured kit-targeting
evidence ("Channel @phishkits24 advertised a $200 kit targeting acme on
2026-05-26 — kit panel URL was ``acme-portal[.]xyz``").

In MOCK_MODE we emit fixed fixtures.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings

logger = get_logger(__name__)


# Curated channel watchlist. Real production keeps hundreds.
_TELEGRAM_CHANNELS: tuple[str, ...] = (
    "@phishkits24",
    "@evilproxy_sales",
    "@aitm_marketplace",
    "@scampage_drops",
)


class TelegramKitSource:
    """Discovery source for kit-marketplace mentions on Telegram + paste sites."""

    name = "telegram_kit"

    def __init__(self) -> None:
        self.settings = get_settings()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        if self.settings.mock_mode:
            yield from self._mock_yield(brand)
            return
        logger.warning(
            "telegram_kit.live_mode_not_implemented",
            note="Set MOCK_MODE=true for fixture data",
        )
        return

    def _mock_yield(self, brand: Brand) -> Iterator[SuspectURL]:
        slug = brand.name.lower().replace(" ", "-")
        now = datetime.now(timezone.utc)

        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url=f"https://t.me/phishkits24/{4928}",
            source=Source.TELEGRAM_KIT,
            discovery_metadata={
                "channel": "@phishkits24",
                "post_id": 4928,
                "posted_at": (now - timedelta(hours=6)).isoformat(),
                "kit_advertised": "16Shop variant",
                "price_usd": 200,
                "message_excerpt": f"New {brand.name} login page kit — $200, full panel.",
                "panel_url_hint": f"{slug}-portal.xyz",
            },
        )
        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url="https://pastebin.com/QqRk4Z9X",
            source=Source.TELEGRAM_KIT,
            discovery_metadata={
                "channel": "pastebin",
                "paste_id": "QqRk4Z9X",
                "posted_at": (now - timedelta(hours=2)).isoformat(),
                "kit_advertised": "Tycoon-2FA fork",
                "message_excerpt": f"Tycoon kit pre-configured for {brand.name}",
                "panel_url_hint": f"tycoon-{slug}.io",
            },
        )
        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url=f"https://t.me/aitm_marketplace/{1024}",
            source=Source.TELEGRAM_KIT,
            discovery_metadata={
                "channel": "@aitm_marketplace",
                "post_id": 1024,
                "posted_at": (now - timedelta(hours=12)).isoformat(),
                "kit_advertised": "EvilProxy",
                "price_usd": 450,
                "message_excerpt": f"EvilProxy AiTM kit, {brand.name} preset included",
                "panel_url_hint": f"ep-{slug}-relay.app",
            },
        )
