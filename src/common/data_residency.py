"""G12 — data residency: EU / US / APAC / IN routing + provable non-egress.

Resolves the storage/processing region for a tenant and asserts that no data
operation crosses a forbidden boundary. Emits a non-egress proof record that the
CompliancePage (P14) and DATA_RESIDENCY_EVIDENCE doc consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field

REGIONS = {"EU", "US", "APAC", "IN"}
REGION_ENDPOINTS = {
    "EU": "eu-west-1.store.spoofvane.internal",
    "US": "us-east-1.store.spoofvane.internal",
    "APAC": "ap-southeast-1.store.spoofvane.internal",
    "IN": "ap-south-1.store.spoofvane.internal",
}


class ResidencyViolation(Exception):
    pass


@dataclass
class NonEgressProof:
    tenant_id: str
    region: str
    endpoint: str
    operation: str
    crossed_boundary: bool


class DataResidencyGuard:
    def __init__(self) -> None:
        self._tenant_region: dict[str, str] = {}

    def set_region(self, tenant_id: str, region: str) -> None:
        if region not in REGIONS:
            raise ValueError(f"unknown region {region}")
        self._tenant_region[tenant_id] = region

    def region_for(self, tenant_id: str) -> str:
        return self._tenant_region.get(tenant_id, "US")

    def route(self, tenant_id: str, target_region: str, operation: str) -> NonEgressProof:
        home = self.region_for(tenant_id)
        crossed = target_region != home
        if crossed:
            raise ResidencyViolation(
                f"tenant {tenant_id} ({home}) data op '{operation}' to {target_region} blocked")
        return NonEgressProof(tenant_id, home, REGION_ENDPOINTS[home], operation, crossed)
