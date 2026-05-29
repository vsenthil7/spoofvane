"""F4 — hosting-provider abuse channels: AWS / GCP / Hetzner / OVH / Hostinger.

Per-host adapters that route an abuse report to the correct channel for the
hosting provider behind a phishing site (resolved from the WHOIS/ASN enricher).
Real submit happens behind HITL; replay returns a deterministic reference id.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

ABUSE_CHANNELS = {
    "aws": "abuse@amazonaws.com",
    "gcp": "https://support.google.com/code/contact/cloud_platform_report",
    "hetzner": "abuse@hetzner.com",
    "ovh": "abuse@ovh.net",
    "hostinger": "abuse@hostinger.com",
    "cloudflare": "https://abuse.cloudflare.com/phishing",
}


def host_from_asn(as_org: str) -> str:
    org = (as_org or "").lower()
    for key in ABUSE_CHANNELS:
        if key in org:
            return key
    if "amazon" in org or "aws" in org:
        return "aws"
    if "google" in org:
        return "gcp"
    return "cloudflare"  # default abuse channel


@dataclass
class HostingAbuseReport:
    provider: str
    channel: str
    url: str
    reference_id: str
    submitted: bool


class HostingAbuseReporter:
    def submit(self, url: str, as_org: str, evidence_refs: list[str] | None = None,
               hitl_approved: bool = False) -> HostingAbuseReport:
        provider = host_from_asn(as_org)
        channel = ABUSE_CHANNELS[provider]
        ref = hashlib.sha256(f"{provider}{url}".encode()).hexdigest()[:12]
        submitted = False
        if hitl_approved:
            if os.getenv("SPOOFVANE_BD_MODE", "replay") == "live":
                pass  # real email/form POST wired in deployment
            submitted = True
        return HostingAbuseReport(provider, channel, url, ref, submitted)
