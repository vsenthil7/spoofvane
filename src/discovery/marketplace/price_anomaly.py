"""W3 price anomaly: flags listings priced implausibly below MSRP."""
from __future__ import annotations


def price_anomaly_score(price: float, msrp: float, threshold: float = 0.70) -> float:
    """Return anomaly score in [0,1]. A price >= `threshold` (default 70%)
    below MSRP is a strong counterfeit signal; scales with the discount depth."""
    if msrp <= 0 or price < 0:
        return 0.0
    discount = 1.0 - (price / msrp)  # fraction below MSRP
    if discount < threshold:
        # Below the alert threshold — mild signal proportional to discount.
        return round(max(0.0, discount / threshold) * 0.3, 4)
    # At/over threshold — high signal, saturating toward a near-free price.
    return round(min(1.0, 0.6 + (discount - threshold) / (1.0 - threshold) * 0.4), 4)
