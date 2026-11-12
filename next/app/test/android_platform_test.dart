import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chesspilot/android_platform.dart';
import 'package:chesspilot/main.dart';
import 'package:chesspilot/native_client.dart';
import 'package:chesspilot/pilot_controller.dart';

void main() {
  testWidgets(
    'phone setup adopts one native session across Activity recreation',
    (tester) async {
      final client = NativeClient.discover();
      final id = client.request({'command': 'open'})['session'];
      final calls = <String>[];
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      messenger.setMockMethodCallHandler(AndroidPlatform.channel, (call) async {
        calls.add(call.method);
        final platform = {'touch': false, 'capture': false, 'error': null};
        if (call.method == 'connect') {
          return jsonEncode({
            'session': id,
            'state': client.request({
              'command': 'status',
              'session': id,
            })['state'],
            'resources': <String, dynamic>{},
            'platform': platform,
          });
        }
        if (call.method == 'status') return platform;
        return null;
      });
      addTearDown(() {
        messenger.setMockMethodCallHandler(AndroidPlatform.channel, null);
        client.request({'command': 'close', 'session': id});
      });
      tester.view.physicalSize = const Size(360, 700);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final first = PilotController(android: AndroidPlatform())
        ..initialize(initializeEngine: false);
      await tester.pump();
      expect(first.error, isNull);
      first.configure({'depth': 22});
      await tester.pumpWidget(ChessPilotApp(controller: first));
      expect(find.text('Enable touch control'), findsOneWidget);
      await tester.tap(find.text('Enable touch control'));
      await tester.pump();
      await tester.tap(find.text('Share entire display'));
      await tester.pump();
      expect(
        calls,
        containsAllInOrder(['connect', 'enableTouch', 'startCapture']),
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      await first.close();
      first.dispose();
      expect(
        (client.request({'command': 'status', 'session': id})['state']
            as Map)['depth'],
        22,
      );
      final second = PilotController(android: AndroidPlatform())
        ..initialize(initializeEngine: false);
      await tester.pump();
      expect(second.state!['depth'], 22);
      expect(second.error, isNull);
      second.dispose();
    },
  );
}
