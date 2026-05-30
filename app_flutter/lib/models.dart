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
