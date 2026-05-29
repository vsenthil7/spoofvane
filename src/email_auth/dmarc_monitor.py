"""W11 DMARC monitor: analyze a report for unauthorized senders + spoof volume."""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import DmarcReport, DmarcRecord


@dataclass
class DmarcAnalysis:
    domain: str
    total_messages: int
    passing_messages: int
    failing_messages: int
    unauthorized_source_ips: list[str]
    spoofing_volume: int
    pass_rate: float


def analyze_dmarc(report: DmarcReport) -> DmarcAnalysis:
    total = sum(r.count for r in report.records)
    passing = sum(r.count for r in report.records if r.aligned)
    failing = total - passing
    # Unauthorized = failed alignment (neither SPF nor DKIM passed).
    unauth_ips = sorted({r.source_ip for r in report.records if not r.aligned})
    spoof_volume = sum(r.count for r in report.records if not r.aligned)
    pass_rate = round(passing / total, 4) if total else 0.0
    return DmarcAnalysis(
        domain=report.domain,
        total_messages=total,
        passing_messages=passing,
        failing_messages=failing,
        unauthorized_source_ips=unauth_ips,
        spoofing_volume=spoof_volume,
        pass_rate=pass_rate,
    )
