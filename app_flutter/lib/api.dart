// Typed API client for the SpoofVane FastAPI backend.
//
// Every call tries the real backend first (GET /api/...). On any failure
// (backend down, endpoint missing, CORS) it falls back to the offline seed and
// flips `source` to SEED — exactly like the console's Demo Health pill, so the
// UI is honest about whether data is live or canned. The backend base URL is
// configurable via --dart-define=API_BASE=...
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'models.dart';
import 'seed.dart';

enum DataSource { live, seed }

class Api {
  Api._();
  static final Api instance = Api._();

  static const String base =
      String.fromEnvironment('API_BASE', defaultValue: 'http://localhost:8000');

  /// Last data source, observable so the app bar can show LIVE/SEED.
  final ValueNotifier<DataSource> source = ValueNotifier(DataSource.live);

  Future<dynamic> _getJson(String path) async {
    final r = await http
        .get(Uri.parse('$base$path'))
        .timeout(const Duration(seconds: 4));
    if (r.statusCode >= 200 && r.statusCode < 300) {
      return jsonDecode(r.body);
    }
    throw Exception('${r.statusCode} $path');
  }

  /// Run a live fetch; on any failure return [fallback] tagged SEED.
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

  Future<List<Brand>> brands() => _withSeed(
        () async => _asList(await _getJson('/api/brands')).map(Brand.fromJson).toList(),
        seedBrands,
      );

  Future<List<Alert>> alerts() => _withSeed(
        () async => _asList(await _getJson('/api/alerts')).map(Alert.fromJson).toList(),
        seedAlerts,
      );

  Future<List<Alert>> triageQueue() => _withSeed(
        () async {
          final all = _asList(await _getJson('/api/alerts')).map(Alert.fromJson).toList();
          return all.where((a) => a.verdict != Verdict.benign).toList();
        },
        seedAlerts.where((a) => a.verdict != Verdict.benign).toList(),
      );

  Future<Alert> alert(String id) => _withSeed(
        () async => Alert.fromJson(await _getJson('/api/alerts/$id') as Map<String, dynamic>),
        seedAlerts.firstWhere((a) => a.id == id, orElse: () => seedAlerts.first),
      );

  // Endpoints the backend doesn't expose yet -> always seed (tagged honestly).
  Future<List<Alert>> deepfakes() => _withSeed<List<Alert>>(
        () async => throw Exception('no /api/deepfakes endpoint'),
        seedDeepfakes,
      );

  Future<List<Cluster>> clusters() => _withSeed<List<Cluster>>(
        () async => throw Exception('no /api/clusters endpoint'),
        seedClusters,
      );

  Future<List<CostRow>> cost() => _withSeed<List<CostRow>>(
        () async => throw Exception('no /api/cost endpoint'),
        seedCost,
      );

  Future<List<AuditRow>> audit() => _withSeed(
        () async => _asList(await _getJson('/api/audit-log')).map(AuditRow.fromJson).toList(),
        seedAudit,
      );
}
