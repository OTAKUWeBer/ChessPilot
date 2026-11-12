import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chesspilot/main.dart';
import 'package:chesspilot/pilot_controller.dart';

class ActionController extends PilotController {
  int plays = 0;
  int logsOpened = 0;
  @override
  Future<Map<String, dynamic>> diagnostics() async => {
    'system': {
      'os': 'fixture',
      'architecture': 'x86_64',
      'cpu_brand': 'Fixture CPU',
      'cpu_cores': 4,
    },
    'log_path': '/fixture/chesspilot-native.log',
    'write_error': null,
    'dropped_records': 0,
    'tail': 'Diagnostic fixture',
  };
  @override
  Future<void> openLogs() async {
    logsOpened++;
  }

  final List<bool> autoRequests = [];
  @override
  void command(String name, [Map<String, dynamic> values = const {}]) {
    if (name == 'play') {
      plays++;
      return;
    }
    if (name == 'set_auto') {
      final enabled = values['enabled'] as bool;
      autoRequests.add(enabled);
      state!.addAll({'auto_mode': enabled, 'busy': enabled});
      notifyListeners();
      return;
    }
    super.command(name, values);
  }

  void presentCapabilities({required bool busy, bool canAuto = false}) {
    state!.addAll({
      'engine_ready': true,
      'capture_ready': true,
      'automation_ready': true,
      'busy': busy,
      'auto_mode': false,
      'auto_available': canAuto,
    });
    notifyListeners();
  }
}

void main() {
  testWidgets(
    'diagnostics opens from help without launching the file manager in tests',
    (tester) async {
      tester.view.physicalSize = const Size(380, 520);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final controller = ActionController()
        ..initialize(initializeEngine: false);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      await tester.tap(find.byTooltip('Shortcuts'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Diagnostics / logs'));
      await tester.pumpAndSettle();
      expect(find.text('Diagnostic fixture'), findsOneWidget);
      await tester.tap(find.text('Open logs folder'));
      await tester.pumpAndSettle();
      expect(controller.logsOpened, 1);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets('download progress exposes Stop before choosing a color', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(380, 520);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final controller = ActionController()..initialize(initializeEngine: false);
    addTearDown(() async {
      await controller.close();
      controller.dispose();
    });
    controller.state!.addAll({
      'busy': true,
      'download': {
        'stage': 'Downloading Stockfish',
        'asset': 'fixture-avx2.zip',
        'cpu': 'Fixture CPU',
        'bytes_per_second': 2097152,
        'downloaded': 5000,
        'total': 10000,
      },
    });
    await tester.pumpWidget(ChessPilotApp(controller: controller));
    expect(find.text('Fixture CPU'), findsOneWidget);
    expect(find.text('2.0 MB/s'), findsOneWidget);
    expect(
      tester
          .widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator))
          .value,
      .5,
    );
    await tester.tap(find.widgetWithText(OutlinedButton, 'Stop'));
    await tester.pump();
    expect(controller.state!['busy'], false);
    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets('380x520 controls retain depth across color selection', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(380, 520);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final controller = PilotController()..initialize(initializeEngine: false);
    expect(controller.error, isNull);
    addTearDown(() async {
      await controller.close();
      controller.dispose();
    });
    await tester.pumpWidget(ChessPilotApp(controller: controller));
    expect(find.text('Select Your Color:'), findsOneWidget);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
    await tester.pump();
    expect(find.text('Stockfish Depth: 16'), findsOneWidget);
    await tester.tap(find.text('Black'));
    await tester.pump();
    expect(find.text('Playing as Black'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Play Next Move'),
          )
          .onPressed,
      isNull,
    );
    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pump();
    expect(find.text('Stockfish Depth: 16'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'Play dispatch and shortcuts respect native readiness and busy state',
    (tester) async {
      tester.view.physicalSize = const Size(380, 520);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final controller = ActionController()
        ..initialize(initializeEngine: false);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      await tester.sendKeyEvent(LogicalKeyboardKey.keyC);
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
      await tester.pump();
      expect(controller.state!['mode'], 'click');
      expect(controller.state!['delay'], 0.5);
      await tester.tap(find.text('White'));
      await tester.pump();
      await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
      expect(controller.plays, 0);
      controller.presentCapabilities(busy: false);
      await tester.pump();
      await tester.tap(find.text('Play Next Move'));
      expect(controller.plays, 1);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
      expect(controller.plays, 2);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyK);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyQ);
      expect(controller.state!['kingside'], true);
      expect(controller.state!['queenside'], true);
      controller.presentCapabilities(busy: false, canAuto: true);
      await tester.pump();
      await tester.sendKeyEvent(LogicalKeyboardKey.keyA);
      await tester.pump();
      expect(controller.state!['auto_mode'], true);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
      expect(controller.plays, 2);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyA);
      await tester.pump();
      expect(controller.autoRequests, [true, false]);
      expect(controller.state!['auto_mode'], false);
      controller.presentCapabilities(busy: true);
      await tester.pump();
      await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
      expect(controller.plays, 2);
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Play Next Move'),
            )
            .onPressed,
        isNull,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
