// API layer for the SpoofVane console.
//
// `ApiClient` is the abstract contract every screen depends on (DI seam so
// widget tests inject a fake without touching the network). `HttpApiClient` is
// the production implementation: it tries the real FastAPI backend first
// (GET /api/...) and on any failure falls back to the offline seed, flipping
// `source` to SEED — so the UI is always honest about live vs canned data.
// Base URL is configurable via --dart-define=API_BASE=...
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'models.dart';
import 'seed.dart';

enum DataSource { live, seed }

/// The contract screens depend on. Swap the implementation in tests.
abstract class ApiClient {
  ValueNotifier<DataSource> get source;
  Future<bool> health();
  Future<List<Brand>> brands();
  Future<List<Alert>> alerts();
  Future<List<Alert>> triageQueue();
  Future<Alert> alert(String id);
  Future<List<Alert>> deepfakes();
  Future<List<Cluster>> clusters();
  Future<List<CostRow>> cost();
  Future<List<AuditRow>> audit();
  Future<List<ReviewItem>> reviewQueue();
  Future<List<Takedown>> takedowns();
  Future<List<ComplianceControl>> compliance();
  Future<List<Agent>> agents();
  Future<List<AdminUser>> adminUsers();
  Future<List<Tenant>> tenants();
  Future<List<DemoHealthRow>> demoHealth();
  Future<List<PricingPlan>> pricing();
  Future<List<UsageMetric>> usage();
  Future<List<Invoice>> invoices();
  Future<List<ApiKey>> apiKeys();
  Future<ScanResult> scan(String url, String brand, {bool demo = false});
}

/// Global accessor. Production code reads `Api.instance`; tests assign a fake to
/// `Api.instance` in setUp and restore it in tearDown.
class Api {
  Api._();
  static ApiClient instance = HttpApiClient();
}

class HttpApiClient implements ApiClient {
  HttpApiClient({http.Client? client, String? base})
      : _client = client ?? http.Client(),
        _base = base ??
            const String.fromEnvironment('API_BASE',
                defaultValue: 'http://localhost:8000');

  final http.Client _client;
  final String _base;

  @override
  final ValueNotifier<DataSource> source = ValueNotifier(DataSource.live);

  Future<dynamic> _getJson(String path) async {
    final r = await _client
        .get(Uri.parse('$_base$path'))
        .timeout(const Duration(seconds: 4));
    if (r.statusCode >= 200 && r.statusCode < 300) {
      return jsonDecode(r.body);
    }
    throw Exception('${r.statusCode} $path');
  }

  Future<T> _withSeed<T>(Future<T> Function() live, T fallback) async {
    try {
      final v = await live();
      source.value = DataSource.live;
      return v;
    } catch (_) {
      source.value = DataSource.seed;
      return fallback;
    }
  }

  List<Map<String, dynamic>> _asList(dynamic body) {
    if (body is List) return body.cast<Map<String, dynamic>>();
    if (body is Map && body['items'] is List) {
      return (body['items'] as List).cast<Map<String, dynamic>>();
    }
    if (body is Map && body['alerts'] is List) {
      return (body['alerts'] as List).cast<Map<String, dynamic>>();
    }
    throw Exception('not a list');
  }

  @override
  Future<bool> health() async {
    try {
      await _getJson('/healthz');
      source.value = DataSource.live;
      return true;
    } catch (_) {
      source.value = DataSource.seed;
      return false;
    }
  }

  @override
  Future<List<Brand>> brands() => _withSeed(
        () async =>
            _asList(await _getJson('/api/brands')).map(Brand.fromJson).toList(),
        seedBrands,
      );

  @override
  Future<List<Alert>> alerts() => _withSeed(
        () async =>
            _asList(await _getJson('/api/alerts')).map(Alert.fromJson).toList(),
        seedAlerts,
      );

