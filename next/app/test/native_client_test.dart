import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:chesspilot/native_client.dart';

void main() {
  test('Dart communicates with compiled Rust and owns no settings', () {
    final client = NativeClient.discover();
    final opened = client.request({'command': 'open'});
    final id = opened['session'];
    try {
      expect((opened['state'] as Map)['depth'], 15);
      final changed = client.request({
        'command': 'configure',
        'session': id,
        'depth': 23,
        'color': 'b',
        'mode': 'click',
      });
      expect((changed['state'] as Map)['depth'], 23);
      expect((changed['state'] as Map)['color'], 'b');
      expect(
        () => client.request({
          'command': 'configure',
          'session': id,
          'depth': 99,
        }),
        throwsStateError,
      );
      for (var i = 0; i < 200; i++) {
        expect(
          (client.request({'command': 'status', 'session': id})['state']
              as Map)['depth'],
          23,
        );
      }
    } finally {
      client.request({'command': 'close', 'session': id});
    }
    expect(
      () => client.request({'command': 'status', 'session': id}),
      throwsStateError,
    );
  });

  test(
    'Dart -> Rust worker -> real Stockfish returns updated FEN',
    () async {
      final client = NativeClient.discover();
      final id = client.request({'command': 'open'})['session'];
      Future<Map> waitIdle() async {
        final deadline = DateTime.now().add(const Duration(seconds: 20));
        while (true) {
          final state =
              client.request({'command': 'status', 'session': id})['state']
                  as Map;
          if (state['busy'] == false) return state;
          if (DateTime.now().isAfter(deadline)) {
            fail('Native operation timed out');
          }
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
      }

      try {
        client.request({
          'command': 'initialize_engine',
          'session': id,
          'engine_path': Platform.environment['CHESSPILOT_STOCKFISH'],
        });
        expect((await waitIdle())['engine_ready'], true);
        client.request({'command': 'configure', 'session': id, 'depth': 10});
        client.request({
          'command': 'analyze',
          'session': id,
          'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        });
        final result = await waitIdle();
        expect((result['analysis'] as Map)['best_move'], isA<String>());
        expect((result['analysis'] as Map)['updated_fen'], contains(' b '));
      } finally {
        client.request({'command': 'close', 'session': id});
      }
    },
    skip: Platform.environment['CHESSPILOT_STOCKFISH'] == null
        ? 'Set CHESSPILOT_STOCKFISH for native engine integration'
        : false,
  );
}
