"""W11 base: DMARC aggregate-report model + XML parsing."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class DmarcRecord:
    source_ip: str
    count: int
    disposition: str           # none | quarantine | reject
    dkim_pass: bool
    spf_pass: bool
    header_from: str

    @property
    def aligned(self) -> bool:
        """DMARC passes if either DKIM or SPF aligns + passes."""
        return self.dkim_pass or self.spf_pass


@dataclass
class DmarcReport:
    domain: str
    org_name: str
    report_id: str
    records: list[DmarcRecord] = field(default_factory=list)

    @classmethod
    def from_xml(cls, xml_text: str) -> "DmarcReport":
        """Parse a DMARC aggregate (RUA) report XML into the model."""
        root = ET.fromstring(xml_text)
        meta = root.find("report_metadata")
        pol = root.find("policy_published")
        org = meta.findtext("org_name", "") if meta is not None else ""
        rid = meta.findtext("report_id", "") if meta is not None else ""
        domain = pol.findtext("domain", "") if pol is not None else ""
        records: list[DmarcRecord] = []
        for rec in root.findall("record"):
            row = rec.find("row")
            pe = row.find("policy_evaluated") if row is not None else None
            ident = rec.find("identifiers")
            records.append(DmarcRecord(
                source_ip=row.findtext("source_ip", "") if row is not None else "",
                count=int(row.findtext("count", "0")) if row is not None else 0,
                disposition=pe.findtext("disposition", "none") if pe is not None else "none",
                dkim_pass=(pe.findtext("dkim", "fail") == "pass") if pe is not None else False,
                spf_pass=(pe.findtext("spf", "fail") == "pass") if pe is not None else False,
                header_from=ident.findtext("header_from", "") if ident is not None else "",
            ))
        return cls(domain=domain, org_name=org, report_id=rid, records=records)
