"""
Registrar takedown automation.

When an alert is confirmed (manually or via auto-confirm policy), DoppelDomain
can file a takedown request with the registrar or hosting provider of the
suspect domain. We do NOT auto-file by default — these are legal acts that
can have real consequences if a false positive slips through. The takedown
draft is generated automatically; the *submission* is gated behind explicit
analyst sign-off or a policy flag (``settings.auto_takedown_above_severity``).

Architecture mirrors integrations/:

* Each registrar implements :class:`TakedownProvider`
* A registry routes a request to the right provider for a domain
* Submissions are recorded in a takedown_log table (in-memory for now,
  expanded to durable storage in production)

In MOCK_MODE no real submissions go out — providers log a structured event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...common.logging import get_logger
from ...common.models import Alert, Brand, InspectionResult, VerdictResult
from ...common.settings import get_settings

logger = get_logger(__name__)


@dataclass(slots=True)
class TakedownResult:
    provider: str
    success: bool
    case_id: str | None = None
    error: str | None = None
    details: dict | None = None


class TakedownProvider(Protocol):
    name: str

    def supports(self, registrar: str | None, host: str) -> bool:
        """Return True iff this provider should handle this host."""
        ...

    def is_enabled(self) -> bool:
        ...

    def submit(
        self,
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> TakedownResult:
        ...


PROVIDERS: list[TakedownProvider] = []


def register_provider(provider: TakedownProvider) -> None:
    PROVIDERS.append(provider)
    logger.debug("takedown.provider_registered", name=provider.name)


def submit_takedown(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> TakedownResult:
    """Route the takedown request to the first matching enabled provider."""
    host = _host_from_alert(alert)
    registrar = inspection.registrar
    for provider in PROVIDERS:
        if not provider.is_enabled():
            continue
        if not provider.supports(registrar, host):
            continue
        result = provider.submit(alert, brand, inspection, verdict)
        logger.info(
            "takedown.submitted",
            provider=provider.name,
            alert_id=alert.id,
            success=result.success,
            case_id=result.case_id,
        )
        return result
    return TakedownResult(
        provider="none",
        success=False,
        error="No enabled takedown provider matched this host/registrar",
    )


def _host_from_alert(alert: Alert) -> str:
    from urllib.parse import urlparse
    return (urlparse(alert.suspect_url).hostname or "").lower()


def _mock_mode() -> bool:
    return get_settings().mock_mode
