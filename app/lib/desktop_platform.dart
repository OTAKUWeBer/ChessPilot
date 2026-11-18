import 'package:flutter/services.dart';

class DesktopPlatform {
  static const channel = MethodChannel('chesspilot/desktop');
  static Future<void> setupWindow(bool enabled, {required int height}) async {
    try {
      await channel.invokeMethod<void>('setupWindow', {
        'enabled': enabled,
        'height': height,
      });
    } on MissingPluginException {
      // Non-desktop frontends keep their normal screen size.
    }
  }

  static Future<Map<String, dynamic>?> returnTarget(Offset point) async {
    try {
      final value = await channel
          .invokeMapMethod<String, dynamic>('returnTarget', {
            'x': point.dx,
            'y': point.dy,
          })
          .timeout(const Duration(milliseconds: 500), onTimeout: () => null);
      return value;
    } on MissingPluginException {
      return null;
    }
  }
}
