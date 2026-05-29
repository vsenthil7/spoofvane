"""v07 W11 — Email authentication & inbox-trust (Fortra/PhishLabs + BIMI/DMARC).

Ingests DMARC aggregate reports, checks SPF/DKIM alignment, validates BIMI
(DMARC-enforced + VMC), and detects cousin-domain lookalike senders. A spoofing
source IP failing SPF+DKIM flags; an aligned legitimate sender passes. Live
report ingestion (IMAP/S3 RUA mailbox) is 🔒 BLOCKED-ENV (replay default).
"""
from __future__ import annotations

from .base import DmarcReport, DmarcRecord
from .dmarc_monitor import analyze_dmarc, DmarcAnalysis
from .spf_dkim_checker import check_alignment, AlignmentResult
from .bimi_validator import validate_bimi, BimiResult
from .lookalike_sender_detector import detect_lookalike_senders, LookalikeSender

__all__ = [
    "DmarcReport", "DmarcRecord", "analyze_dmarc", "DmarcAnalysis",
    "check_alignment", "AlignmentResult", "validate_bimi", "BimiResult",
    "detect_lookalike_senders", "LookalikeSender",
]
