// SpoofVane data models. Shapes mirror the backend API (src/api/app.py) and the
// console seed data, so live JSON and offline seed both deserialize cleanly.
import 'package:flutter/material.dart';

enum Verdict { phish, suspicious, benign, unknown }

Verdict verdictFrom(String? s) {
  switch ((s ?? '').toLowerCase()) {
    case 'phish':
      return Verdict.phish;
    case 'suspicious':
      return Verdict.suspicious;
    case 'benign':
      return Verdict.benign;
    default:
      return Verdict.unknown;
  }
}

Color verdictColor(Verdict v) {
  switch (v) {
    case Verdict.phish:
      return const Color(0xFFFF4D57);
    case Verdict.suspicious:
      return const Color(0xFFFFB020);
    case Verdict.benign:
      return const Color(0xFF3DDC84);
    case Verdict.unknown:
      return const Color(0xFF93A1B8);
  }
}

class Brand {
  final String id;
  final String name;
  final String loginUrl;
  final String targetCountry;
  final double scoreThreshold;

  Brand({
    required this.id,
    required this.name,
    required this.loginUrl,
    required this.targetCountry,
    required this.scoreThreshold,
  });

  factory Brand.fromJson(Map<String, dynamic> j) => Brand(
        id: (j['id'] ?? j['brand_id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        loginUrl: (j['loginUrl'] ?? j['login_url'] ?? '').toString(),
        targetCountry: (j['targetCountry'] ?? j['target_country'] ?? '').toString(),
        scoreThreshold:
            ((j['scoreThreshold'] ?? j['score_threshold'] ?? 0.65) as num).toDouble(),
      );
}

class Alert {
  final String id;
  final String brandId;
  final String url;
  final Verdict verdict;
  final double composite;
  final String? family;
  final String? kit;
  final String? renderedFrom;
  final String discoveredAt;
  final List<String> mitreTechniques;

  Alert({
    required this.id,
    required this.brandId,
    required this.url,
    required this.verdict,
    required this.composite,
    this.family,
    this.kit,
    this.renderedFrom,
    required this.discoveredAt,
    this.mitreTechniques = const [],
  });

  factory Alert.fromJson(Map<String, dynamic> j) => Alert(
        id: (j['id'] ?? '').toString(),
        brandId: (j['brandId'] ?? j['brand_id'] ?? '').toString(),
        url: (j['url'] ?? '').toString(),
        verdict: verdictFrom(j['verdict']?.toString()),
        composite: ((j['composite'] ?? j['composite_score'] ?? 0) as num).toDouble(),
        family: j['family']?.toString(),
        kit: j['kit']?.toString(),
        renderedFrom: (j['renderedFrom'] ?? j['rendered_from'])?.toString(),
        discoveredAt:
            (j['discoveredAt'] ?? j['discovered_at'] ?? '').toString(),
        mitreTechniques: ((j['mitreTechniques'] ?? j['mitre_techniques'] ?? []) as List)
            .map((e) => e.toString())
            .toList(),
      );
}

class Cluster {
  final int id;
  final List<String> members;
  final double risk;
  Cluster({required this.id, required this.members, required this.risk});

  factory Cluster.fromJson(Map<String, dynamic> j) => Cluster(
        id: (j['id'] ?? 0) as int,
        members: ((j['members'] ?? []) as List).map((e) => e.toString()).toList(),
        risk: ((j['risk'] ?? 0) as num).toDouble(),
      );
}

class CostRow {
  final String product;
  final double usd;
  CostRow({required this.product, required this.usd});
  factory CostRow.fromJson(Map<String, dynamic> j) =>
      CostRow(product: (j['product'] ?? '').toString(), usd: ((j['usd'] ?? 0) as num).toDouble());
}

class AuditRow {
  final int seq;
  final String actorRole;
  final String action;
  final String outcome;
  final String ts;
  final String hash;
  AuditRow({
    required this.seq,
    required this.actorRole,
    required this.action,
    required this.outcome,
    required this.ts,
    required this.hash,
  });
  factory AuditRow.fromJson(Map<String, dynamic> j) => AuditRow(
        seq: (j['seq'] ?? 0) as int,
        actorRole: (j['actorRole'] ?? j['actor_role'] ?? '').toString(),
        action: (j['action'] ?? '').toString(),
        outcome: (j['outcome'] ?? '').toString(),
        ts: (j['ts'] ?? '').toString(),
        hash: (j['hash'] ?? '').toString(),
      );
}

/// A human-in-the-loop review item: a consequential action (e.g. a takedown)
/// awaiting reviewer approval. Segregation of duties: the reviewer must differ
/// from the analyst who raised it.
class ReviewItem {
  final String id;
  final String action; // e.g. takedown.submit
  final String targetUrl;
  final Verdict verdict;
  final String raisedBy; // analyst actor id
  final String ts;

  ReviewItem({
    required this.id,
    required this.action,
    required this.targetUrl,
    required this.verdict,
    required this.raisedBy,
    required this.ts,
  });

  factory ReviewItem.fromJson(Map<String, dynamic> j) => ReviewItem(
        id: (j['id'] ?? '').toString(),
        action: (j['action'] ?? '').toString(),
        targetUrl: (j['targetUrl'] ?? j['target_url'] ?? '').toString(),
        verdict: verdictFrom(j['verdict']?.toString()),
        raisedBy: (j['raisedBy'] ?? j['raised_by'] ?? '').toString(),
        ts: (j['ts'] ?? '').toString(),
      );
}

/// Takedown status across one abuse channel (registrar or hosting provider).
enum TakedownState { draft, submitted, acknowledged, resolved, rejected }

TakedownState takedownStateFrom(String? s) {
  switch ((s ?? '').toLowerCase()) {
    case 'submitted':
      return TakedownState.submitted;
    case 'acknowledged':
      return TakedownState.acknowledged;
    case 'resolved':
      return TakedownState.resolved;
    case 'rejected':
      return TakedownState.rejected;
    default:
      return TakedownState.draft;
  }
}

class Takedown {
  final String id;
  final String targetUrl;
  final String channel; // e.g. Cloudflare (registrar), AWS (hosting-abuse)
  final String channelKind; // registrar | hosting
  final TakedownState state;
  final String referenceId; // provider ticket / case id
  final String updatedAt;

  Takedown({
    required this.id,
    required this.targetUrl,
    required this.channel,
    required this.channelKind,
    required this.state,
    required this.referenceId,
    required this.updatedAt,
  });

  factory Takedown.fromJson(Map<String, dynamic> j) => Takedown(
        id: (j['id'] ?? '').toString(),
        targetUrl: (j['targetUrl'] ?? j['target_url'] ?? '').toString(),
        channel: (j['channel'] ?? '').toString(),
        channelKind: (j['channelKind'] ?? j['channel_kind'] ?? '').toString(),
        state: takedownStateFrom(j['state']?.toString()),
        referenceId: (j['referenceId'] ?? j['reference_id'] ?? '').toString(),
        updatedAt: (j['updatedAt'] ?? j['updated_at'] ?? '').toString(),
      );
}

Color takedownStateColor(TakedownState s) {
  switch (s) {
    case TakedownState.resolved:
      return const Color(0xFF3DDC84);
    case TakedownState.acknowledged:
    case TakedownState.submitted:
      return const Color(0xFF36C2CE);
    case TakedownState.rejected:
      return const Color(0xFFFF4D57);
    case TakedownState.draft:
      return const Color(0xFF93A1B8);
  }
}

/// A compliance control's status within a framework (SOC 2 / ISO 27001 / etc).
enum ControlStatus { met, partial, gap, notApplicable }

ControlStatus controlStatusFrom(String? s) {
  switch ((s ?? '').toLowerCase()) {
    case 'met':
      return ControlStatus.met;
    case 'partial':
      return ControlStatus.partial;
    case 'gap':
      return ControlStatus.gap;
    default:
      return ControlStatus.notApplicable;
  }
}

Color controlStatusColor(ControlStatus s) {
  switch (s) {
    case ControlStatus.met:
      return const Color(0xFF3DDC84);
    case ControlStatus.partial:
      return const Color(0xFFFFB020);
    case ControlStatus.gap:
      return const Color(0xFFFF4D57);
    case ControlStatus.notApplicable:
      return const Color(0xFF5E6E88);
  }
}

class ComplianceControl {
  final String framework; // SOC 2 | ISO 27001 | DORA | NIS2
  final String controlId; // e.g. CC6.1, A.12.4
  final String title;
  final ControlStatus status;
  final String evidence; // short evidence reference

  ComplianceControl({
    required this.framework,
    required this.controlId,
    required this.title,
    required this.status,
    required this.evidence,
  });

  factory ComplianceControl.fromJson(Map<String, dynamic> j) => ComplianceControl(
        framework: (j['framework'] ?? '').toString(),
        controlId: (j['controlId'] ?? j['control_id'] ?? '').toString(),
        title: (j['title'] ?? '').toString(),
        status: controlStatusFrom(j['status']?.toString()),
        evidence: (j['evidence'] ?? '').toString(),
      );
}

/// An autonomous agent in the registry (P15) with a governance budget.
class Agent {
  final String id;
  final String name; // e.g. discovery, inspector, takedown-router
  final String tenant;
  final bool running;
  final int runsToday;
  final double budgetUsd; // monthly governance budget
  final double spentUsd; // spent this month

  Agent({
    required this.id,
    required this.name,
    required this.tenant,
    required this.running,
    required this.runsToday,
    required this.budgetUsd,
    required this.spentUsd,
  });

  double get budgetRatio => budgetUsd <= 0 ? 0 : (spentUsd / budgetUsd).clamp(0, 1);

  factory Agent.fromJson(Map<String, dynamic> j) => Agent(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        tenant: (j['tenant'] ?? '').toString(),
        running: (j['running'] ?? false) == true,
        runsToday: (j['runsToday'] ?? j['runs_today'] ?? 0) as int,
        budgetUsd: ((j['budgetUsd'] ?? j['budget_usd'] ?? 0) as num).toDouble(),
        spentUsd: ((j['spentUsd'] ?? j['spent_usd'] ?? 0) as num).toDouble(),
      );
}

/// A user in RBAC management (P16).
class AdminUser {
  final String id;
  final String email;
  final String role; // one of the six role names
  final bool mfaEnabled;
  final String lastActive;

  AdminUser({
    required this.id,
    required this.email,
    required this.role,
    required this.mfaEnabled,
    required this.lastActive,
  });

  factory AdminUser.fromJson(Map<String, dynamic> j) => AdminUser(
        id: (j['id'] ?? '').toString(),
        email: (j['email'] ?? '').toString(),
        role: (j['role'] ?? '').toString(),
        mfaEnabled: (j['mfaEnabled'] ?? j['mfa_enabled'] ?? false) == true,
        lastActive: (j['lastActive'] ?? j['last_active'] ?? '').toString(),
      );
}

/// A tenant in multi-tenant management (P17).
class Tenant {
  final String id;
  final String name;
  final String plan; // free | pro | business | enterprise
  final String region; // data-residency region
  final int seats;
  final bool active;

  Tenant({
    required this.id,
    required this.name,
    required this.plan,
    required this.region,
    required this.seats,
    required this.active,
  });

  factory Tenant.fromJson(Map<String, dynamic> j) => Tenant(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        plan: (j['plan'] ?? '').toString(),
        region: (j['region'] ?? '').toString(),
        seats: (j['seats'] ?? 0) as int,
        active: (j['active'] ?? true) == true,
      );
}

/// A demo-health row (P18): seed completeness / coverage check.
class DemoHealthRow {
  final String check;
  final bool ok;
  final String detail;

  DemoHealthRow({required this.check, required this.ok, required this.detail});

  factory DemoHealthRow.fromJson(Map<String, dynamic> j) => DemoHealthRow(
        check: (j['check'] ?? '').toString(),
        ok: (j['ok'] ?? false) == true,
        detail: (j['detail'] ?? '').toString(),
      );
}

/// A public pricing plan (Pricing page). [priceMonthly] < 0 means "custom".
class PricingPlan {
  final String id;
  final String name;
  final double priceMonthly; // USD/mo billed annually; <0 = custom/contact
  final double priceMonthlyMonthly; // USD/mo billed monthly; <0 = custom
  final String tagline;
  final List<String> features;
  final bool highlighted; // the "most popular" plan
  final String cta;

  PricingPlan({
    required this.id,
    required this.name,
    required this.priceMonthly,
    required this.priceMonthlyMonthly,
    required this.tagline,
    required this.features,
    this.highlighted = false,
    this.cta = 'Start free trial',
  });

  bool get isCustom => priceMonthly < 0;

  factory PricingPlan.fromJson(Map<String, dynamic> j) => PricingPlan(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        priceMonthly: ((j['priceMonthly'] ?? j['price_monthly'] ?? -1) as num).toDouble(),
        priceMonthlyMonthly:
            ((j['priceMonthlyMonthly'] ?? j['price_monthly_monthly'] ?? -1) as num).toDouble(),
        tagline: (j['tagline'] ?? '').toString(),
        features:
            ((j['features'] ?? const []) as List).map((e) => e.toString()).toList(),
        highlighted: (j['highlighted'] ?? false) == true,
        cta: (j['cta'] ?? 'Start free trial').toString(),
      );
}

/// One metered usage line on the Usage page (this billing period).
class UsageMetric {
  final String name; // e.g. Scans, Takedowns, Brands, Bright Data spend
  final double used;
  final double included; // plan allowance; <0 = unlimited
  final String unit; // '', 'USD', etc

  UsageMetric({
    required this.name,
    required this.used,
    required this.included,
    this.unit = '',
  });

  bool get unlimited => included < 0;
  double get ratio => unlimited || included == 0 ? 0 : (used / included).clamp(0, 1);
  bool get overage => !unlimited && used > included;

  factory UsageMetric.fromJson(Map<String, dynamic> j) => UsageMetric(
        name: (j['name'] ?? '').toString(),
        used: ((j['used'] ?? 0) as num).toDouble(),
        included: ((j['included'] ?? -1) as num).toDouble(),
        unit: (j['unit'] ?? '').toString(),
      );
}

/// A billing invoice (Billing page).
class Invoice {
  final String id; // e.g. INV-2026-0042
  final String date;
  final double amountUsd;
  final String status; // paid | due | failed

  Invoice({
    required this.id,
    required this.date,
    required this.amountUsd,
    required this.status,
  });

  factory Invoice.fromJson(Map<String, dynamic> j) => Invoice(
        id: (j['id'] ?? '').toString(),
        date: (j['date'] ?? '').toString(),
        amountUsd: ((j['amountUsd'] ?? j['amount_usd'] ?? 0) as num).toDouble(),
        status: (j['status'] ?? '').toString(),
      );
}

/// An API key (market-standard API keys screen). The secret is only the masked
/// prefix + last4 once created; the full secret is shown once at creation.
class ApiKey {
  final String id;
  final String name; // human label, e.g. "CI pipeline"
  final String prefix; // e.g. sv_live_8f2c
  final String last4;
  final String scope; // read | read_write | admin
  final String created;
  final String lastUsed; // '' = never
  final bool active;

  ApiKey({
    required this.id,
    required this.name,
    required this.prefix,
    required this.last4,
    required this.scope,
    required this.created,
    required this.lastUsed,
    this.active = true,
  });

  String get masked => '$prefix' '${'•' * 8}' '$last4';

  factory ApiKey.fromJson(Map<String, dynamic> j) => ApiKey(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        prefix: (j['prefix'] ?? '').toString(),
        last4: (j['last4'] ?? '').toString(),
        scope: (j['scope'] ?? 'read').toString(),
        created: (j['created'] ?? '').toString(),
        lastUsed: (j['lastUsed'] ?? j['last_used'] ?? '').toString(),
        active: (j['active'] ?? true) == true,
      );
}

/// One model's independent vote within the live ensemble (DEMO-1).
class ScanMember {
  final String name; // Claude | GPT | Gemini
  final String model; // claude-sonnet-4-6, gpt-4o, ...
  final Verdict verdict;
  final double confidence;
  final int latencyMs;
  final int tokensIn;
  final int tokensOut;
  final double costUsd;

  ScanMember({
    required this.name,
    required this.model,
    required this.verdict,
    required this.confidence,
    required this.latencyMs,
    required this.tokensIn,
    required this.tokensOut,
    required this.costUsd,
  });

  factory ScanMember.fromJson(Map<String, dynamic> j) => ScanMember(
        name: (j['name'] ?? '').toString(),
        model: (j['model'] ?? '').toString(),
        verdict: verdictFrom(j['verdict']?.toString()),
        confidence: ((j['confidence'] ?? 0) as num).toDouble(),
        latencyMs: (j['latency_ms'] ?? 0) as int,
        tokensIn: (j['tokens_in'] ?? 0) as int,
        tokensOut: (j['tokens_out'] ?? 0) as int,
        costUsd: ((j['cost_usd'] ?? 0) as num).toDouble(),
      );
}

/// Result of the live "Scan this URL now" loop (POST /api/scan, DEMO-1).
/// [mode] is 'live' on success or 'error' when the live path could not run
/// (we never silently mock — the whole point is to prove the live loop).
class ScanResult {
  final String mode; // live | error
  final String url;
  final String host;
  final String brand;
  // Fetch leg (Bright Data).
  final String fetchProduct;
  final int fetchStatus;
  final int htmlLen;
  final int fetchLatencyMs;
  // Merged ensemble verdict.
  final Verdict verdict;
  final double confidence;
  final String severity;
  final List<String> evidence;
  final String suggestedAction;
  final String model;
  final int llmLatencyMs;
  final int tokensIn;
  final int tokensOut;
  final double llmCostUsd;
  final double totalCostUsd;
  final int totalLatencyMs;
  // Ensemble detail.
  final List<ScanMember> members;
  final List<String> modelsUsed;
  final bool dissent;
  final double agreementRatio;
  final List<String> skipped; // "Gemini: suspended" style notes
  // Error path.
  final String stage; // fetch | verdict | ''
  final String error;

  ScanResult({
    required this.mode,
    required this.url,
    this.host = '',
    this.brand = '',
    this.fetchProduct = '',
    this.fetchStatus = 0,
    this.htmlLen = 0,
    this.fetchLatencyMs = 0,
    this.verdict = Verdict.unknown,
    this.confidence = 0,
    this.severity = '',
    this.evidence = const [],
    this.suggestedAction = '',
    this.model = '',
    this.llmLatencyMs = 0,
    this.tokensIn = 0,
    this.tokensOut = 0,
    this.llmCostUsd = 0,
    this.totalCostUsd = 0,
    this.totalLatencyMs = 0,
    this.members = const [],
    this.modelsUsed = const [],
    this.dissent = false,
    this.agreementRatio = 1,
    this.skipped = const [],
    this.stage = '',
    this.error = '',
  });

  bool get isLive => mode == 'live';

  factory ScanResult.fromJson(Map<String, dynamic> j) {
    final fetch = (j['fetch'] ?? const {}) as Map<String, dynamic>;
    final rawMembers = (j['members'] ?? const []) as List;
    final rawSkipped = (j['skipped'] ?? const []) as List;
    return ScanResult(
      mode: (j['mode'] ?? 'error').toString(),
      url: (j['url'] ?? '').toString(),
      host: (j['host'] ?? '').toString(),
      brand: (j['brand'] ?? '').toString(),
      fetchProduct: (fetch['product'] ?? '').toString(),
      fetchStatus: (fetch['status'] ?? 0) is int ? (fetch['status'] ?? 0) as int : 0,
      htmlLen: (fetch['html_len'] ?? 0) as int,
      fetchLatencyMs: (fetch['latency_ms'] ?? 0) as int,
      verdict: verdictFrom(j['verdict']?.toString()),
      confidence: ((j['confidence'] ?? 0) as num).toDouble(),
      severity: (j['severity'] ?? '').toString(),
      evidence: ((j['evidence'] ?? const []) as List).map((e) => e.toString()).toList(),
      suggestedAction: (j['suggested_action'] ?? '').toString(),
      model: (j['model'] ?? '').toString(),
      llmLatencyMs: (j['llm_latency_ms'] ?? 0) as int,
      tokensIn: (j['tokens_in'] ?? 0) as int,
      tokensOut: (j['tokens_out'] ?? 0) as int,
      llmCostUsd: ((j['llm_cost_usd'] ?? 0) as num).toDouble(),
      totalCostUsd: ((j['total_cost_usd'] ?? 0) as num).toDouble(),
      totalLatencyMs: (j['total_latency_ms'] ?? 0) as int,
      members: rawMembers
          .map((m) => ScanMember.fromJson(m as Map<String, dynamic>))
          .toList(),
      modelsUsed:
          ((j['models_used'] ?? const []) as List).map((e) => e.toString()).toList(),
      dissent: (j['dissent'] ?? false) == true,
      agreementRatio: ((j['agreement_ratio'] ?? 1) as num).toDouble(),
      skipped: rawSkipped.map((s) {
        if (s is Map) return '${s['model']}: ${s['reason']}';
        return s.toString();
      }).toList(),
      stage: (j['stage'] ?? '').toString(),
      error: (j['error'] ?? '').toString(),
    );
  }
}
