# Security Abuse-Case Catalogue (review §V8-5)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

For each offensive/sensitive capability: how an insider or compromised tenant
could misuse it, and the control that prevents it.

| Capability | Abuse scenario | Control |
|-----------|----------------|---------|
| E2 victim_id_agent | Insider correlates session telemetry to deanonymise users for non-security purposes | Named lawful basis required per action; HITL (reviewer≠analyst); audit row records basis |
| E3 cred_poison_agent | Compromised tenant sprays canary creds to frame a third party | Two-person rule + jurisdiction guard (US/GB only) + unique-per-URL canary + hash-chained audit |
| E4 synth_pages_agent | Honeypot deployed outside isolated namespace, hitting real infra | Isolated namespace enforced; two-person + jurisdiction gate; kill-switch |
| H5 exec_attack_surface | Likeness/voice scan repurposed to build a surveillance dossier | Sensitive-agent gate; lawful basis; scan limited to impersonation detection |
