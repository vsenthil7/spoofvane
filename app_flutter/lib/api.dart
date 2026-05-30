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

  // Endpoints the backend doesn't expose yet -> always seed (tagged honestly).
  @override
  Future<List<Alert>> deepfakes() => _withSeed<List<Alert>>(
        () async => throw Exception('no /api/deepfakes endpoint'),
        seedDeepfakes,
      );

  @override
  Future<List<Cluster>> clusters() => _withSeed<List<Cluster>>(
        () async => throw Exception('no /api/clusters endpoint'),
        seedClusters,
      );

  @override
  Future<List<CostRow>> cost() => _withSeed<List<CostRow>>(
        () async => throw Exception('no /api/cost endpoint'),
        seedCost,
      );

  @override
  Future<List<AuditRow>> audit() => _withSeed(
        () async =>
            _asList(await _getJson('/api/audit-log')).map(AuditRow.fromJson).toList(),
        seedAudit,
      );
}
