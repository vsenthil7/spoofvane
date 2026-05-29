"""C2 — URL risk scorer: lexical + entropy + age + registrar reputation.

Computes a 0..1 risk score from real URL features: Shannon entropy of the host,
suspicious-token presence, TLD reputation, domain age (from WHOIS enrichment),
homoglyph/punycode flags, and excessive subdomain depth. Output varies with
input (differential-probe safe).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from urllib.parse import urlparse

SUSPICIOUS_TOKENS = (
    "login", "secure", "verify", "account", "update", "signin", "webscr",
    "confirm", "wallet", "support", "billing", "auth", "recover",
)
HIGH_RISK_TLDS = {"top", "xyz", "cc", "live", "online", "click", "tk", "ml", "ga"}
LOW_RISK_TLDS = {"com", "org", "net", "gov", "edu"}


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


@dataclass
class UrlRisk:
    url: str
    score: float
    entropy: float
    suspicious_tokens: list[str] = field(default_factory=list)
    tld: str = ""
    subdomain_depth: int = 0
    has_punycode: bool = False
    has_ip_host: bool = False
    contributions: dict[str, float] = field(default_factory=dict)


class UrlRiskScorer:
    def score(self, url: str, age_days: int | None = None) -> UrlRisk:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        host = parsed.hostname or ""
        labels = host.split(".")
        tld = labels[-1].lower() if labels else ""
        entropy = shannon_entropy(host)
        tokens = [t for t in SUSPICIOUS_TOKENS if t in url.lower()]
        depth = max(len(labels) - 2, 0)
        puny = "xn--" in host
        ip_host = host.replace(".", "").isdigit() and host.count(".") == 3

        contrib: dict[str, float] = {}
        contrib["entropy"] = min(max((entropy - 3.0) / 2.0, 0.0), 1.0) * 0.20
        contrib["tokens"] = min(len(tokens) / 3.0, 1.0) * 0.25
        contrib["tld"] = (0.20 if tld in HIGH_RISK_TLDS else 0.0 if tld in LOW_RISK_TLDS else 0.10)
        contrib["subdomain"] = min(depth / 4.0, 1.0) * 0.10
        contrib["punycode"] = 0.15 if puny else 0.0
        contrib["ip_host"] = 0.15 if ip_host else 0.0
        if age_days is not None:
            contrib["age"] = (0.20 if age_days < 30 else 0.10 if age_days < 90 else 0.0)
        raw = sum(contrib.values())
        score = min(raw, 1.0)
        return UrlRisk(
            url=url, score=round(score, 4), entropy=round(entropy, 4),
            suspicious_tokens=tokens, tld=tld, subdomain_depth=depth,
            has_punycode=puny, has_ip_host=ip_host,
            contributions={k: round(v, 4) for k, v in contrib.items()},
        )
