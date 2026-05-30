// Role model for the console — mirrors the 6-role SoD model in the canonical
// spec (docs/USER_GUIDE.md §2). A page is visible iff the current role's rank is
// >= the page's minRole rank.
enum Role { viewer, auditor, reviewer, analyst, admin, owner }

/// Privilege rank, least (0) to most (5). Higher rank sees everything a lower
/// rank sees.
int roleRank(Role r) {
  switch (r) {
    case Role.viewer:
      return 0;
    case Role.auditor:
      return 1;
    case Role.reviewer:
      return 2;
    case Role.analyst:
      return 3;
    case Role.admin:
      return 4;
    case Role.owner:
      return 5;
  }
}

Role roleFromString(String s) {
  switch (s.toLowerCase()) {
    case 'auditor':
      return Role.auditor;
    case 'reviewer':
      return Role.reviewer;
    case 'analyst':
      return Role.analyst;
    case 'admin':
      return Role.admin;
    case 'owner':
      return Role.owner;
    case 'viewer':
    default:
      return Role.viewer;
  }
}

String roleLabel(Role r) => r.name[0].toUpperCase() + r.name.substring(1);

/// True if [role] is allowed to see something requiring at least [minRole].
bool roleAllows(Role role, Role minRole) => roleRank(role) >= roleRank(minRole);
