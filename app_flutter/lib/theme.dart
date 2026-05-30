// SpoofVane SOC palette + theme. Single source of truth for colours so screens
// and widgets never hard-code hex values.
import 'package:flutter/material.dart';

class SvColors {
  SvColors._();
  static const bg = Color(0xFF0B0F17);
  static const panel = Color(0xFF131A26);
  static const panel2 = Color(0xFF0E141F);
  static const border = Color(0xFF2C3A52);
  static const text = Color(0xFFE8EDF5);
  static const muted = Color(0xFF93A1B8);
  static const faint = Color(0xFF5E6E88);
  static const amber = Color(0xFFFFB020);
  static const cyan = Color(0xFF36C2CE);
  static const phish = Color(0xFFFF4D57);
  static const benign = Color(0xFF3DDC84);
  static const chipDanger = Color(0xFF2A1316);
  static const chip = Color(0xFF1B2433);
  static const node = Color(0xFF232F42);
}

ThemeData buildSvTheme() => ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: SvColors.bg,
      fontFamily: 'Roboto',
      colorScheme: const ColorScheme.dark(
        surface: SvColors.panel,
        primary: SvColors.cyan,
        secondary: SvColors.amber,
      ),
    );
