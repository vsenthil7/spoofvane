"""Discovery feeds — surface URLs that *might* be brand-impersonation pages.

Seven sources implement the ``DiscoverySource`` protocol:

* ``serp.py``             : Bright Data SERP API (organic results)
* ``cert_stream.py``      : Certificate Transparency feed
* ``new_domains.py``      : Newly-registered domain delta
* ``paid_ads.py``         : Sponsored / paid-ad SERP slots (v0.2)
* ``mobile_app_store.py`` : Play Store / App Store / APK sideload (v0.2)
* ``github_leak.py``      : Public GitHub kit + credential leak detection (v0.2)
* ``telegram_kit.py``     : Telegram + paste-site kit marketplace mentions (v0.2)
* ``social_media.py``     : Social-platform impersonation profiles/pages (v0.4)

All emit ``SuspectURL`` instances into the queue.
"""

from .base import DiscoverySource, DiscoveryRunResult
from .serp import SERPSource
from .cert_stream import CertStreamSource
from .new_domains import NewDomainsSource
from .paid_ads import PaidAdSource
from .mobile_app_store import MobileAppStoreSource
from .github_leak import GitHubLeakSource
from .telegram_kit import TelegramKitSource
from .social_media import SocialMediaSource

__all__ = [
    "DiscoverySource",
    "DiscoveryRunResult",
    "SERPSource",
    "CertStreamSource",
    "NewDomainsSource",
    "PaidAdSource",
    "MobileAppStoreSource",
    "GitHubLeakSource",
    "TelegramKitSource",
    "SocialMediaSource",
]
