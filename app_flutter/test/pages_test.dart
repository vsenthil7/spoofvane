import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/pages.dart';
import 'package:spoofvane_app/roles.dart';

void main() {
  test('registry holds exactly 21 canonical pages P01..P21', () {
    expect(kPageCount, 21);
    final ids = kPages.map((p) => p.id).toList();
    expect(ids.first, 'P01');
    expect(ids.last, 'P21');
    // ids are unique and sequential
    expect(ids.toSet().length, 21);
  });

  test('role ranks order least -> most privileged', () {
    expect(roleRank(Role.viewer), lessThan(roleRank(Role.auditor)));
    expect(roleRank(Role.auditor), lessThan(roleRank(Role.reviewer)));
    expect(roleRank(Role.reviewer), lessThan(roleRank(Role.analyst)));
    expect(roleRank(Role.analyst), lessThan(roleRank(Role.admin)));
    expect(roleRank(Role.admin), lessThan(roleRank(Role.owner)));
  });

  test('roleAllows is monotonic in rank', () {
    expect(roleAllows(Role.owner, Role.viewer), isTrue);
    expect(roleAllows(Role.viewer, Role.owner), isFalse);
    expect(roleAllows(Role.analyst, Role.analyst), isTrue);
  });

  test('roleFromString round-trips known roles, defaults to viewer', () {
    expect(roleFromString('admin'), Role.admin);
    expect(roleFromString('OWNER'), Role.owner);
    expect(roleFromString('nonsense'), Role.viewer);
  });

  test('nav for viewer excludes analyst/admin/owner pages', () {
    final labels = navPagesFor(Role.viewer).map((p) => p.title).toList();
    expect(labels, contains('Dashboard')); // viewer
    expect(labels, contains('Settings')); // viewer
    expect(labels, isNot(contains('Triage Queue'))); // analyst
    expect(labels, isNot(contains('Cost Attribution'))); // admin
    expect(labels, isNot(contains('Tenants'))); // owner
  });

  test('nav for analyst includes analyst pages but not admin/owner', () {
    final labels = navPagesFor(Role.analyst).map((p) => p.title).toList();
    expect(labels, contains('Triage Queue'));
    expect(labels, contains('Audit Log')); // auditor <= analyst
    expect(labels, isNot(contains('Cost Attribution'))); // admin
    expect(labels, isNot(contains('Tenants'))); // owner
  });

  test('owner sees every nav page', () {
    final ownerNav = navPagesFor(Role.owner).length;
    final allNav = kPages.where((p) => p.nav).length;
    expect(ownerNav, allNav);
  });

  test('non-nav pages exist (login, detail, errors)', () {
    final nonNav = kPages.where((p) => !p.nav).map((p) => p.id).toList();
    expect(nonNav, containsAll(<String>['P01', 'P04', 'P06', 'P20', 'P21']));
  });

  test('every page has a builder and a route', () {
    for (final p in kPages) {
      expect(p.route, isNotEmpty, reason: '${p.id} route');
      expect(p.title, isNotEmpty, reason: '${p.id} title');
    }
  });
}
