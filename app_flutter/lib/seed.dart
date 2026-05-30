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
