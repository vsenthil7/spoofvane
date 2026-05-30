"""W6 takedown router: selects the right channel(s) by IoC type."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IocType(str, Enum):
    DOMAIN = "domain"
    SOCIAL = "social"
    APP = "app"
    URL = "url"
    CERT = "cert"


class Channel(str, Enum):
    REGISTRAR = "registrar"
    HOST = "host"
    SAFEBROWSING = "google_safebrowsing"
    APWG = "apwg_ecrime"
    CERT_REVOCATION = "cert_revocation"
    SOCIAL_PLATFORM = "social_platform"
    APP_STORE = "app_store"


# IoC type -> ordered list of channels to file with.
_ROUTING = {
    IocType.DOMAIN: [Channel.REGISTRAR, Channel.HOST, Channel.SAFEBROWSING, Channel.APWG],
    IocType.URL: [Channel.HOST, Channel.SAFEBROWSING, Channel.APWG],
    IocType.SOCIAL: [Channel.SOCIAL_PLATFORM],
    IocType.APP: [Channel.APP_STORE],
    IocType.CERT: [Channel.CERT_REVOCATION],
}


@dataclass
class TakedownCase:
    ioc: str
    ioc_type: IocType
    channels: list[Channel]
    status: str = "open"
    opened_at: str = ""
    closed_at: str | None = None
    sla_state: str = "filed"
    evidence_ref: str | None = None
    escalation_tier: str = "auto"


def route_takedown(ioc: str, ioc_type: IocType) -> TakedownCase:
    """Map an IoC to the correct channel(s)."""
    channels = _ROUTING.get(ioc_type, [])
    if not channels:
        raise ValueError(f"no routing for IoC type {ioc_type}")
    from datetime import datetime, timezone
    return TakedownCase(
        ioc=ioc, ioc_type=ioc_type, channels=list(channels),
        opened_at=datetime.now(timezone.utc).isoformat(),
    )
