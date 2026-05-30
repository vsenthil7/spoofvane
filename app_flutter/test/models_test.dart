import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/models.dart';

void main() {
  test('Brand.fromJson handles camelCase and snake_case', () {
    final a = Brand.fromJson({'id': 'b1', 'name': 'X', 'loginUrl': 'u', 'targetCountry': 'US', 'scoreThreshold': 0.7});
    expect(a.scoreThreshold, 0.7);
    final b = Brand.fromJson({'brand_id': 'b2', 'name': 'Y', 'login_url': 'u2', 'target_country': 'GB', 'score_threshold': 0.6});
    expect(b.id, 'b2');
    expect(b.targetCountry, 'GB');
  });

  test('Alert.fromJson handles both key styles + missing fields', () {
    final a = Alert.fromJson({'id': 'a1', 'brandId': 'b1', 'url': 'u', 'verdict': 'phish', 'composite': 0.9});
    expect(a.verdict, Verdict.phish);
    expect(a.mitreTechniques, isEmpty);
    final b = Alert.fromJson({'id': 'a2', 'brand_id': 'b2', 'url': 'u2', 'verdict': 'benign', 'composite_score': 0.1, 'mitre_techniques': ['T1']});
    expect(b.composite, 0.1);
    expect(b.mitreTechniques, ['T1']);
  });

  test('Cluster + CostRow + AuditRow parse', () {
    expect(Cluster.fromJson({'id': 1, 'members': ['x'], 'risk': 0.5}).members, ['x']);
    expect(CostRow.fromJson({'product': 'serp', 'usd': 4.2}).usd, 4.2);
    expect(AuditRow.fromJson({'seq': 1, 'actor_role': 'analyst', 'action': 'a', 'outcome': 'ok', 'ts': 't', 'hash': 'h'}).actorRole, 'analyst');
  });
}
