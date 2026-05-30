"""SpoofVane commercial pricing — the backend source of truth for plan tiers.

These tiers are set from market norms for brand-protection / anti-phishing SaaS
(positioning vs ZeroFox, Bolster, Red Sift OnDMARC, Doppel, PhishLabs). The
console Pricing page reads these over the API so pricing is owned in one place
(here) rather than hard-coded in the client.

Annual prices are shown as USD/month billed annually; monthly billing is ~20%
higher per month. A negative price means "custom / contact sales".
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PricingPlan:
    id: str
    name: str
    price_monthly: float          # USD/mo billed annually; <0 => custom
    price_monthly_monthly: float  # USD/mo billed monthly; <0 => custom
    tagline: str
    features: list[str]
    highlighted: bool = False
    cta: str = "Start free trial"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "price_monthly": self.price_monthly,
            "price_monthly_monthly": self.price_monthly_monthly,
            "tagline": self.tagline,
            "features": list(self.features),
            "highlighted": self.highlighted,
            "cta": self.cta,
        }


_PLANS: list[PricingPlan] = [
    PricingPlan(
        id="free",
        name="Free",
        price_monthly=0.0,
        price_monthly_monthly=0.0,
        tagline="Protect a single brand and try the platform.",
        cta="Get started",
        features=[
            "1 protected brand",
            "100 scans / month",
            "Phishing + lookalike detection",
            "Community support",
            "7-day evidence retention",
        ],
    ),
    PricingPlan(
        id="pro",
        name="Pro",
        price_monthly=499.0,
        price_monthly_monthly=599.0,
        tagline="For growing teams defending a handful of brands.",
        features=[
            "3 protected brands",
            "5,000 scans / month",
            "Automated takedowns",
            "Campaign clustering",
            "Email support (next business day)",
            "90-day evidence retention",
        ],
    ),
    PricingPlan(
        id="business",
        name="Business",
        price_monthly=1999.0,
        price_monthly_monthly=2399.0,
        tagline="Full-surface defense with deepfake & exec protection.",
        highlighted=True,
        features=[
            "15 protected brands",
            "50,000 scans / month",
            "Deepfake & executive protection",
            "SSO (OIDC) + RBAC",
            "Multi-region cloaking detection",
            "Priority support (4h SLA)",
            "1-year evidence retention",
        ],
    ),
    PricingPlan(
        id="enterprise",
        name="Enterprise",
        price_monthly=-1.0,
        price_monthly_monthly=-1.0,
        tagline="Compliance-grade defense for regulated organisations.",
        cta="Contact sales",
        features=[
            "Unlimited brands & scans",
            "SAML + SCIM provisioning",
            "SOC 2 / ISO 27001 / DORA / NIS2 evidence",
            "Data residency choice",
            "Dedicated CSM + 1h SLA",
            "Custom agent governance & kill-switch",
            "Unlimited evidence retention",
        ],
    ),
]


def all_plans() -> list[PricingPlan]:
    """Return the canonical pricing tiers."""
    return list(_PLANS)


def plan_by_id(plan_id: str) -> PricingPlan | None:
    for p in _PLANS:
        if p.id == plan_id:
            return p
    return None


# Per-plan metered allowances, used by the Usage surface to compute "included"
# limits. -1 means unlimited. Keyed by plan id then metric name.
PLAN_ALLOWANCES: dict[str, dict[str, float]] = {
    "free": {"Scans": 100, "Protected brands": 1, "API calls": 1000, "Takedowns": 0},
    "pro": {"Scans": 5000, "Protected brands": 3, "API calls": 20000, "Takedowns": -1},
    "business": {
        "Scans": 50000, "Protected brands": 15, "API calls": 100000,
        "Takedowns": -1, "Deepfake checks": 5000,
    },
    "enterprise": {
        "Scans": -1, "Protected brands": -1, "API calls": -1,
        "Takedowns": -1, "Deepfake checks": -1,
    },
}
