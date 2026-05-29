"""
Attack-family classification.

Phishing isn't homogeneous — different victim industries get hit by different
kit families with characteristic signatures:

* **m365** — Microsoft 365 / Outlook / SharePoint credential-harvest kits
* **banking** — bank login clones (heavy on account-number / OTP fields)
* **crypto** — crypto wallet drainers, exchange logins, seed-phrase capture
* **payment** — checkout-page clones, card-data exfiltration
* **support** — fake "tech support" sites driving call-back fraud
* **generic** — anything not matching the above

Knowing the family upfront lets us:

1. Score with family-specific weights — a crypto kit with `seed phrase` in the
   DOM gets a strong dom_score boost beyond what generic structural similarity
   would give.
2. Route the verdict via family-specific prompts — the LLM is given the
   relevant kit signatures to look for, raising precision on known patterns.
3. Surface family in the alert so analysts can batch-triage by kit type.

The classifier is intentionally rule-based with explicit DOM keyword
signatures. A more sophisticated production version would learn a model from
labelled examples, but the rule-based baseline is more inspectable and easier
to tune at hackathon scale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..common.logging import get_logger
from ..common.models import InspectionResult
from ..storage.blob_store import read_blob

logger = get_logger(__name__)


class AttackFamily(str, Enum):
    """Known phishing-kit families."""

    M365 = "m365"
    BANKING = "banking"
    CRYPTO = "crypto"
    PAYMENT = "payment"
    SUPPORT = "support"
    GENERIC = "generic"


@dataclass(frozen=True, slots=True)
class FamilyClassification:
    """Result of classifying an inspection by attack family."""

    family: AttackFamily
    confidence: float  # 0..1
    signatures_hit: list[str]
    notes: str

    def as_dict(self) -> dict:
        return {
            "family": self.family.value,
            "confidence": self.confidence,
            "signatures_hit": list(self.signatures_hit),
            "notes": self.notes,
        }


# --------------------------------------------------------------------------- #
# Family signatures
# --------------------------------------------------------------------------- #
# Each tuple is (signature_label, regex). The regex is run against the
# lower-cased rendered DOM. The family with the most matches wins; ties go
# to the most-specific family in the order below (generic last).

_M365_SIGNATURES = [
    ("microsoft-branding", re.compile(r"microsoft|office\s?365|outlook|sharepoint|onedrive")),
    ("aad-login", re.compile(r"login\.microsoftonline\.com|aad|azure\s?ad")),
    ("o365-mailbox-full", re.compile(r"mailbox\s+(?:is\s+)?full|quota\s+exceeded")),
    ("teams-meeting-lure", re.compile(r"teams\s+meeting|voicemail\s+received")),
    ("docusign-lure", re.compile(r"docusign|secure\s+document|signed\s+document")),
]

_BANKING_SIGNATURES = [
    ("account-number", re.compile(r"account\s+number|sort\s+code|routing\s+number|iban")),
    ("otp-field", re.compile(r"one[\s-]?time\s+(?:passcode|password|pin)|otp")),
    ("card-pan", re.compile(r"card\s+number|primary\s+account\s+number|pan")),
    ("balance-lure", re.compile(r"insufficient\s+funds|unusual\s+activity|locked\s+account")),
    ("bank-keywords", re.compile(r"online\s+banking|net\s?banking|mobile\s+banking")),
]

_CRYPTO_SIGNATURES = [
    ("seed-phrase", re.compile(r"seed\s+phrase|recovery\s+phrase|mnemonic|12[\s-]?word")),
    ("wallet-connect", re.compile(r"walletconnect|connect\s+wallet|metamask|trust\s+wallet")),
    ("exchange-brand", re.compile(r"binance|coinbase|kraken|kucoin|okx|crypto\.com|gemini")),
    ("airdrop-lure", re.compile(r"airdrop|claim\s+(?:your|token|reward)|free\s+(?:eth|btc|sol)")),
    ("private-key", re.compile(r"private\s+key|secret\s+key|export\s+key")),
]

_PAYMENT_SIGNATURES = [
    ("cvv-field", re.compile(r"cvv|cvc|cv2|card\s+(?:security|verification)\s+code")),
    ("expiry-field", re.compile(r"expir(?:y|ation)\s+date|exp\.?\s+date|mm/?yy")),
    ("checkout-keywords", re.compile(r"complete\s+(?:payment|purchase|order)|shipping\s+address")),
    ("3ds-lure", re.compile(r"3-?d\s?secure|verified\s+by\s+visa|mastercard\s+securecode")),
]

_SUPPORT_SIGNATURES = [
    ("tech-support", re.compile(r"tech\s+support|call\s+(?:us|now)|toll[\s-]?free")),
    ("scareware", re.compile(r"your\s+(?:computer|pc|device)\s+(?:is\s+)?infected|virus\s+detected")),
    ("phone-number", re.compile(r"\+?1[\s\-.]?\(?8(?:00|88|77|66)\)?[\s\-.]?\d{3}[\s\-.]?\d{4}")),
    ("microsoft-support-lure", re.compile(r"microsoft\s+support|apple\s+support|geek\s+squad")),
]


_FAMILY_TABLE = [
    (AttackFamily.M365, _M365_SIGNATURES),
    (AttackFamily.BANKING, _BANKING_SIGNATURES),
    (AttackFamily.CRYPTO, _CRYPTO_SIGNATURES),
    (AttackFamily.PAYMENT, _PAYMENT_SIGNATURES),
    (AttackFamily.SUPPORT, _SUPPORT_SIGNATURES),
]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def classify(inspection: InspectionResult) -> FamilyClassification:
    """Classify an inspection's rendered DOM into one of the known families.

    Returns GENERIC with low confidence when no signatures match.
    """
    if not inspection.dom_hash:
        return FamilyClassification(
            family=AttackFamily.GENERIC,
            confidence=0.0,
            signatures_hit=[],
            notes="no DOM captured",
        )

    try:
        dom_bytes = read_blob(inspection.dom_hash, ".html")
    except FileNotFoundError:
        return FamilyClassification(
            family=AttackFamily.GENERIC,
            confidence=0.0,
            signatures_hit=[],
            notes="DOM blob missing",
        )

    dom_text = dom_bytes.decode("utf-8", errors="replace").lower()
    return classify_dom_text(dom_text)


def classify_dom_text(dom_text: str) -> FamilyClassification:
    """Classify against a raw DOM string. Exposed for direct testing."""
    dom_text = dom_text.lower()
    best = (AttackFamily.GENERIC, 0, [], "no family signatures matched")
    for family, signatures in _FAMILY_TABLE:
        hits = [label for label, rx in signatures if rx.search(dom_text)]
        if len(hits) > best[1]:
            best = (family, len(hits), hits, _summary(family, hits))

    family, n_hits, hits, notes = best
    if family == AttackFamily.GENERIC:
        confidence = 0.0
    else:
        # Two or more signature hits → high confidence; one hit → medium
        confidence = min(1.0, 0.4 + 0.2 * n_hits)
    return FamilyClassification(
        family=family,
        confidence=round(confidence, 3),
        signatures_hit=hits,
        notes=notes,
    )


def _summary(family: AttackFamily, hits: list[str]) -> str:
    if not hits:
        return f"classified as {family.value}"
    return f"{family.value}: {len(hits)} signature(s) — " + ", ".join(hits[:4])


# --------------------------------------------------------------------------- #
# Scoring weight overrides per family
# --------------------------------------------------------------------------- #
# When a strong family classification is in hand, downstream scoring can use
# these per-family weight overrides to capture what matters most for that
# family. E.g. crypto kits live or die by DOM signatures (seed-phrase fields),
# while M365 kits are mostly recognised by visual layout.


_FAMILY_WEIGHTS = {
    AttackFamily.M365:     {"phash": 0.45, "dom": 0.30, "logo": 0.20, "favicon": 0.05},
    AttackFamily.BANKING:  {"phash": 0.35, "dom": 0.35, "logo": 0.25, "favicon": 0.05},
    AttackFamily.CRYPTO:   {"phash": 0.20, "dom": 0.55, "logo": 0.20, "favicon": 0.05},
    AttackFamily.PAYMENT:  {"phash": 0.30, "dom": 0.45, "logo": 0.20, "favicon": 0.05},
    AttackFamily.SUPPORT:  {"phash": 0.50, "dom": 0.25, "logo": 0.20, "favicon": 0.05},
    AttackFamily.GENERIC:  {"phash": 0.35, "dom": 0.25, "logo": 0.30, "favicon": 0.10},
}


def weights_for_family(family: AttackFamily) -> dict[str, float]:
    """Return the scoring weights to use for a given attack family."""
    return dict(_FAMILY_WEIGHTS[family])
