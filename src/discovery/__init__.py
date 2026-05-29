"""Discovery feeds — surface URLs that *might* be brand-impersonation pages.

Three sources implement the ``DiscoverySource`` protocol:
- ``serp.py``        : Bright Data SERP API
- ``cert_stream.py`` : Certificate Transparency feed
- ``new_domains.py`` : Newly-registered domain delta

All emit ``SuspectURL`` instances into the queue.
"""

from .base import DiscoverySource, DiscoveryRunResult
from .serp import SERPSource
from .cert_stream import CertStreamSource
from .new_domains import NewDomainsSource

__all__ = [
    "DiscoverySource",
    "DiscoveryRunResult",
    "SERPSource",
    "CertStreamSource",
    "NewDomainsSource",
]
