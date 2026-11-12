import 'dart:async';
import 'dart:isolate';
import 'package:flutter/foundation.dart';
import 'native_client.dart';

/// The snapshot is presentation data; Rust owns all settings and session state.
class PilotController extends ChangeNotifier {
  NativeClient? _client;
  int? _session;
  Timer? _timer;
  Map<String, dynamic>? state;
  String? error;
  bool _disposed = false;

  void initialize({bool initializeEngine = true, NativeClient? client}) {
    if (_disposed || _session != null) return;
    try {
      _client = client ?? NativeClient.discover();
      final result = _client!.request({'command': 'open'});
      _session = result['session'] as int;
      state = result['state'] as Map<String, dynamic>;
      if (initializeEngine) command('initialize_engine');
    } catch (e) {
      error = '$e';
    }
    notifyListeners();
  }

  void configure(Map<String, dynamic> values) => command('configure', values);
  void command(String name, [Map<String, dynamic> values = const {}]) {
    if (_disposed || _session == null) return;
    try {
      final result = _client!.request({
        ...values,
        'command': name,
        'session': _session,
      });
      state = result['state'] as Map<String, dynamic>;
      error = state!['error'] as String?;
      if (state!['busy'] == true && _timer == null) {
        _timer = Timer.periodic(
          const Duration(milliseconds: 100),
          (_) => command('status'),
        );
      } else if (state!['busy'] != true) {
        _timer?.cancel();
        _timer = null;
      }
    } catch (e) {
      error = '$e';
      _timer?.cancel();
      _timer = null;
    }
    notifyListeners();
  }

  Future<void> close() async {
    _timer?.cancel();
    _timer = null;
    final session = _session;
    final path = _client?.path;
    _session = null;
    if (session != null && path != null) {
      await Isolate.run(() {
        NativeClient(path).request({'command': 'close', 'session': session});
      });
    }
  }

  @override
  void dispose() {
    _disposed = true;
    unawaited(
      close().catchError((Object error, StackTrace stack) {
        FlutterError.reportError(
          FlutterErrorDetails(
            exception: error,
            stack: stack,
            context: ErrorDescription('closing the native session'),
          ),
        );
      }),
    );
    super.dispose();
  }
}
