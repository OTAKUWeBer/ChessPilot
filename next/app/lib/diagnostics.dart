import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'native_client.dart';
import 'pilot_controller.dart';

void reportNativeError(String message) {
  try {
    NativeClient.discover().request({
      'command': 'report_error',
      'message': String.fromCharCodes(message.runes.take(16 * 1024)),
    });
  } catch (error) {
    debugPrint('Native diagnostics unavailable: $error');
  }
}

void installErrorReporting() {
  final previous = FlutterError.onError;
  FlutterError.onError = (details) {
    reportNativeError(
      'Flutter: ${details.exceptionAsString()}\n${details.stack ?? ''}',
    );
    previous?.call(details);
  };
  final previousPlatform = PlatformDispatcher.instance.onError;
  PlatformDispatcher.instance.onError = (error, stack) {
    reportNativeError('Dart: $error\n$stack');
    return previousPlatform?.call(error, stack) ?? false;
  };
}

class DiagnosticsDialog extends StatefulWidget {
  final PilotController controller;
  const DiagnosticsDialog({super.key, required this.controller});
  @override
  State<DiagnosticsDialog> createState() => _DiagnosticsDialogState();
}

class _DiagnosticsDialogState extends State<DiagnosticsDialog> {
  late Future<Map<String, dynamic>> details = widget.controller.diagnostics();
  String? error;
  bool opening = false;
  Future<void> open() async {
    setState(() {
      opening = true;
      error = null;
    });
    try {
      await widget.controller.openLogs();
    } catch (failure) {
      if (mounted) setState(() => error = '$failure');
    } finally {
      if (mounted) setState(() => opening = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Diagnostics'),
    content: SizedBox(
      width: 320,
      height: (MediaQuery.sizeOf(context).height * .45).clamp(120, 360),
      child: FutureBuilder<Map<String, dynamic>>(
        future: details,
        builder: (context, snapshot) {
          if (snapshot.hasError) return Text('${snapshot.error}');
          final info = snapshot.data;
          if (info == null) {
            return const Center(child: CircularProgressIndicator());
          }
          final system = info['system'] as Map;
          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${system['os']} · ${system['architecture']}\n${system['cpu_brand']}\n${system['cpu_cores']} logical CPUs',
                ),
                const SizedBox(height: 8),
                SelectableText(
                  info['log_path'] as String? ?? 'File logging unavailable',
                ),
                if (info['write_error'] != null)
                  Text(
                    info['write_error'] as String,
                    style: const TextStyle(color: Colors.orangeAccent),
                  ),
                if (info['dropped_records'] != 0)
                  Text(
                    'Log queue overflow: ${info['dropped_records']} file records omitted',
                  ),
                const SizedBox(height: 8),
                if (error != null)
                  Text(
                    error!,
                    style: const TextStyle(color: Colors.orangeAccent),
                  ),
                SelectableText(
                  info['tail'] as String? ?? '',
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
                ),
              ],
            ),
          );
        },
      ),
    ),
    actions: [
      TextButton(
        onPressed: opening ? null : open,
        child: Text(
          widget.controller.isAndroid
              ? 'Share recent logs'
              : 'Open logs folder',
        ),
      ),
      TextButton(
        onPressed: () => Navigator.of(context).pop(),
        child: const Text('Close'),
      ),
    ],
  );
}
