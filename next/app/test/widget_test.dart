import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chesspilot/main.dart';

void main() {
  testWidgets('380x520 controls retain depth across color selection', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(380, 520);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const ChessPilotApp());
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
}
