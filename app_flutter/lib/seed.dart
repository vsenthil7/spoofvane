// Offline seed data — mirrors console/src/lib/seed.ts. Lets every screen render
// with the backend DOWN, clearly tagged SEED by the API client.
import 'models.dart';

final seedBrands = <Brand>[
  Brand(id: 'brand_acmebank', name: 'AcmeBank', loginUrl: 'https://acmebank.com/login', targetCountry: 'US', scoreThreshold: 0.65),
  Brand(id: 'brand_globex', name: 'Globex', loginUrl: 'https://globex.com/signin', targetCountry: 'GB', scoreThreshold: 0.6),
];

final seedAlerts = <Alert>[
  Alert(id: 'alert_seed_001', brandId: 'brand_acmebank', url: 'https://acmebank-secure-login.top/verify', verdict: Verdict.phish, composite: 0.91, family: 'banking', kit: '16Shop', renderedFrom: 'US', discoveredAt: '2026-05-29T09:10:00Z', mitreTechniques: ['T1566.002', 'T1598.003']),
  Alert(id: 'alert_seed_002', brandId: 'brand_acmebank', url: 'https://my-acmebank-login.xyz/', verdict: Verdict.suspicious, composite: 0.72, family: 'banking', kit: 'Tycoon-2FA', renderedFrom: 'US', discoveredAt: '2026-05-29T09:25:00Z', mitreTechniques: ['T1566.002']),
  Alert(id: 'alert_seed_003', brandId: 'brand_globex', url: 'https://globex-portal-update.cc/', verdict: Verdict.suspicious, composite: 0.68, family: 'm365', kit: 'EvilProxy', renderedFrom: 'GB', discoveredAt: '2026-05-29T08:50:00Z', mitreTechniques: ['T1566.002', 'T1557']),
  Alert(id: 'alert_seed_004', brandId: 'brand_globex', url: 'https://globex.com/promo', verdict: Verdict.benign, composite: 0.21, renderedFrom: 'GB', discoveredAt: '2026-05-29T07:40:00Z'),
];

final seedDeepfakes = <Alert>[
  Alert(id: 'df_seed_001', brandId: 'brand_acmebank', url: 'https://youtu.be/fake-ceo-clip', verdict: Verdict.phish, composite: 0.88, family: 'deepfake', kit: 'voice-clone', discoveredAt: '2026-05-29T06:30:00Z', mitreTechniques: ['T1656']),
];

final seedClusters = <Cluster>[
  Cluster(id: 1, members: ['alert_seed_001', 'alert_seed_002'], risk: 0.86),
  Cluster(id: 2, members: ['alert_seed_003'], risk: 0.68),
];

final seedAudit = <AuditRow>[
  AuditRow(seq: 1, actorRole: 'analyst', action: 'alert.triage', outcome: 'ok', ts: '2026-05-29T09:30:00Z', hash: 'a1b2c3d4'),
  AuditRow(seq: 2, actorRole: 'reviewer', action: 'takedown.approve', outcome: 'ok', ts: '2026-05-29T09:35:00Z', hash: 'e5f6a7b8'),
];

final seedCost = <CostRow>[
  CostRow(product: 'serp', usd: 4.21),
  CostRow(product: 'unlocker', usd: 9.84),
  CostRow(product: 'scraping_browser', usd: 12.50),
  CostRow(product: 'residential', usd: 6.10),
];

final seedReview = <ReviewItem>[
  ReviewItem(id: 'rv_001', action: 'takedown.submit', targetUrl: 'https://acmebank-secure-login.top/verify', verdict: Verdict.phish, raisedBy: 'analyst.kim', ts: '2026-05-29T09:32:00Z'),
  ReviewItem(id: 'rv_002', action: 'cred_poison.deploy', targetUrl: 'https://my-acmebank-login.xyz/', verdict: Verdict.suspicious, raisedBy: 'analyst.lee', ts: '2026-05-29T09:40:00Z'),
  // Raised by the default reviewer -> demonstrates the SoD block in the UI.
  ReviewItem(id: 'rv_003', action: 'takedown.submit', targetUrl: 'https://globex-portal-update.cc/', verdict: Verdict.suspicious, raisedBy: 'reviewer.osei', ts: '2026-05-29T09:44:00Z'),
];

final seedTakedowns = <Takedown>[
  Takedown(id: 'td_001', targetUrl: 'https://acmebank-secure-login.top/verify', channel: 'Cloudflare', channelKind: 'registrar', state: TakedownState.acknowledged, referenceId: 'CF-AB-481920', updatedAt: '2026-05-29T10:05:00Z'),
  Takedown(id: 'td_002', targetUrl: 'https://acmebank-secure-login.top/verify', channel: 'Hetzner', channelKind: 'hosting', state: TakedownState.submitted, referenceId: 'HZ-2026-77310', updatedAt: '2026-05-29T10:02:00Z'),
  Takedown(id: 'td_003', targetUrl: 'https://my-acmebank-login.xyz/', channel: 'Namecheap', channelKind: 'registrar', state: TakedownState.resolved, referenceId: 'NC-559021', updatedAt: '2026-05-29T11:20:00Z'),
  Takedown(id: 'td_004', targetUrl: 'https://globex-portal-update.cc/', channel: 'AWS', channelKind: 'hosting', state: TakedownState.rejected, referenceId: 'AWS-ABUSE-99812', updatedAt: '2026-05-29T11:45:00Z'),
  Takedown(id: 'td_005', targetUrl: 'https://globex-portal-update.cc/', channel: 'GoDaddy', channelKind: 'registrar', state: TakedownState.draft, referenceId: '—', updatedAt: '2026-05-29T09:50:00Z'),
];

final seedCompliance = <ComplianceControl>[
  ComplianceControl(framework: 'SOC 2', controlId: 'CC6.1', title: 'Logical access controls', status: ControlStatus.met, evidence: 'RBAC + SSO enforced; access reviews quarterly'),
  ComplianceControl(framework: 'SOC 2', controlId: 'CC7.2', title: 'Security event monitoring', status: ControlStatus.met, evidence: 'Hash-chained audit log; alerting on anomalies'),
  ComplianceControl(framework: 'SOC 2', controlId: 'CC8.1', title: 'Change management', status: ControlStatus.partial, evidence: 'CI gates in place; formal CAB pending'),
  ComplianceControl(framework: 'ISO 27001', controlId: 'A.12.4', title: 'Logging and monitoring', status: ControlStatus.met, evidence: 'Tamper-evident audit trail retained 1y'),
  ComplianceControl(framework: 'ISO 27001', controlId: 'A.9.2', title: 'User access management', status: ControlStatus.met, evidence: 'Joiner/mover/leaver workflow; SoD enforced'),
  ComplianceControl(framework: 'DORA', controlId: 'Art.17', title: 'ICT incident management', status: ControlStatus.partial, evidence: 'Runbooks drafted; major-incident drill scheduled'),
  ComplianceControl(framework: 'DORA', controlId: 'Art.28', title: 'Third-party risk (Bright Data)', status: ControlStatus.met, evidence: 'Sub-processor DPA on file; usage capped per tenant'),
  ComplianceControl(framework: 'NIS2', controlId: 'Art.21', title: 'Cyber risk-management measures', status: ControlStatus.gap, evidence: 'Risk register WIP; board sign-off outstanding'),
];
