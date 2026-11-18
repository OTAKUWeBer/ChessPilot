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
      var platform = <String, dynamic>{
        'touch': false,
        'capture': false,
        'error': null,
      };
      messenger.setMockMethodCallHandler(AndroidPlatform.channel, (call) async {
        calls.add(call.method);
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
      final depthSlider = tester.widget<Slider>(find.byType(Slider));
      expect(depthSlider.min, 8);
      expect(depthSlider.max, 30);
      expect(depthSlider.divisions, 22);
      expect(find.text('Open accessibility settings'), findsOneWidget);
      expect(find.text('Share entire display'), findsNothing);
      expect(find.byTooltip('Shortcuts'), findsNothing);
      await tester.tap(find.byTooltip('Help and logs'));
      await tester.pumpAndSettle();
      expect(find.text('Keyboard shortcuts'), findsNothing);
      expect(find.textContaining('floating bubble'), findsOneWidget);
      expect(find.text('Diagnostics / logs'), findsOneWidget);
      await tester.tap(find.text('Close'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Open accessibility settings'));
      await tester.pump();
      platform = {
        'touch': true,
        'capture': false,
        'error': 'Accessibility service disconnected; restart capture',
      };
      await first.refreshPlatform();
      await tester.pump();
      expect(find.text('Setup needs attention'), findsNothing);
      expect(find.text('Touch control enabled'), findsOneWidget);
      expect(find.text('Share your board'), findsOneWidget);
      await tester.tap(find.text('Share entire display'));
      await tester.pump();
      expect(
        calls,
        containsAllInOrder(['connect', 'enableTouch', 'startCapture']),
      );
      first.configure({'color': 'w'});
      first.state!.addAll({
        'engine_ready': true,
        'capture_ready': true,
        'automation_ready': true,
      });
      first.notifyListeners();
      await tester.pump();
      expect(find.text('Play Next Move'), findsNothing);
      await tester.tap(find.text('Show floating controls'));
      await tester.pump();
      expect(calls, contains('showControls'));
      await tester.tap(find.byTooltip('Stop sharing and exit'));
      await tester.pump();
      expect(calls, contains('exit'));
      final statusCalls = calls.where((name) => name == 'status').length;
      await tester.pump(const Duration(seconds: 1));
      expect(calls.where((name) => name == 'status').length, statusCalls);
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
