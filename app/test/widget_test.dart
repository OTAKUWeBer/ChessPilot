import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:ui' show AppExitResponse;
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chesspilot/main.dart';
import 'package:chesspilot/pilot_controller.dart';
import 'package:chesspilot/desktop_platform.dart';

class ActionController extends PilotController {
  int plays = 0;
  int logsOpened = 0;
  int captureRetries = 0;
  Map<String, dynamic>? playedWith;
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
    if (name == 'initialize_capture') {
      captureRetries++;
      return;
    }
    if (name == 'play') {
      playedWith = values;
      plays++;
      return;
    }
    if (name == 'set_auto') {
      final enabled = values['enabled'] as bool;
      autoRequests.add(enabled);
      state!.addAll({'auto_mode': enabled, 'busy': false});
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

class ClosingController extends ActionController {
  final pendingClose = Completer<void>();
  int closes = 0;
  @override
  Future<void> close() {
    closes++;
    return pendingClose.future;
  }

  Future<void> finishNativeClose() => super.close();
}

void main() {
  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(DesktopPlatform.channel, (_) async => null);
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(DesktopPlatform.channel, null);
  });
  testWidgets('game results offer New game and block Play and Auto shortcuts', (
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
    controller.configure({'color': 'w'});
    controller.setupAttempted = true;
    controller.presentCapabilities(busy: false, canAuto: true);
    controller.state!.addAll({
      'game_result': 'checkmate',
      'status': 'Checkmate!',
      'analysis': {'best_move': 'b6b7'},
    });
    await tester.pumpWidget(ChessPilotApp(controller: controller));
    expect(find.text('Checkmate!'), findsOneWidget);
    expect(find.textContaining('Move played: b6b7'), findsOneWidget);
    expect(find.text('Setup needs attention'), findsNothing);
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Play Next Move'),
          )
          .onPressed,
      isNull,
    );
    await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
    await tester.sendKeyEvent(LogicalKeyboardKey.keyA);
    expect(controller.plays, 0);
    expect(controller.autoRequests, isEmpty);
    controller.state!.addAll({'game_result': 'stalemate', 'analysis': null});
    controller.notifyListeners();
    await tester.pump();
    expect(find.text('Draw by stalemate'), findsOneWidget);
    await tester.ensureVisible(find.text('New game'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('New game'));
    expect(controller.state!['color'], isNull);
    controller.presentCapabilities(busy: false);
    await tester.pump();
    expect(find.text('Select Your Color:'), findsOneWidget);
    expect(controller.state!['game_result'], isNull);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets(
    'position errors stay in controls with readable details at large text size',
    (tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1;
      tester.platformDispatcher.textScaleFactorTestValue = 2;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      final controller = ActionController()
        ..initialize(initializeEngine: false);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      controller.configure({'color': 'w'});
      controller.setupAttempted = true;
      controller.presentCapabilities(busy: false, canAuto: true);
      controller.error =
          'Engine error: info string CRITICAL ERROR: Unsupported position. King can be captured.';
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      expect(find.text('Check the board position'), findsOneWidget);
      expect(find.text('Setup needs attention'), findsNothing);
      expect(find.text('Try again'), findsNothing);
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Play Next Move'),
            )
            .onPressed,
        isNotNull,
      );
      await tester.ensureVisible(find.text('Details'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Details'));
      await tester.pumpAndSettle();
      expect(find.text(controller.error!), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets(
    'phone can change color without a keyboard and preserves settings at large text size',
    (tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1;
      tester.platformDispatcher.textScaleFactorTestValue = 2;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      final controller = ActionController()
        ..initialize(initializeEngine: false);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      controller.configure({'depth': 19, 'delay': 0.7, 'mode': 'click'});
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      await tester.tap(find.text('White'));
      await tester.pump();
      expect(find.byTooltip('Change color'), findsOneWidget);
      await tester.tap(find.byTooltip('Change color'));
      await tester.pump();
      expect(controller.state!['color'], isNull);
      expect(controller.state!['depth'], 19);
      expect(controller.state!['delay'], 0.7);
      expect(controller.state!['mode'], 'click');
      expect(find.text('Select Your Color:'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets(
    'manual Play includes the native return target and ignores a stopped pending request',
    (tester) async {
      final controller = ActionController()
        ..initialize(initializeEngine: false);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      Completer<Map<String, dynamic>?>? pending;
      messenger.setMockMethodCallHandler(DesktopPlatform.channel, (call) async {
        if (call.method == 'setupWindow') return null;
        expect(call.method, 'returnTarget');
        expect((call.arguments as Map)['x'], isA<double>());
        if (pending != null) return await pending.future;
        return {'window': 123, 'x': 50, 'y': 60};
      });
      addTearDown(
        () => messenger.setMockMethodCallHandler(DesktopPlatform.channel, null),
      );
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      await tester.tap(find.text('White'));
      controller.presentCapabilities(busy: false);
      await tester.pump();
      await tester.tap(find.text('Play Next Move'));
      await tester.pump();
      expect(controller.plays, 1);
      expect(controller.playedWith?['return_target'], {
        'window': 123,
        'x': 50,
        'y': 60,
      });
      pending = Completer<Map<String, dynamic>?>();
      await tester.tap(find.text('Play Next Move'));
      await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
      controller.command('stop');
      pending.complete(null);
      await tester.pump();
      expect(
        controller.plays,
        1,
        reason: 'Stop must invalidate pending platform mapping',
      );
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets(
    'desktop exit waits for native shutdown before allowing termination',
    (tester) async {
      final controller = ClosingController()
        ..initialize(initializeEngine: false);
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      AppExitResponse? response;
      final exit = WidgetsBinding.instance.handleRequestAppExit().then((value) {
        response = value;
      });
      await tester.pump();
      expect(controller.closes, 1);
      expect(response, isNull);
      controller.pendingClose.complete();
      await exit;
      expect(response, AppExitResponse.exit);
      await tester.pumpWidget(const SizedBox());
      // Close the actual fixture session; the override above only delays the lifecycle callback.
      await tester.runAsync(controller.finishNativeClose);
      controller.dispose();
    },
  );
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
  testWidgets(
    'capture recovery stays available after its error is cleared and reuses the ready engine',
    (tester) async {
      final controller = ActionController()
        ..initialize(initializeEngine: false);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      controller.setupAttempted = true;
      controller.state!.addAll({'engine_ready': true, 'capture_ready': false});
      controller.error = 'Capture failed';
      await tester.pumpWidget(ChessPilotApp(controller: controller));
      expect(find.text('Capture failed'), findsOneWidget);
      controller.error = null;
      controller.notifyListeners();
      await tester.pump();
      expect(find.text('Preparing screen capture'), findsOneWidget);
      await tester.tap(find.text('Try again'));
      expect(controller.captureRetries, 1);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets('download progress exposes Cancel before choosing a color', (
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
    await tester.tap(find.widgetWithText(OutlinedButton, 'Cancel'));
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
    expect(find.text('Depth: 16'), findsOneWidget);
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
    expect(find.text('Depth: 16'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'Auto can start directly after color selection without a manual Play request',
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
      await tester.tap(find.text('White'));
      controller.presentCapabilities(busy: false, canAuto: true);
      await tester.pump();
      expect(controller.state!['confirmed_fen'], isNull);
      expect(
        find.byTooltip(
          'Start on your turn. Auto plays the first move, then waits for the opponent.',
        ),
        findsOneWidget,
      );
      await tester.tap(find.byType(CheckboxListTile).last);
      await tester.pump();
      expect(controller.autoRequests, [true]);
      expect(controller.plays, 0);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyA);
      await tester.pump();
      expect(controller.autoRequests, [true, false]);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
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
      await tester.pump();
      expect(controller.plays, 1);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyP);
      await tester.pump();
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
