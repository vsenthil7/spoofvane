# Depth Ledger (review §0.1, §V8-4)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

For each implemented module: the live provider/path, the deterministic replay
mechanism, and the differential-probe evidence that output varies with input.
"Deterministic" is never "constant" (§V8-4).

| Module | Live path | Deterministic path | Differential evidence |
|--------|-----------|--------------------|-----------------------|
| A1 serp_scanner | SERP API `brd_json=1` over BD proxy | hash-seeded synthetic SERP | `test_serp_is_input_dependent` |
| A4 registrar_feed | BD Datasets WHOIS snapshot | hash-seeded WHOIS record | `test_registrar_feed_uses_bd_dataset_tag` |
| A5 openphish_feed | OpenPhish/URLhaus HTTPS pull | per-feed synthetic rows | `test_openphish_dedupes_and_tags` |
| A7 url_shortener | residential-proxy redirect follow | deterministic chain | `test_url_shortener_records_full_chain` |
| B1 browser_inspector | Playwright-over-CDP to brd.superproxy.io | seeded render record | depth probe `B1 scraping_browser` |
| B4 tls_inspector | real TLS handshake | seeded cert chain (some self-signed) | `test_tls_input_dependent_and_detects_self_signed` |
| B5 har_collector | CDP network log | seeded HAR entries | `test_har_input_dependent` |
| B7 whois_enricher | RDAP + BD WHOIS | seeded ASN/rDNS | `test_whois_flags_bulletproof_hosting` |
| C1 composite (calibrated) | — (pure) | Platt sigmoid | `test_calibration_not_raw_passthrough` |
| C2 url_risk | — (pure) | entropy/token/TLD features | `test_url_risk_higher_for_phishy_url` |
| C6 kit_fingerprinter | — (pure) | 13 kit signatures + JS-hash | `test_at_least_twelve_kits` |
| C8 cluster_score | — (pure) | union-find over shared signals | `test_clustering_links_shared_signals` |
| C9 voiceprint | ECAPA-TDNN embedding | hash-seeded 192-dim embedding | `test_voiceprint_deterministic_but_not_constant` |
| C10 deepfake_score | face+lipsync+C2PA ensemble | seeded ensemble | `test_deepfake_input_dependent` |
| D2 gpt_verdict | GPT-5 tool-use | seeded verdict w/ per-model jitter | `test_models_are_input_dependent` |
| D3 gemini_verdict | Gemini 3 tool-use | seeded verdict | (group D probe) |
| D5 verdict_merger | — (pure) | dissent-aware merge | `test_dissent_discounts_confidence_and_escalates` |
| D7 mitre_enricher | bundled ATT&CK corpus | deterministic map | `test_mitre_maps_real_technique_ids` |
| E1–E10 agents | governed live actions | governed execution | `tests/test_agents_s7.py` (15 cases) |
| H5 exec_attack_surface | likeness/voice scan | seeded handles | `test_h5_exec_surface_input_dependent_and_handles` |
| H7 intel_narrator | Claude narrative | templated narrative | `test_h7_narrator_reflects_verdict` |
| H8 kit_explainer | RAG over KB (prompt-cached) | KB lookup | `test_h8_kit_explainer_kb_hit_and_miss` |
