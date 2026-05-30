// Shared test double for ApiClient. Returns deterministic in-memory data with
// no network, so widget tests are fast and hermetic. The `forcedSource` lets a
// test assert LIVE vs SEED rendering.
import 'package:flutter/foundation.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/models.dart';
import 'package:spoofvane_app/seed.dart';

class FakeApi implements ApiClient {
  FakeApi({DataSource forcedSource = DataSource.live})
      : source = ValueNotifier(forcedSource);

  @override
  final ValueNotifier<DataSource> source;

  @override
  Future<bool> health() async => source.value == DataSource.live;

  @override
  Future<List<Brand>> brands() async => seedBrands;

  @override
  Future<List<Alert>> alerts() async => seedAlerts;

  @override
  Future<List<Alert>> triageQueue() async =>
      seedAlerts.where((a) => a.verdict != Verdict.benign).toList();

  @override
  Future<Alert> alert(String id) async =>
      seedAlerts.firstWhere((a) => a.id == id, orElse: () => seedAlerts.first);

  @override
  Future<List<Alert>> deepfakes() async => seedDeepfakes;

  @override
  Future<List<Cluster>> clusters() async => seedClusters;

  @override
  Future<List<CostRow>> cost() async => seedCost;

  @override
  Future<List<AuditRow>> audit() async => seedAudit;

  @override
  Future<List<ReviewItem>> reviewQueue() async => seedReview;

  @override
  Future<List<Takedown>> takedowns() async => seedTakedowns;

  @override
  Future<List<ComplianceControl>> compliance() async => seedCompliance;

  @override
  Future<List<Agent>> agents() async => seedAgents;

  @override
  Future<List<AdminUser>> adminUsers() async => seedAdminUsers;

  @override
  Future<List<Tenant>> tenants() async => seedTenants;

  @override
  Future<List<DemoHealthRow>> demoHealth() async => seedDemoHealth;

  @override
  Future<List<PricingPlan>> pricing() async => seedPricing;

  @override
  Future<List<UsageMetric>> usage() async => seedUsage;

  @override
  Future<List<Invoice>> invoices() async => seedInvoices;

  @override
  Future<List<ApiKey>> apiKeys() async => seedApiKeys;

  /// Deterministic fake scan result so widget tests are hermetic. A test can
  /// override this to simulate phish / error paths.
  ScanResult Function(String url, String brand)? scanStub;

  @override
  Future<ScanResult> scan(String url, String brand, {bool demo = false}) async {
    if (scanStub != null) return scanStub!(url, brand);
    if (demo) {
      return ScanResult(
        mode: 'demo',
        url: url,
        host: Uri.tryParse(url.startsWith('http') ? url : 'https://$url')?.host ?? url,
        brand: brand,
        fetchProduct: 'Bright Data Web Unlocker',
        fetchStatus: 200,
        htmlLen: 18432,
        fetchLatencyMs: 1180,
        verdict: Verdict.phish,
        confidence: 0.86,
        severity: 'critical',
        evidence: const ['Login form posts to an off-brand domain.'],
        suggestedAction: 'takedown',
        model: 'claude-sonnet-4-6',
        members: [
          ScanMember(name: 'Claude', model: 'claude-sonnet-4-6', verdict: Verdict.phish, confidence: 0.92, latencyMs: 4600, tokensIn: 1180, tokensOut: 240, costUsd: 0.0071),
          ScanMember(name: 'GPT', model: 'gpt-4o', verdict: Verdict.phish, confidence: 0.88, latencyMs: 1700, tokensIn: 1180, tokensOut: 210, costUsd: 0.0050),
          ScanMember(name: 'Gemini', model: 'gemini-1.5-pro', verdict: Verdict.suspicious, confidence: 0.71, latencyMs: 2100, tokensIn: 1180, tokensOut: 190, costUsd: 0.0024),
        ],
        modelsUsed: const ['Claude', 'GPT', 'Gemini'],
        dissent: true,
        agreementRatio: 0.667,
        llmLatencyMs: 8400,
        tokensIn: 3540,
        tokensOut: 640,
        llmCostUsd: 0.0145,
        totalCostUsd: 0.016,
        totalLatencyMs: 9580,
      );
    }
    return ScanResult(
      mode: 'live',
      url: url,
      host: Uri.tryParse(url)?.host ?? url,
      brand: brand,
      fetchProduct: 'Bright Data Web Unlocker',
      fetchStatus: 200,
      htmlLen: 528,
      fetchLatencyMs: 1190,
      verdict: Verdict.suspicious,
      confidence: 0.74,
      severity: 'high',
      evidence: const [
        'Login form posts credentials to an off-brand domain.',
        'Brand logo is pixel-matched to the canonical asset.',
      ],
      suggestedAction: 'watch',
      model: 'claude-sonnet-4-6',
      members: [
        ScanMember(name: 'Claude', model: 'claude-sonnet-4-6', verdict: Verdict.suspicious, confidence: 0.78, latencyMs: 4200, tokensIn: 1100, tokensOut: 210, costUsd: 0.0066),
        ScanMember(name: 'GPT', model: 'gpt-4o', verdict: Verdict.suspicious, confidence: 0.70, latencyMs: 1600, tokensIn: 1100, tokensOut: 180, costUsd: 0.0046),
      ],
      modelsUsed: const ['Claude', 'GPT'],
      dissent: false,
      agreementRatio: 1.0,
      llmLatencyMs: 5800,
      tokensIn: 2200,
      tokensOut: 390,
      llmCostUsd: 0.0112,
      totalCostUsd: 0.0127,
      totalLatencyMs: 6980,
    );
  }
}
