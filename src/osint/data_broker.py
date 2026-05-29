"""Data-broker exposure check: which brokers list the exec's PII.

Input-dependent: distinct execs are listed by distinct broker sets with
distinct exposed-field sets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import ExecInput, OsintMode, get_osint_mode

_BROKERS = ["Spokeo", "WhitePages", "BeenVerified", "Radaris", "PeopleFinder",
            "Intelius", "TruePeopleSearch", "FastPeopleSearch"]
_FIELDS = ["home_address", "phone", "relatives", "age", "email", "prior_addresses",
           "property_records", "political_affiliation"]


@dataclass
class BrokerListing:
    broker: str
    exposed_fields: list[str]
    opt_out_url: str


@dataclass
class DataBrokerResult:
    exec_name: str
    listings: list[BrokerListing] = field(default_factory=list)
    exposure_score: float = 0.0

    @property
    def all_exposed_fields(self) -> set[str]:
        out: set[str] = set()
        for l in self.listings:
            out.update(l.exposed_fields)
        return out


class DataBrokerSource:
    name = "data_broker"

    def check(self, exec_in: ExecInput) -> DataBrokerResult:
        if get_osint_mode() == OsintMode.LIVE:
            return self._live(exec_in)
        return self._replay(exec_in)

    def _live(self, exec_in: ExecInput) -> DataBrokerResult:  # pragma: no cover - BLOCKED-ENV
        raise NotImplementedError(
            "live data-broker scraping is fixture-backed (ToS + BLOCKED-ENV)")

    def _replay(self, exec_in: ExecInput) -> DataBrokerResult:
        s = exec_in.seed("broker")
        n_brokers = 1 + (s % 5)
        listings: list[BrokerListing] = []
        weighted = 0.0
        for i in range(n_brokers):
            si = exec_in.seed("broker", str(i))
            broker = _BROKERS[(s + i) % len(_BROKERS)]
            n_fields = 1 + (si % 4)
            fields = sorted({_FIELDS[(si >> j) % len(_FIELDS)] for j in range(n_fields)})
            # home_address + phone are the high-risk doxxing fields.
            weighted += sum(2.0 if f in ("home_address", "phone") else 1.0 for f in fields)
            listings.append(BrokerListing(
                broker=broker, exposed_fields=fields,
                opt_out_url=f"https://{broker.lower()}.example/opt-out",
            ))
        score = min(1.0, weighted / 20.0)
        return DataBrokerResult(
            exec_name=exec_in.name, listings=listings, exposure_score=round(score, 3),
        )
