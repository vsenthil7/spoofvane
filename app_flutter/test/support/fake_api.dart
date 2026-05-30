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
}
