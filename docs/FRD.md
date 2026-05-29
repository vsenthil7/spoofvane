# Functional Requirements (FRD) — selected flows

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

## F-DISCOVERY
Given a brand, the system SHALL run all registered discovery sources, dedupe by
URL, exclude the brand's own domain, and queue suspects with source provenance.

## F-INSPECT
For each suspect the system SHALL render via Bright Data Scraping Browser
(country-pinned), capture DOM/screenshot/HAR/TLS, and tag external origins.

## F-VERDICT
The system SHALL produce a calibrated probability and an ensemble verdict;
on model dissent it SHALL discount confidence and escalate to a human reviewer.

## F-AGENT (governed)
Offensive/sensitive agents SHALL require a named lawful basis; egress agents
SHALL additionally require a second authoriser and a permitted data-residency
region; a kill-switch SHALL halt all agents.

## F-DELIVERY
Approved takedowns SHALL route to the correct registrar/hosting abuse channel;
alerts SHALL fan out to Splunk/Sentinel/ServiceNow/PagerDuty/Cortex XSOAR.
