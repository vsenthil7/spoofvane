"""W12 entity model: typed nodes + edges + the cross-surface Finding input."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NodeType(str, Enum):
    DOMAIN = "domain"
    IP = "ip"
    CERT = "cert"
    ASN = "asn"
    REGISTRAR = "registrar"
    SOCIAL = "social"
    APP = "app"
    ACTOR = "actor"
    KIT = "kit"
    VICTIM = "victim"


@dataclass(frozen=True)
class Node:
    type: NodeType
    value: str

    @property
    def id(self) -> str:
        return f"{self.type.value}:{self.value}"


@dataclass
class Edge:
    src: str            # node id
    dst: str            # node id
    relation: str

    def key(self) -> tuple[str, str, str]:
        return (self.src, self.dst, self.relation)


@dataclass
class Finding:
    """A normalized cross-surface finding fed into the graph. Any surface
    (social, appstore, domain, cert, kit, etc.) emits these."""
    finding_id: str
    domain: str | None = None
    ip: str | None = None
    cert_sha: str | None = None
    asn: str | None = None
    registrar: str | None = None
    kit_family: str | None = None
    social_handle: str | None = None
    app_id: str | None = None
    actor: str | None = None
    victim_cluster: str | None = None
    surface: str = "unknown"
