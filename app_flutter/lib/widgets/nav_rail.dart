// Collapsible left navigation rail (presentation only — selection state is
// owned by the parent Console). The rail width animates between expanded and
// collapsed; content is clipped to the rail bounds so it never paints outside
// during the transition.
import 'package:flutter/material.dart';
import '../theme.dart';

class NavEntry {
  final String label;
  final IconData icon;
  const NavEntry(this.label, this.icon);
}

const double kRailExpanded = 232;
const double kRailCollapsed = 64;

class NavRail extends StatelessWidget {
  final List<NavEntry> items;
  final int selected;
  final bool collapsed;
  final ValueChanged<int> onSelect;
  final VoidCallback onToggle;

  const NavRail({
    super.key,
    required this.items,
    required this.selected,
    required this.collapsed,
    required this.onSelect,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      width: collapsed ? kRailCollapsed : kRailExpanded,
      clipBehavior: Clip.hardEdge,
      decoration: const BoxDecoration(color: SvColors.panel),
      // Pin the inner content to the EXPANDED width and align left, so the row
      // children always lay out at a stable width and are simply clipped as the
      // outer width animates — no RenderFlex overflow at intermediate widths.
      child: OverflowBox(
        alignment: Alignment.topLeft,
        minWidth: kRailExpanded,
        maxWidth: kRailExpanded,
        child: SizedBox(
          width: kRailExpanded,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _header(),
              const SizedBox(height: 8),
              Expanded(
                child: ListView.builder(
                  itemCount: items.length,
                  itemBuilder: (_, i) => _navTile(i),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header() {
    return Container(
      height: 56,
      color: SvColors.panel2,
      padding: EdgeInsets.symmetric(horizontal: collapsed ? 8 : 16),
      child: Row(
        children: [
          if (!collapsed) const Expanded(child: _BrandMark()),
          IconButton(
            tooltip: collapsed ? 'Expand' : 'Collapse',
            icon: Icon(collapsed ? Icons.chevron_right : Icons.chevron_left,
                color: SvColors.muted, size: 18),
            onPressed: onToggle,
          ),
        ],
      ),
    );
  }

  Widget _navTile(int i) {
    final n = items[i];
    final sel = i == selected;
    return InkWell(
      onTap: () => onSelect(i),
      child: Semantics(
        button: true,
        selected: sel,
        label: n.label,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: sel ? SvColors.cyan.withOpacity(0.13) : null,
            borderRadius: BorderRadius.circular(6),
            border: sel ? Border.all(color: SvColors.cyan.withOpacity(0.4)) : null,
          ),
          child: Row(
            mainAxisAlignment:
                collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
            children: [
              Icon(n.icon, size: 18, color: sel ? SvColors.cyan : SvColors.faint),
              if (!collapsed) ...[
                const SizedBox(width: 10),
                Expanded(
                  child: Text(n.label,
                      softWrap: false,
                      overflow: TextOverflow.clip,
                      style: TextStyle(
                          color: sel ? SvColors.text : SvColors.muted,
                          fontSize: 13)),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        RichText(
          text: const TextSpan(children: [
            TextSpan(
                text: 'Spoof',
                style: TextStyle(
                    color: SvColors.text,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    fontFamily: 'Georgia')),
            TextSpan(
                text: 'Vane',
                style: TextStyle(
                    color: SvColors.amber,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    fontFamily: 'Georgia')),
          ]),
        ),
        const Text('v0.5 Enterprise',
            style: TextStyle(color: SvColors.faint, fontSize: 9)),
      ],
    );
  }
}
