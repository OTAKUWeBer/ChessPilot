import 'dart:convert';
import 'dart:ffi';
import 'dart:io';

typedef _AllocNative = Pointer<Uint8> Function(UintPtr);
typedef _Alloc = Pointer<Uint8> Function(int);
typedef _RequestNative = Pointer<Uint8> Function(Pointer<Uint8>, UintPtr);
typedef _Request = Pointer<Uint8> Function(Pointer<Uint8>, int);
typedef _FreeInputNative = Void Function(Pointer<Uint8>, UintPtr);
typedef _FreeInput = void Function(Pointer<Uint8>, int);
typedef _FreeResponseNative = Void Function(Pointer<Uint8>);
typedef _FreeResponse = void Function(Pointer<Uint8>);

/// Memory for both buffers is allocated/freed by the same Rust library.
class NativeClient {
  final String path;
  late final DynamicLibrary _library = DynamicLibrary.open(path);
  late final _Alloc _alloc = _library.lookupFunction<_AllocNative, _Alloc>(
    'chesspilot_alloc',
  );
  late final _Request _request = _library
      .lookupFunction<_RequestNative, _Request>('chesspilot_request');
  late final _FreeInput _freeInput = _library
      .lookupFunction<_FreeInputNative, _FreeInput>('chesspilot_free_input');
  late final _FreeResponse _freeResponse = _library
      .lookupFunction<_FreeResponseNative, _FreeResponse>(
        'chesspilot_free_response',
      );

  NativeClient(this.path);
  factory NativeClient.discover() {
    final override = Platform.environment['CHESSPILOT_LIBRARY_PATH'];
    if (override != null) return NativeClient(override);
    final name = Platform.isWindows
        ? 'chesspilot_runtime.dll'
        : 'libchesspilot_runtime.so';
    if (Platform.isAndroid) return NativeClient(name);
    final executableDirectory = File(Platform.resolvedExecutable).parent;
    for (final file in [
      File('${executableDirectory.path}/$name'),
      File('${executableDirectory.path}/lib/$name'),
      File('${Directory.current.path}/../native/target/debug/$name'),
    ]) {
      if (file.existsSync()) return NativeClient(file.absolute.path);
    }
    throw StateError(
      'ChessPilot native library is missing. Build the Rust runtime first.',
    );
  }

  Map<String, dynamic> request(Map<String, dynamic> command) {
    final bytes = utf8.encode(jsonEncode(command));
    final input = _alloc(bytes.length);
    if (input == nullptr) {
      throw StateError('Native request is too large or cannot be allocated');
    }
    Pointer<Uint8> response = nullptr;
    try {
      input.asTypedList(bytes.length).setAll(0, bytes);
      response = _request(input, bytes.length);
      if (response == nullptr) throw StateError('Native response is missing');
      final output = <int>[];
      for (var i = 0; ; i++) {
        if (i >= 1024 * 1024) {
          throw StateError('Native response exceeded its size limit');
        }
        final byte = (response + i).value;
        if (byte == 0) break;
        output.add(byte);
      }
      final envelope = jsonDecode(utf8.decode(output)) as Map<String, dynamic>;
      if (envelope['ok'] != true) {
        throw StateError(
          envelope['error'] as String? ?? 'Native operation failed',
        );
      }
      return envelope['result'] as Map<String, dynamic>;
    } finally {
      if (response != nullptr) _freeResponse(response);
      _freeInput(input, bytes.length);
    }
  }
}
