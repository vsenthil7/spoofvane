"""Test suite. Forces MOCK_MODE before any src imports."""

import os

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("SLACK_WEBHOOK_URL", "")
os.environ.setdefault("SPLUNK_HEC_URL", "")
