"""
Public GitHub leak detection.

Phishing-kit authors and operators leak in several ways via public GitHub:

* **Kit source repos** — kit-as-a-service authors host their codebase
  publicly (16Shop, Caffeine source has been mirrored). Detecting a repo
  containing brand-specific assets pre-emptively flags the brand as a target.
* **Stolen-credential dumps** — some operators commit captured credentials
  to GitHub by accident (Git history rewrites are often incomplete).
* **Forks of known phishing kits** that have been customised with the
  target brand's logo / colours.

This source queries Bright Data Web Scraper API against GitHub's public
code search for:

1. Repos containing the brand name + login-form keywords
2. Files containing the brand's canonical login URL but in suspicious
   contexts (PHP files, JavaScript exfil endpoints, etc.)
3. Forks of repos in a curated kit-watchlist with recent commits

Output: a SuspectURL pointing at the offending file, with discovery_metadata
carrying the repo, commit, and matched pattern. The inspection layer fetches
the raw file content via Bright Data Web Unlocker (GitHub aggressively rate-
limits the public API).

In MOCK_MODE this source yields a small set of plausible fixtures.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings

logger = get_logger(__name__)


# Curated kit watchlist — repos known to be phishing kit codebases or
# common forks thereof. Real production maintains hundreds.
_KIT_REPO_WATCHLIST: tuple[str, ...] = (
    "anonghost/16shop-mirror",
    "phishlabs-research/caffeine-leaked",
    "darkforge/tycoon-2fa-source",
    "evilproxy-archive/main",
    "modlishka-fork-collection/all",
)


class GitHubLeakSource:
    """Discovery source for phishing kit / credential leaks on public GitHub."""

    name = "github_leak"

    def __init__(self) -> None:
        self.settings = get_settings()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        if self.settings.mock_mode:
            yield from self._mock_yield(brand)
            return
        logger.warning(
            "github_leak.live_mode_not_implemented",
            note="Set MOCK_MODE=true for fixture data",
        )
        return

    def _mock_yield(self, brand: Brand) -> Iterator[SuspectURL]:
        slug = brand.name.lower().replace(" ", "-")
        now = datetime.now(timezone.utc)

        # 1. A kit repo that mentions the brand
        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url=(
                f"https://github.com/anonghost/16shop-mirror/blob/main/"
                f"templates/{slug}/login.html"
            ),
            source=Source.GITHUB_LEAK,
            discovery_metadata={
                "repo": "anonghost/16shop-mirror",
                "filename": f"templates/{slug}/login.html",
                "matched_pattern": f"brand-asset-fork:{brand.name}",
                "last_commit": (now - timedelta(days=3)).isoformat(),
                "kit_family": "16Shop",
                "stars": 42,
                "warning": "Repo on kit watchlist; this fork was customised for brand",
            },
        )

        # 2. A credential dump (CSV in someone's "test" repo)
        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url=(
                f"https://github.com/random-dev/test-data/blob/main/"
                f"{slug}-creds-dump.csv"
            ),
            source=Source.GITHUB_LEAK,
            discovery_metadata={
                "repo": "random-dev/test-data",
                "filename": f"{slug}-creds-dump.csv",
                "matched_pattern": "credential_dump",
                "last_commit": (now - timedelta(hours=18)).isoformat(),
                "warning": "File appears to contain captured credentials",
            },
        )

        # 3. A fork of EvilProxy with brand-specific config
        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url=(
                f"https://github.com/darkforge/tycoon-{slug}/blob/main/"
                f"config/relay.json"
            ),
            source=Source.GITHUB_LEAK,
            discovery_metadata={
                "repo": f"darkforge/tycoon-{slug}",
                "filename": "config/relay.json",
                "matched_pattern": "kit_fork_with_brand_config",
                "last_commit": (now - timedelta(days=1)).isoformat(),
                "kit_family": "Tycoon-2FA",
                "warning": "Customised kit fork targeting this brand",
            },
        )
