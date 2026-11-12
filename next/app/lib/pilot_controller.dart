import 'dart:async';
import 'dart:isolate';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'android_platform.dart';
import 'native_client.dart';

/// The snapshot is presentation data; Rust owns all settings and session state.
class PilotController extends ChangeNotifier {
  final AndroidPlatform? android;
  PilotController({AndroidPlatform? android})
    : android = android ?? (Platform.isAndroid ? AndroidPlatform() : null);
  bool get isAndroid => android != null;
  Map<String, dynamic>? platformState;
  Map<String, dynamic> _resources = {};
  bool _connecting = false;
  bool _refreshingPlatform = false;
  bool _captureAttempted = false;
  NativeClient? _client;
  int? _session;
  Timer? _timer;
  Map<String, dynamic>? state;
  String? error;
  bool _disposed = false;

  void initialize({bool initializeEngine = true, NativeClient? client}) {
    if (_disposed || _session != null || _connecting) return;
    if (android != null) {
      unawaited(_initializeAndroid(initializeEngine, client));
      return;
    }
    try {
      _client = client ?? NativeClient.discover();
      final result = _client!.request({'command': 'open'});
      _session = result['session'] as int;
      state = result['state'] as Map<String, dynamic>;
      if (initializeEngine) command('initialize');
    } catch (e) {
      error = '$e';
    }
    notifyListeners();
  }

  Future<void> _initializeAndroid(
    bool initializeEngine,
    NativeClient? client,
  ) async {
    _connecting = true;
    try {
      final connected = await android!.connect();
      if (_disposed) return;
      _client = client ?? NativeClient.discover();
      _session = connected['session'] as int;
      state = connected['state'] as Map<String, dynamic>;
      _resources = connected['resources'] as Map<String, dynamic>;
      platformState = connected['platform'] as Map<String, dynamic>;
      if (initializeEngine &&
          state!['engine_ready'] != true &&
          state!['busy'] != true) {
        command('initialize_engine');
      }
      _timer ??= Timer.periodic(const Duration(milliseconds: 500), (_) {
        command('status');
        unawaited(refreshPlatform());
      });
    } catch (e) {
      if (!_disposed) error = '$e';
    } finally {
      _connecting = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> refreshPlatform() async {
    if (_disposed || android == null || _refreshingPlatform) return;
    _refreshingPlatform = true;
    try {
      final next = await android!.status();
      if (_disposed) return;
      platformState = next;
      if (next['capture'] != true) _captureAttempted = false;
      if (next['capture'] == true &&
          next['touch'] == true &&
          !_captureAttempted &&
          state?['engine_ready'] == true &&
          state?['capture_ready'] != true &&
          state?['busy'] != true) {
        _captureAttempted = true;
        command('initialize_capture');
      }
    } catch (e) {
      if (!_disposed) error = '$e';
    } finally {
      _refreshingPlatform = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> platformAction(String name) async {
    try {
      await android!.action(name);
      if (!_disposed) await refreshPlatform();
    } catch (e) {
      if (!_disposed) {
        error = '$e';
        notifyListeners();
      }
    }
  }

  void configure(Map<String, dynamic> values) => command('configure', values);
  Future<Map<String, dynamic>> diagnostics() async {
    final path = _client?.path ?? NativeClient.discover().path;
    return Isolate.run(
      () => NativeClient(
        path,
      ).request({'command': 'diagnostics', 'include_tail': true}),
    );
  }

  Future<void> openLogs() async {
    if (android != null) {
      await android!.action('shareLogs');
      return;
    }
    final path = _client?.path ?? NativeClient.discover().path;
    await Isolate.run(
      () => NativeClient(path).request({'command': 'open_log_folder'}),
    );
  }

  void command(String name, [Map<String, dynamic> values = const {}]) {
    if (_disposed || _session == null) return;
    try {
      final result = _client!.request({
        if (name.startsWith('initialize')) ..._resources,
        ...values,
        'command': name,
        'session': _session,
      });
      state = result['state'] as Map<String, dynamic>;
      error = state!['error'] as String?;
      if (state!['busy'] == true && _timer == null) {
        _timer = Timer.periodic(Duration(milliseconds: isAndroid ? 500 : 100), (
          _,
        ) {
          command('status');
          if (isAndroid) unawaited(refreshPlatform());
        });
      } else if (state!['busy'] != true && android == null) {
        _timer?.cancel();
        _timer = null;
      }
    } catch (e) {
      error = '$e';
      if (!isAndroid) {
        _timer?.cancel();
        _timer = null;
      }
    }
    notifyListeners();
  }

  Future<void> close() async {
    _timer?.cancel();
    _timer = null;
    final session = _session;
    final path = _client?.path;
    _session = null;
    // The Android service owns the session while the Activity is backgrounded/recreated.
    if (android != null) return;
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
