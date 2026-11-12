import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chesspilot/main.dart';
import 'package:chesspilot/pilot_controller.dart';

class ActionController extends PilotController {
  int plays = 0;
  @override
  void command(String name, [Map<String, dynamic> values = const {}]) {
    if (name == 'play') {
      plays++;
      return;
    }
    super.command(name, values);
  }

  void presentCapabilities({required bool busy}) {
    state!.addAll({
      'engine_ready': true,
      'capture_ready': true,
      'automation_ready': true,
      'busy': busy,
    });
    notifyListeners();
  }
}

void main() {
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
