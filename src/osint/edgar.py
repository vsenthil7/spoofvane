"""SEC EDGAR filings pull for an exec / company.

Live mode hits data.sec.gov (🔒 BLOCKED-ENV: no outbound in sandbox); replay
yields a deterministic, input-dependent filing set so two distinct execs get
two distinct filing histories.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import ExecInput, OsintMode, get_osint_mode

_FORM_TYPES = ["4", "8-K", "10-K", "10-Q", "SC 13D", "DEF 14A"]


@dataclass
class Filing:
    form_type: str
    filed_date: str
    accession: str
    summary: str


@dataclass
class EdgarResult:
    exec_name: str
    company: str
    cik: str
    filings: list[Filing] = field(default_factory=list)
    insider_transactions: int = 0


class EdgarSource:
    name = "edgar"

    def lookup(self, exec_in: ExecInput) -> EdgarResult:
        if get_osint_mode() == OsintMode.LIVE:
            return self._live(exec_in)
        return self._replay(exec_in)

    def _live(self, exec_in: ExecInput) -> EdgarResult:  # pragma: no cover - BLOCKED-ENV
        raise NotImplementedError(
            "live EDGAR pull needs outbound to data.sec.gov (BLOCKED-ENV in sandbox)")

    def _replay(self, exec_in: ExecInput) -> EdgarResult:
        s = exec_in.seed("edgar")
        cik = f"{s % 9999999:07d}"
        n = 2 + (s % 5)  # 2..6 filings, varies by exec
        filings: list[Filing] = []
        insider = 0
        for i in range(n):
            si = exec_in.seed("edgar", str(i))
            form = _FORM_TYPES[si % len(_FORM_TYPES)]
            if form == "4":
                insider += 1
            filings.append(Filing(
                form_type=form,
                filed_date=f"2026-{1 + (si % 12):02d}-{1 + (si % 27):02d}",
                accession=f"{cik}-26-{si % 999999:06d}",
                summary=f"{form} for {exec_in.company} ({exec_in.role})",
            ))
        return EdgarResult(
            exec_name=exec_in.name, company=exec_in.company, cik=cik,
            filings=filings, insider_transactions=insider,
        )
