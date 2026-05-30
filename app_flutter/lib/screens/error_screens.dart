// P20 — Not found (404) and P21 — Forbidden (403). Standard error screens.
// 403 appears when the current role lacks access to a surface; 404 for unknown
// routes. Both offer a route back to the dashboard.
import 'package:flutter/material.dart';
import '../theme.dart';

class _ErrorScaffold extends StatelessWidget {
  final String code;
  final String title;
  final String message;
  final IconData icon;
  final Color color;
  final Key listKey;
  const _ErrorScaffold({
    required this.code,
    required this.title,
    required this.message,
    required this.icon,
    required this.color,
    required this.listKey,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      key: listKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 56, color: color),
          const SizedBox(height: 16),
          Text(code,
              style: TextStyle(
                  color: color,
                  fontSize: 40,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'Georgia')),
          const SizedBox(height: 8),
          Text(title,
              style: const TextStyle(
                  color: SvColors.text,
                  fontSize: 18,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          SizedBox(
            width: 360,
            child: Text(message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: SvColors.muted, fontSize: 13)),
          ),
        ],
      ),
    );
  }
}

class NotFoundScreen extends StatelessWidget {
  const NotFoundScreen({super.key});
  @override
  Widget build(BuildContext context) => const _ErrorScaffold(
        code: '404',
        title: 'Page not found',
        message:
            'The page you were looking for does not exist or has moved. Use the navigation rail to find your way back.',
        icon: Icons.travel_explore_outlined,
        color: SvColors.cyan,
        listKey: Key('notfound-screen'),
      );
}

class ForbiddenScreen extends StatelessWidget {
  const ForbiddenScreen({super.key});
  @override
  Widget build(BuildContext context) => const _ErrorScaffold(
        code: '403',
        title: 'Access forbidden',
        message:
            'Your role does not have access to this surface. Contact an admin if you believe this is a mistake.',
        icon: Icons.lock_outline,
        color: SvColors.amber,
        listKey: Key('forbidden-screen'),
      );
}