  @override
  Future<List<Alert>> triageQueue() => _withSeed(
        () async {
          final all =
              _asList(await _getJson('/api/alerts')).map(Alert.fromJson).toList();
          return all.where((a) => a.verdict != Verdict.benign).toList();
        },
        seedAlerts.where((a) => a.verdict != Verdict.benign).toList(),
      );

  @override
  Future<Alert> alert(String id) => _withSeed(
        () async =>
            Alert.fromJson(await _getJson('/api/alerts/$id') as Map<String, dynamic>),
        seedAlerts.firstWhere((a) => a.id == id, orElse: () => seedAlerts.first),
      );

  // These endpoints now exist on the backend (/api/deepfakes, /api/clusters,
  // /api/cost). They go LIVE when the backend is reachable + has data, and fall
  // back to seed (tagged SEED) otherwise. Deepfakes is LIVE once a deepfake-
  // family alert is seeded (build 071, via the real DeepfakeScorer).
  @override
  Future<List<Alert>> deepfakes() => _withSeed<List<Alert>>(
        () async {
          final rows =
              _asList(await _getJson('/api/deepfakes')).map(Alert.fromJson).toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedDeepfakes,
      );

  @override
  Future<List<Cluster>> clusters() => _withSeed<List<Cluster>>(
        () async {
          final rows =
              _asList(await _getJson('/api/clusters')).map(Cluster.fromJson).toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedClusters,
      );

  @override
  Future<List<CostRow>> cost() => _withSeed<List<CostRow>>(
        () async {
          final rows =
              _asList(await _getJson('/api/cost')).map(CostRow.fromJson).toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedCost,
      );

  @override
  Future<List<AuditRow>> audit() => _withSeed(
        () async =>
            _asList(await _getJson('/api/audit-log')).map(AuditRow.fromJson).toList(),
        seedAudit,
      );

  // Review is LIVE-when-present: /api/review serves real pending HITL items
  // (build 066); empty -> honest SEED fallback.
  @override
  Future<List<ReviewItem>> reviewQueue() => _withSeed<List<ReviewItem>>(
        () async {
          final rows = _asList(await _getJson('/api/review'))
              .map(ReviewItem.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedReview,
      );

  // Takedowns is LIVE: /api/takedowns routes real high-severity phish alerts
  // through the real W6 takedown router (build 069); empty -> SEED fallback.
  @override
  Future<List<Takedown>> takedowns() => _withSeed<List<Takedown>>(
        () async {
          final rows = _asList(await _getJson('/api/takedowns'))
              .map(Takedown.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedTakedowns,
      );

  // Compliance is LIVE: /api/compliance serves real controls from the NIST AI
  // RMF + compliance modules (build 065). Seed remains the offline fallback.
  @override
  Future<List<ComplianceControl>> compliance() =>
      _withSeed<List<ComplianceControl>>(
        () async {
          final rows = _asList(await _getJson('/api/compliance'))
              .map(ComplianceControl.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedCompliance,
      );

  // Agents is LIVE: /api/admin/agents enumerates the real agent registry with
  // kill-switch state + governance budgets (build 067). Seed = offline fallback.
  @override
  Future<List<Agent>> agents() => _withSeed<List<Agent>>(
        () async {
          final rows =
              _asList(await _getJson('/api/admin/agents')).map(Agent.fromJson).toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedAgents,
      );

  // Users is LIVE: /api/admin/users serves real UserRow+MembershipRow rows
  // (build 067). Seed = offline fallback.
  @override
  Future<List<AdminUser>> adminUsers() => _withSeed<List<AdminUser>>(
        () async {
          final rows = _asList(await _getJson('/api/admin/users'))
              .map(AdminUser.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedAdminUsers,
      );

  // Tenants is LIVE: /api/console/tenants serves real TenantRepo rows (build
  // 065). Seed remains the offline fallback.
  @override
  Future<List<Tenant>> tenants() => _withSeed<List<Tenant>>(
        () async {
          final rows = _asList(await _getJson('/api/console/tenants'))
              .map(Tenant.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedTenants,
      );

  // Demo-health is LIVE: /api/console/demo-health computes coverage from the DB
  // (build 065). Seed remains the offline fallback.
  @override
  Future<List<DemoHealthRow>> demoHealth() => _withSeed<List<DemoHealthRow>>(
        () async {
          final rows = _asList(await _getJson('/api/console/demo-health'))
              .map(DemoHealthRow.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedDemoHealth,
      );

  // Pricing is LIVE: /api/pricing serves the backend tier catalogue
  // (src.common.pricing, build 065). Seed remains the offline fallback.
  @override
  Future<List<PricingPlan>> pricing() => _withSeed<List<PricingPlan>>(
        () async {
          final rows = _asList(await _getJson('/api/pricing'))
              .map(PricingPlan.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedPricing,
      );

  // Usage is LIVE: /api/usage computes metered consumption vs plan allowance
  // from real cost/alert data (build 065). Seed remains the offline fallback.
  @override
  Future<List<UsageMetric>> usage() => _withSeed<List<UsageMetric>>(
        () async {
          final rows = _asList(await _getJson('/api/usage'))
              .map(UsageMetric.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedUsage,
      );

  // Invoices is LIVE: /api/billing/invoices derives invoices from the tenant's
  // real cost-event history + plan fee (build 070); empty -> SEED fallback.
  @override
  Future<List<Invoice>> invoices() => _withSeed<List<Invoice>>(
        () async {
          final rows = _asList(await _getJson('/api/billing/invoices'))
              .map(Invoice.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedInvoices,
      );

  // API keys is LIVE-when-present: /api/api-keys serves real ApiKeyRepo rows
  // (masked, never secrets; build 066); empty -> honest SEED fallback.
  @override
  Future<List<ApiKey>> apiKeys() => _withSeed<List<ApiKey>>(
        () async {
          final rows = _asList(await _getJson('/api/api-keys'))
              .map(ApiKey.fromJson)
              .toList();
          if (rows.isEmpty) throw Exception('empty -> seed');
          return rows;
        },
        seedApiKeys,
      );

  // Live "Scan this URL now" (DEMO-1): POST /api/scan runs a REAL Bright Data
  // fetch + a REAL multi-LLM ensemble verdict. No seed fallback — on failure it
  // returns a ScanResult with mode='error' carrying the real reason, so the demo
  // never shows a fake "live" result. Longer timeout (real BD + LLM calls).
  //
  // When [demo] is true we return a canned sample result WITHOUT calling the
  // backend, so a presenter can show the result shape with no spend / no
  // network (clearly tagged demo via mode != 'live').
  @override
  Future<ScanResult> scan(String url, String brand, {bool demo = false}) async {
    if (demo) return _demoScan(url, brand);
    try {
      final r = await _client
          .post(
            Uri.parse('$_base/api/scan'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'url': url, 'brand': brand}),
          )
          .timeout(const Duration(seconds: 60));
      if (r.statusCode >= 200 && r.statusCode < 300) {
        source.value = DataSource.live;
        return ScanResult.fromJson(jsonDecode(r.body) as Map<String, dynamic>);
      }
      return ScanResult(
          mode: 'error', url: url, stage: 'http',
          error: 'Backend returned HTTP ${r.statusCode}');
    } catch (e) {
      return ScanResult(
          mode: 'error', url: url, stage: 'network',
          error: 'Could not reach the backend: $e');
    }
  }

  // A canned multi-LLM ensemble result for offline/demo mode. mode='demo' so
  // the UI clearly marks it as sample data, never as a live call.
  ScanResult _demoScan(String url, String brand) => ScanResult(
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
        evidence: const [
          'Login form posts credentials to an off-brand domain.',
          'Brand logo is pixel-matched to the canonical asset.',
          'Domain registered 3 days ago via a bulk registrar.',
        ],
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
