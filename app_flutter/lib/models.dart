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
