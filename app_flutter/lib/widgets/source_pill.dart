// LIVE / SEED data-source indicator, bound to Api.instance.source.
import 'package:flutter/material.dart';
import '../api.dart';
import '../theme.dart';

class SourcePill extends StatelessWidget {
  const SourcePill({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<DataSource>(
      valueListenable: Api.instance.source,
      builder: (_, src, __) {
        final live = src == DataSource.live;
        final color = live ? SvColors.benign : SvColors.amber;
        return Semantics(
          label: live ? 'data source live' : 'data source seed',
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              live ? 'LIVE' : 'SEED',
              style: TextStyle(
                color: color,
                fontSize: 11,
                letterSpacing: 1,
                fontFamily: 'monospace',
              ),
            ),
          ),
        );
      },
    );
  }
}
