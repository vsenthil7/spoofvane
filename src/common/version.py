"""SpoofVane build identity and attribution.

Single source of truth for product name, version, coder attribution, and build
timestamp. Imported by the API, the web console footer, the CLI, and every
generated artifact (PDF reports, evidence packs, demo manifests) so the brand
and provenance are stamped consistently everywhere.

Coder:  Claude (Opus 4.8), running in Claude Code
Issued: 29 May 2026, 08:45 BST
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


PRODUCT_NAME = "SpoofVane"
PRODUCT_TAGLINE = (
    "Autonomous Brand, Executive, Deepfake & Fraud Surface Defense Platform"
)
# Renamed from the DoppelDomain v0.4 enterprise lineage. v0.5 is the first
# SpoofVane-branded convergence build incorporating the 08:22 v9 review stack.
VERSION = "0.5.0"
VERSION_CODENAME = "spoofvane-convergence-v9"

# Attribution — required by the product owner: coder name + datetime on every
# downloadable artifact.
CODER = "Claude (Opus 4.8)"
CODER_ENV = "Claude Code (Anthropic CLI)"
BUILD_ISSUED = "2026-05-29T08:45:00+01:00"  # 08:45 BST
BUILD_ISSUED_HUMAN = "29 May 2026, 08:45 BST"

# Review lineage this build incorporates (newest first).
REVIEW_LINEAGE = [
    "Perplexity v9 (08:22 BST 2026-05-29)",
    "Claude v8 (07:51 BST 2026-05-29)",
    "ChatGPT v7 (07:19 BST 2026-05-29)",
    "Claude v6 (07:09 BST 2026-05-29)",
]


@dataclass(frozen=True)
class BuildIdentity:
    product: str
    tagline: str
    version: str
    codename: str
    coder: str
    coder_env: str
    issued: str
    issued_human: str
    review_lineage: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)

    def stamp(self) -> str:
        """One-line provenance stamp for artifact footers."""
        return (
            f"{self.product} v{self.version} ({self.codename}) — "
            f"built by {self.coder} in {self.coder_env}, {self.issued_human}"
        )


def build_identity() -> BuildIdentity:
    return BuildIdentity(
        product=PRODUCT_NAME,
        tagline=PRODUCT_TAGLINE,
        version=VERSION,
        codename=VERSION_CODENAME,
        coder=CODER,
        coder_env=CODER_ENV,
        issued=BUILD_ISSUED,
        issued_human=BUILD_ISSUED_HUMAN,
        review_lineage=tuple(REVIEW_LINEAGE),
    )


def artifact_footer(now: datetime | None = None) -> str:
    """Footer line stamped onto generated PDFs / evidence packs / manifests."""
    rendered = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%SZ")
    return f"{build_identity().stamp()} · rendered {rendered}"
