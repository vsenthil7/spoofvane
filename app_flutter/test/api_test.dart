// Exercises the real HttpApiClient without a live backend, using http's
// MockClient. Covers: live-success parsing, fallback-to-seed on HTTP error,
// the list-shape variants (_asList), health(), and the always-seed endpoints.
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/models.dart';

HttpApiClient clientReturning(Map<String, dynamic Function()> routes,
    {String base = 'http://test'}) {
  final mock = MockClient((req) async {
    final path = req.url.path + (req.url.hasQuery ? '?${req.url.query}' : '');
    for (final entry in routes.entries) {
      if (path.startsWith(entry.key)) {
        return http.Response(jsonEncode(entry.value()), 200);
      }
    }
    return http.Response('not found', 404);
  });
  return HttpApiClient(client: mock, base: base);
}

void main() {
  test('brands(): live success parses + tags LIVE', () async {
    final api = clientReturning({
      '/api/brands': () => [
            {'id': 'b1', 'name': 'AcmeBank', 'loginUrl': 'u', 'targetCountry': 'US', 'scoreThreshold': 0.65}
          ],
    });
    final brands = await api.brands();
    expect(brands.single.name, 'AcmeBank');
    expect(api.source.value, DataSource.live);
  });

  test('alerts(): HTTP 404 falls back to seed + tags SEED', () async {
    final api = clientReturning({}); // every route 404s
    final alerts = await api.alerts();
    expect(alerts, isNotEmpty); // seed data
    expect(api.source.value, DataSource.seed);
  });

  test('triageQueue(): filters benign from live payload', () async {
    final api = clientReturning({
      '/api/alerts': () => [
            {'id': 'p', 'brandId': 'b', 'url': 'u1', 'verdict': 'phish', 'composite': 0.9},
            {'id': 'n', 'brandId': 'b', 'url': 'u2', 'verdict': 'benign', 'composite': 0.1},
          ],
    });
    final q = await api.triageQueue();
    expect(q.length, 1);
    expect(q.single.verdict, Verdict.phish);
  });

  test('_asList accepts {items:[...]} and {alerts:[...]} envelopes', () async {
    final itemsApi = clientReturning({
      '/api/brands': () => {
            'items': [
              {'id': 'b1', 'name': 'X', 'loginUrl': 'u', 'targetCountry': 'US', 'scoreThreshold': 0.6}
            ]
          },
    });
    expect((await itemsApi.brands()).single.id, 'b1');

    final alertsApi = clientReturning({
      '/api/alerts': () => {
            'alerts': [
              {'id': 'a1', 'brandId': 'b', 'url': 'u', 'verdict': 'phish', 'composite': 0.9}
            ]
          },
    });
    expect((await alertsApi.alerts()).single.id, 'a1');
  });

  test('alert(id): live single-object parse', () async {
    final api = clientReturning({
      '/api/alerts/a1': () =>
          {'id': 'a1', 'brandId': 'b', 'url': 'u', 'verdict': 'suspicious', 'composite': 0.6},
    });
    expect((await api.alert('a1')).verdict, Verdict.suspicious);
  });

  test('audit(): live parse', () async {
    final api = clientReturning({
      '/api/audit-log': () => [
            {'seq': 1, 'actor_role': 'analyst', 'action': 'x', 'outcome': 'ok', 'ts': 't', 'hash': 'h'}
          ],
    });
    expect((await api.audit()).single.action, 'x');
  });

  test('health(): true on 200, false on error', () async {
    final up = clientReturning({'/healthz': () => {'ok': true}});
    expect(await up.health(), true);
    expect(up.source.value, DataSource.live);

    final down = clientReturning({});
    expect(await down.health(), false);
    expect(down.source.value, DataSource.seed);
  });

  test('always-seed endpoints return seed + tag SEED', () async {
    final api = clientReturning({});
    expect(await api.deepfakes(), isNotEmpty);
    expect(await api.clusters(), isNotEmpty);
    expect(await api.cost(), isNotEmpty);
    expect(api.source.value, DataSource.seed);
  });
}
