import 'dart:async';
import 'dart:ffi';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:chesspilot/desktop_platform.dart';
import 'package:chesspilot/main.dart';
import 'package:chesspilot/native_client.dart';
import 'package:chesspilot/pilot_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

class RecordingClient extends NativeClient {
  RecordingClient(super.path);
  int? session;
  @override
  Map<String, dynamic> request(Map<String, dynamic> command) {
    final result = super.request(command);
    if (command['command'] == 'open') session = result['session'] as int;
    return result;
  }
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'real Windows window starts, renders, maps Play and awaits engine exit',
    (tester) async {
      final output = Directory(
        Platform.environment['CHESSPILOT_UI_TEST_OUTPUT']!,
      );
      await output.create(recursive: true);
      final config = File('${output.path}/engine_config.txt');
      await config.writeAsString(
        'setoption name Hash value 16\nsetoption name Threads value 1\n',
      );
      final client = RecordingClient(NativeClient.discover().path);
      expect(
        File(client.path).parent.path,
        File(Platform.resolvedExecutable).parent.path,
        reason: 'The real runner must load its bundled Rust library',
      );
      final controller = PilotController()
        ..initialize(initializeEngine: false, client: client);
      addTearDown(() async {
        await controller.close();
        controller.dispose();
      });
      final boundary = GlobalKey();
      await tester.pumpWidget(
        RepaintBoundary(
          key: boundary,
          child: ChessPilotApp(controller: controller),
        ),
      );
      await tester.pumpAndSettle();

      Future<void> screenshot(String name, {bool settle = true}) async {
        if (settle) await tester.pumpAndSettle();
        final image =
            await (boundary.currentContext!.findRenderObject()
                    as RenderRepaintBoundary)
                .toImage(pixelRatio: tester.view.devicePixelRatio);
        try {
          final png = await image.toByteData(format: ui.ImageByteFormat.png);
          await File(
            '${output.path}/$name.png',
          ).writeAsBytes(png!.buffer.asUint8List());
        } finally {
          image.dispose();
        }
      }

      expect(find.text('Select Your Color:'), findsOneWidget);
      final size = tester.view.physicalSize / tester.view.devicePixelRatio;
      expect(size.width, greaterThanOrEqualTo(379));
      expect(size.height, greaterThanOrEqualTo(519));
      expect(size.width / size.height, closeTo(380 / 520, 0.01));

      // Exercise the full progress layout even on a warm launch with a cached engine.
      controller.setupAttempted = true;
      controller.state!.addAll({
        'busy': true,
        'download': {
          'stage': 'Downloading Stockfish',
          'cpu': 'Compatible CPU build selected',
          'total': 80000000,
          'downloaded': 40000000,
          'bytes_per_second': 8000000,
        },
      });
      await tester.pumpWidget(
        RepaintBoundary(
          key: boundary,
          child: ChessPilotApp(controller: controller),
        ),
      );
      await screenshot('downloader');
      final compact = tester.view.physicalSize / tester.view.devicePixelRatio;
      expect(compact.width, closeTo(420, 1));
      expect(compact.height, lessThan(280));
      expect(
        (compact.height - tester.getSize(find.byType(Card)).height).abs(),
        lessThan(2),
      );
      expect(find.text('Select Your Color:'), findsNothing);

      controller.command('initialize', {'config_path': config.absolute.path});
      final deadline = DateTime.now().add(const Duration(seconds: 90));
      var capturedSetup = false;
      while (controller.state!['busy'] == true) {
        expect(
          DateTime.now().isBefore(deadline),
          isTrue,
          reason: '${controller.state}',
        );
        await tester.pump(const Duration(milliseconds: 100));
        if (!capturedSetup &&
            controller.state!['download'] is Map &&
            controller.state!['engine_ready'] != true) {
          expect(find.text('Select Your Color:'), findsNothing);
          await screenshot('setup', settle: false);
          capturedSetup = true;
        }
      }
      expect(controller.error, isNull);
      expect(controller.state!['engine_ready'], isTrue);
      expect(controller.state!['capture_ready'], isTrue);
      expect(
        File(
          '${File(Platform.resolvedExecutable).parent.path}/stockfish.exe',
        ).existsSync(),
        isTrue,
      );
      expect(find.text('Retry engine'), findsNothing);
      await screenshot('color-selection');
      expect(tester.view.physicalSize / tester.view.devicePixelRatio, size);
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyC);
      await tester.pump();
      await tester.tap(find.text('White'));
      await tester.pumpAndSettle();
      expect(controller.state!['depth'], 16);
      expect(controller.state!['delay'], 0.5);
      expect(controller.state!['mode'], 'click');
      expect(controller.state!['auto_available'], isTrue);
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Play Next Move'),
            )
            .onPressed,
        isNotNull,
      );
      await screenshot('play-controls');

      final button = tester.getCenter(
        find.widgetWithText(FilledButton, 'Play Next Move'),
      );
      final target = await DesktopPlatform.returnTarget(button);
      expect(target, isNotNull);
      expect(target!['x'], greaterThanOrEqualTo(0));
      expect(target['y'], greaterThanOrEqualTo(0));
      final user32 = DynamicLibrary.open('user32.dll');
      final rootWindow = user32
          .lookupFunction<
            Pointer<Void> Function(Pointer<Void>, Uint32),
            Pointer<Void> Function(Pointer<Void>, int)
          >(
            'GetAncestor',
          )(Pointer<Void>.fromAddress(target['window'] as int), 2);
      final style = user32
          .lookupFunction<
            IntPtr Function(Pointer<Void>, Int32),
            int Function(Pointer<Void>, int)
          >('GetWindowLongPtrW')(rootWindow, -20);
      expect(style & 8, 8, reason: 'The actual native window must stay on top');

      await tester.tap(find.byTooltip('Shortcuts'));
      await tester.pumpAndSettle();
      await screenshot('shortcuts');
      await tester.tap(find.text('Close'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Change color'));
      await tester.pumpAndSettle();
      expect(controller.state!['color'], isNull);
      expect(controller.state!['depth'], 16);
      await tester.tap(find.text('Black'));
      await tester.pumpAndSettle();
      expect(controller.state!['color'], 'b');

      final diagnostics = await controller.diagnostics();
      final pid = int.parse(
        RegExp(
          r'Stockfish started \(PID (\d+)\)',
        ).firstMatch(diagnostics['tail'] as String)!.group(1)!,
      );
      final kernel32 = DynamicLibrary.open('kernel32.dll');
      final process = kernel32
          .lookupFunction<
            Pointer<Void> Function(Uint32, Int32, Uint32),
            Pointer<Void> Function(int, int, int)
          >('OpenProcess')(0x100000, 0, pid);
      expect(process, isNot(nullptr));
      final closeHandle = kernel32
          .lookupFunction<
            Int32 Function(Pointer<Void>),
            int Function(Pointer<Void>)
          >('CloseHandle');
      addTearDown(() => closeHandle(process));
      final waitProcess = kernel32
          .lookupFunction<
            Uint32 Function(Pointer<Void>, Uint32),
            int Function(Pointer<Void>, int)
          >('WaitForSingleObject');
      expect(
        waitProcess(process, 0),
        258,
        reason: 'The app must own a live Stockfish child',
      );
      final exitRequested = Completer<void>();
      // Keep the test connection alive after the real application has awaited cleanup.
      final keepTestAlive = AppLifecycleListener(
        onExitRequested: () async {
          exitRequested.complete();
          return ui.AppExitResponse.cancel;
        },
      );
      addTearDown(keepTestAlive.dispose);
      expect(
        user32.lookupFunction<
          Int32 Function(Pointer<Void>, Uint32, UintPtr, IntPtr),
          int Function(Pointer<Void>, int, int, int)
        >('PostMessageW')(rootWindow, 0x10, 0, 0),
        isNot(0),
      );
      final exitDeadline = DateTime.now().add(const Duration(seconds: 10));
      while (!exitRequested.isCompleted) {
        expect(
          DateTime.now().isBefore(exitDeadline),
          isTrue,
          reason: 'WM_CLOSE did not reach the lifecycle handler',
        );
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(
        waitProcess(process, 0),
        0,
        reason: 'The engine must exit before the app accepts close',
      );
      expect(
        () => client.request({'command': 'status', 'session': client.session}),
        throwsStateError,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
    skip: !Platform.isWindows,
  );
}
