import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui' show AppExitResponse;
import 'pilot_controller.dart';
import 'diagnostics.dart';
import 'desktop_platform.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  installErrorReporting();
  runApp(const ChessPilotApp());
}

class ChessPilotApp extends StatelessWidget {
  final PilotController? controller;
  const ChessPilotApp({super.key, this.controller});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'ChessPilot',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: const Color(0xff2d2d2d),
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xff4caf50),
        brightness: Brightness.dark,
        primary: const Color(0xff4caf50),
      ),
      cardTheme: const CardThemeData(
        color: Color(0xff373737),
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(0, 42),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(0, 36),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        ),
      ),
      sliderTheme: SliderThemeData(
        trackHeight: 4,
        trackGap: 0,
        inactiveTrackColor: const Color(0xff5a5a5a),
        tickMarkShape: SliderTickMarkShape.noTickMark,
        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
        overlayShape: const RoundSliderOverlayShape(overlayRadius: 16),
      ),
      dividerTheme: const DividerThemeData(
        color: Color(0xff505050),
        thickness: 1,
      ),
    ),
    home: PilotControls(controller: controller),
  );
}

class PilotControls extends StatefulWidget {
  final PilotController? controller;
  const PilotControls({super.key, this.controller});
  @override
  State<PilotControls> createState() => _PilotControlsState();
}

class _PilotControlsState extends State<PilotControls> {
  late final PilotController controller;
  late final AppLifecycleListener lifecycle;
  final playKey = GlobalKey();
  bool requestingPlay = false;
  bool? setupWindow;
  int? setupHeight;
  final setupKey = GlobalKey();

  Future<void> play() async {
    if (!canPlay || requestingPlay) return;
    requestingPlay = true;
    final generation = controller.state!['generation'];
    Map<String, dynamic>? target;
    try {
      final box = playKey.currentContext?.findRenderObject();
      if (!controller.isAndroid && box is RenderBox && box.hasSize) {
        try {
          target = await DesktopPlatform.returnTarget(
            box.localToGlobal(box.size.center(Offset.zero)),
          );
        } catch (error, stack) {
          FlutterError.reportError(
            FlutterErrorDetails(
              exception: error,
              stack: stack,
              context: ErrorDescription('reading the pointer return target'),
            ),
          );
        }
      }
      if (mounted && canPlay && generation == controller.state!['generation']) {
        controller.command('play', {'return_target': ?target});
      }
    } finally {
      requestingPlay = false;
    }
  }

  String? get color => switch (controller.state?['color']) {
    'w' => 'White',
    'b' => 'Black',
    _ => null,
  };
  String get mode => controller.state!['mode'] as String;
  int get depth => controller.state!['depth'] as int;
  double get delay => (controller.state!['delay'] as num).toDouble();
  bool get kingside => controller.state!['kingside'] as bool;
  bool get queenside => controller.state!['queenside'] as bool;
  bool get canPlay =>
      color != null &&
      controller.state!['game_result'] == null &&
      controller.state!['auto_mode'] != true &&
      controller.state!['busy'] != true &&
      controller.state!['engine_ready'] == true &&
      controller.state!['automation_ready'] == true;
  bool get autoMode => controller.state!['auto_mode'] == true;
  bool get canStartAuto =>
      canPlay && controller.state!['auto_available'] == true;
  void toggleAuto() {
    if (autoMode || canStartAuto) {
      controller.command('set_auto', {'enabled': !autoMode});
    }
  }

  void selectColor(String value) =>
      controller.configure({'color': value == 'White' ? 'w' : 'b'});
  void changeColor() {
    controller.command('stop');
    controller.configure({'color': null});
  }

  void refresh() {
    if (!mounted) return;
    setState(() {});
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncSetupWindow());
  }

  void _syncSetupWindow() {
    if (!mounted || controller.isAndroid || controller.state == null) return;
    final enabled = _compactSetup;
    final box = setupKey.currentContext?.findRenderObject();
    final height = enabled && box is RenderBox && box.hasSize
        ? box.size.height.ceil().clamp(160, 600)
        : 160;
    if (setupWindow == enabled && setupHeight == height) return;
    setupWindow = enabled;
    setupHeight = height;
    DesktopPlatform.setupWindow(enabled, height: height).catchError((
      Object error,
      StackTrace stack,
    ) {
      setupWindow = null;
      FlutterError.reportError(
        FlutterErrorDetails(
          exception: error,
          stack: stack,
          context: ErrorDescription('switching the Stockfish setup window'),
        ),
      );
    });
  }

  @override
  void initState() {
    super.initState();
    controller = widget.controller ?? PilotController();
    controller.addListener(refresh);
    controller.initialize();
    lifecycle = AppLifecycleListener(
      onExitRequested: () async {
        if (controller.isAndroid) return AppExitResponse.exit;
        controller.command('stop');
        try {
          await controller.close();
          return AppExitResponse.exit;
        } catch (error, stack) {
          controller.error = 'Cannot close ChessPilot: $error';
          refresh();
          FlutterError.reportError(
            FlutterErrorDetails(
              exception: error,
              stack: stack,
              context: ErrorDescription('waiting for native shutdown'),
            ),
          );
          return AppExitResponse.cancel;
        }
      },
    );
  }

  @override
  void dispose() {
    lifecycle.dispose();
    controller.removeListener(refresh);
    if (widget.controller == null) controller.dispose();
    super.dispose();
  }

  bool get busy => controller.state!['busy'] == true;
  bool get _showSetup {
    if (controller.isAndroid) {
      return controller.setupAttempted &&
          controller.state!['engine_ready'] != true;
    }
    return controller.state!['download'] != null ||
        busy &&
            (controller.state!['operation'] as String? ?? '').startsWith(
              'initialize',
            ) ||
        controller.setupAttempted &&
            (controller.state!['engine_ready'] != true ||
                !controller.isAndroid &&
                    controller.state!['capture_ready'] != true) ||
        controller.error != null && controller.state!['capture_ready'] != true;
  }

  bool get _compactSetup =>
      !controller.isAndroid &&
      _showSetup &&
      (controller.state!['engine_ready'] != true ||
          busy &&
              (controller.state!['operation'] as String? ?? '').startsWith(
                'initialize',
              ));

  Widget _header() => SizedBox(
    height: controller.isAndroid ? 48 : 40,
    child: Row(
      children: [
        SizedBox(
          width: controller.isAndroid ? 48 : 40,
          child: color == null
              ? null
              : IconButton(
                  tooltip: 'Change color',
                  onPressed: changeColor,
                  icon: const Icon(Icons.arrow_back, size: 20),
                  padding: EdgeInsets.zero,
                ),
        ),
        const Expanded(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              'ChessPilot',
              style: TextStyle(
                color: Color(0xff4caf50),
                fontSize: 26,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
        SizedBox(
          width: controller.isAndroid ? 48 : 40,
          child: IconButton(
            tooltip: controller.isAndroid ? 'Help and logs' : 'Shortcuts',
            icon: Icon(
              controller.isAndroid
                  ? Icons.help_outline
                  : Icons.keyboard_outlined,
              size: 22,
            ),
            padding: EdgeInsets.zero,
            onPressed: () => showDialog<void>(
              context: context,
              builder: (_) => AlertDialog(
                scrollable: true,
                title: Text(
                  controller.isAndroid
                      ? 'Phone controls'
                      : 'Keyboard shortcuts',
                ),
                content: Text(
                  controller.isAndroid
                      ? 'Choose your color, enable touch control, then share your entire display.\n\nSwitch to the board and tap the floating bubble for Play, Auto and Stop. Drag the bubble or panel header to move it away from the board.\n\nStart Play or Auto on your turn. Tap Stop to pause; opening this dashboard also pauses moves.'
                      : 'W / B — choose color\n← / → — analysis depth\n↑ / ↓ — screenshot delay\nD / C — drag / click before choosing color\nP — play next move\nA — toggle Auto (start on your turn)\nK / Q — castling rights\nEsc — stop and change color',
                ),
                actions: [
                  TextButton(
                    onPressed: () => showDialog<void>(
                      context: context,
                      builder: (_) => DiagnosticsDialog(controller: controller),
                    ),
                    child: const Text('Diagnostics / logs'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Close'),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (controller.isAndroid)
          IconButton(
            tooltip: 'Stop sharing and exit',
            onPressed: () => controller.platformAction('exit'),
            icon: const Icon(Icons.close, size: 22),
          ),
      ],
    ),
  );

  Widget _setup() {
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncSetupWindow());
    final download = controller.state!['download'] as Map?;
    final engineReady = controller.state!['engine_ready'] == true;
    return Card(
      key: setupKey,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              controller.error != null
                  ? 'Setup needs attention'
                  : engineReady
                  ? 'Preparing screen capture'
                  : 'Preparing Stockfish',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              controller.error ??
                  download?['stage'] as String? ??
                  controller.state!['status'] as String,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            if (download != null) ...[
              if (download['cpu'] != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    download['cpu'] as String,
                    style: const TextStyle(fontSize: 12, color: Colors.white70),
                  ),
                ),
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value:
                    download['total'] is num && (download['total'] as num) > 0
                    ? ((download['downloaded'] as num? ?? 0) /
                              (download['total'] as num))
                          .clamp(0, 1)
                          .toDouble()
                    : null,
              ),
              const SizedBox(height: 8),
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                spacing: 12,
                children: [
                  if (download['total'] != null)
                    Text(
                      '${((download['downloaded'] as num? ?? 0) / 1048576).toStringAsFixed(1)} / ${((download['total'] as num) / 1048576).toStringAsFixed(1)} MB',
                      style: const TextStyle(fontSize: 12),
                    ),
                  if (download['bytes_per_second'] case final num speed)
                    Text(
                      '${(speed / 1048576).toStringAsFixed(1)} MB/s',
                      style: const TextStyle(fontSize: 12),
                    ),
                  if (download['total'] is num &&
                      (download['total'] as num) > 0)
                    Text(
                      '${(((download['downloaded'] as num? ?? 0) / (download['total'] as num)) * 100).clamp(0, 100).round()}%',
                      style: const TextStyle(fontSize: 12),
                    ),
                ],
              ),
            ] else if (busy) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton(
                onPressed: busy
                    ? () => controller.command('stop')
                    : () => controller.command(
                        engineReady ? 'initialize_capture' : 'initialize',
                      ),
                child: Text(busy ? 'Cancel' : 'Try again'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _phoneSetup() {
    final touch = controller.platformState?['touch'] == true;
    final sharing = controller.platformState?['capture'] == true;
    final ready = sharing && controller.state!['capture_ready'] == true;
    final preparing =
        busy && controller.state!['operation'] == 'initialize_capture';
    final failure =
        controller.platformState?['error'] as String? ?? controller.error;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              !touch
                  ? 'Enable touch control'
                  : ready
                  ? 'Ready for your board'
                  : preparing
                  ? 'Preparing screen capture'
                  : sharing
                  ? 'Restart screen sharing'
                  : 'Share your board',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Text(
              !touch
                  ? 'Allow ChessPilot to tap and drag chess pieces. Turn on ChessPilot touch control in Android Accessibility.'
                  : ready
                  ? 'Switch to your board. Use the movable bubble for Play, Auto and Stop.'
                  : preparing
                  ? 'Checking the shared display and board detector…'
                  : sharing
                  ? failure ??
                        'Capture is not ready. Restart sharing to reconnect your display.'
                  : 'Share your entire display so ChessPilot can read the board. Allow notifications for visible Stop and Exit controls while sharing.',
              style: const TextStyle(fontSize: 13, color: Colors.white70),
            ),
            const SizedBox(height: 10),
            if (!touch)
              OutlinedButton(
                onPressed: () => controller.platformAction('enableTouch'),
                child: const Text('Open accessibility settings'),
              )
            else ...[
              const Text(
                'Touch control enabled',
                style: TextStyle(fontSize: 12, color: Color(0xff81c784)),
              ),
              const SizedBox(height: 6),
              OutlinedButton(
                onPressed: preparing
                    ? null
                    : () async {
                        if (sharing) {
                          await controller.platformAction('stopCapture');
                        }
                        if (!sharing || !ready) {
                          await controller.platformAction('startCapture');
                        }
                      },
                child: Text(
                  sharing
                      ? ready
                            ? 'Stop screen sharing'
                            : 'Restart screen sharing'
                      : 'Share entire display',
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _checkbox(String label, bool value, ValueChanged<bool>? changed) =>
      CheckboxListTile(
        title: Text(label, style: const TextStyle(fontSize: 14)),
        value: value,
        onChanged: changed == null ? null : (value) => changed(value!),
        controlAffinity: ListTileControlAffinity.leading,
        contentPadding: EdgeInsets.zero,
        dense: true,
        visualDensity: controller.isAndroid
            ? VisualDensity.standard
            : const VisualDensity(horizontal: -4, vertical: -4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
      );

  Widget _depthControl() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const Text(
        'Stockfish Depth:',
        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
      ),
      SizedBox(
        height: controller.isAndroid ? 44 : 30,
        child: Slider(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          min: controller.isAndroid ? 8 : 10,
          max: 30,
          divisions: controller.isAndroid ? 22 : 20,
          value: depth.toDouble(),
          semanticFormatterCallback: (value) => 'Depth ${value.round()}',
          onChanged: (value) => controller.configure({'depth': value.round()}),
        ),
      ),
      Text(
        'Depth: $depth',
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 12, color: Colors.white70),
      ),
    ],
  );

  Widget _delayControl() => Wrap(
    alignment: WrapAlignment.spaceBetween,
    crossAxisAlignment: WrapCrossAlignment.center,
    spacing: 12,
    runSpacing: 8,
    children: [
      const Text('Screenshot delay', style: TextStyle(fontSize: 14)),
      DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xff4a4a4a),
          borderRadius: BorderRadius.circular(5),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              tooltip: 'Decrease screenshot delay',
              icon: const Icon(Icons.remove, size: 16),
              visualDensity: controller.isAndroid
                  ? VisualDensity.standard
                  : VisualDensity.compact,
              onPressed: delay <= 0
                  ? null
                  : () => controller.configure({
                      'delay': ((delay * 10).round() - 1) / 10,
                    }),
            ),
            Text(
              '${delay.toStringAsFixed(1)} s',
              style: const TextStyle(fontSize: 13),
            ),
            IconButton(
              tooltip: 'Increase screenshot delay',
              icon: const Icon(Icons.add, size: 16),
              visualDensity: controller.isAndroid
                  ? VisualDensity.standard
                  : VisualDensity.compact,
              onPressed: delay >= 1
                  ? null
                  : () => controller.configure({
                      'delay': ((delay * 10).round() + 1) / 10,
                    }),
            ),
          ],
        ),
      ),
    ],
  );

  Widget _moveStatus() {
    final result = controller.state!['game_result'] as String?;
    final error = controller.error;
    final invalidPosition =
        error != null &&
        (error.contains('Unsupported position') ||
            error.contains('King can be captured') ||
            error.contains('Invalid FEN') ||
            error.contains('Expected one king'));
    final accent = error != null
        ? Theme.of(context).colorScheme.error
        : result != null
        ? const Color(0xff81c784)
        : Colors.white70;
    final title = error != null
        ? invalidPosition
              ? 'Check the board position'
              : 'Move could not be completed'
        : switch (result) {
            'checkmate' => 'Checkmate!',
            'stalemate' => 'Draw by stalemate',
            'game_over' => 'Game over',
            _ => controller.state!['status'] as String,
          };
    final move = (controller.state!['analysis'] as Map?)?['best_move'];
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.07),
        border: Border.all(color: accent.withValues(alpha: 0.25)),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                error != null
                    ? Icons.info_outline
                    : result == 'checkmate'
                    ? Icons.emoji_events_outlined
                    : result != null
                    ? Icons.flag_outlined
                    : Icons.play_circle_outline,
                color: accent,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: result != null ? 16 : 13,
                    color: accent,
                    fontWeight: result != null || error != null
                        ? FontWeight.w600
                        : FontWeight.normal,
                  ),
                ),
              ),
            ],
          ),
          if (error != null || result != null) ...[
            const SizedBox(height: 8),
            Text(
              error != null
                  ? invalidPosition
                        ? 'Make sure the board is fully visible and your selected color is correct, then try Play again.'
                        : 'Check the board before trying Play again. Your settings are unchanged.'
                  : move != null
                  ? 'Move played: $move'
                  : 'This game has finished.',
              style: const TextStyle(fontSize: 12, color: Colors.white70),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: error != null
                  ? TextButton(
                      onPressed: () => showDialog<void>(
                        context: context,
                        builder: (_) => AlertDialog(
                          title: const Text('Move details'),
                          scrollable: true,
                          content: SelectableText(error),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(context).pop(),
                              child: const Text('Close'),
                            ),
                          ],
                        ),
                      ),
                      child: const Text('Details'),
                    )
                  : OutlinedButton(
                      onPressed: changeColor,
                      child: const Text('New game'),
                    ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _controls() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (color == null) ...[
            const Text(
              'Select Your Color:',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 15),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    onPressed: () => selectColor('White'),
                    child: const Text('White'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton(
                    onPressed: () => selectColor('Black'),
                    child: const Text('Black'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            _depthControl(),
            const Divider(height: 26),
            _delayControl(),
            const SizedBox(height: 16),
            const Text('Move Mode:', style: TextStyle(fontSize: 14)),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              style: SegmentedButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(5),
                ),
                minimumSize: const Size(0, 40),
              ),
              segments: const [
                ButtonSegment(value: 'drag', label: Text('Drag')),
                ButtonSegment(value: 'click', label: Text('Click')),
              ],
              selected: {mode},
              onSelectionChanged: (value) =>
                  controller.configure({'mode': value.single}),
            ),
          ] else ...[
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    key: playKey,
                    style: FilledButton.styleFrom(
                      minimumSize: Size(0, controller.isAndroid ? 48 : 45),
                    ),
                    onPressed: !canPlay
                        ? null
                        : controller.isAndroid
                        ? () => controller.platformAction('showControls')
                        : play,
                    child: Text(
                      controller.isAndroid
                          ? 'Show floating controls'
                          : 'Play Next Move',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    minimumSize: Size(68, controller.isAndroid ? 48 : 45),
                  ),
                  onPressed: busy || autoMode
                      ? () => controller.command('stop')
                      : null,
                  child: const Text('Stop'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Castling Rights:',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: _checkbox(
                    'Kingside',
                    kingside,
                    (value) => controller.configure({'kingside': value}),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _checkbox(
                    'Queenside',
                    queenside,
                    (value) => controller.configure({'queenside': value}),
                  ),
                ),
              ],
            ),
            const Divider(height: 18),
            if (!controller.isAndroid)
              Tooltip(
                message:
                    'Start on your turn. Auto plays the first move, then waits for the opponent.',
                child: _checkbox(
                  'Auto Next Moves',
                  autoMode,
                  autoMode || canStartAuto
                      ? (value) =>
                            controller.command('set_auto', {'enabled': value})
                      : null,
                ),
              ),
            const SizedBox(height: 8),
            _moveStatus(),
            const Divider(height: 26),
            _depthControl(),
          ],
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => controller.state == null
      ? Scaffold(
          body: Center(
            child: Text(controller.error ?? 'Starting ChessPilot...'),
          ),
        )
      : CallbackShortcuts(
          bindings: controller.isAndroid
              ? {}
              : {
                  const SingleActivator(LogicalKeyboardKey.escape): changeColor,
                  const SingleActivator(LogicalKeyboardKey.keyW): () =>
                      selectColor('White'),
                  const SingleActivator(LogicalKeyboardKey.keyB): () =>
                      selectColor('Black'),
                  const SingleActivator(LogicalKeyboardKey.arrowRight): () =>
                      controller.configure({
                        'depth': (depth + 1).clamp(10, 30),
                      }),
                  const SingleActivator(LogicalKeyboardKey.arrowLeft): () =>
                      controller.configure({
                        'depth': (depth - 1).clamp(10, 30),
                      }),
                  const SingleActivator(LogicalKeyboardKey.keyP): () {
                    play();
                  },
                  const SingleActivator(LogicalKeyboardKey.keyA): toggleAuto,
                  const SingleActivator(LogicalKeyboardKey.keyD): () {
                    if (color == null) controller.configure({'mode': 'drag'});
                  },
                  const SingleActivator(LogicalKeyboardKey.keyC): () {
                    if (color == null) controller.configure({'mode': 'click'});
                  },
                  const SingleActivator(LogicalKeyboardKey.arrowUp): () {
                    if (color == null) {
                      controller.configure({
                        'delay': ((delay * 10).round() + 1).clamp(0, 10) / 10,
                      });
                    }
                  },
                  const SingleActivator(LogicalKeyboardKey.arrowDown): () {
                    if (color == null) {
                      controller.configure({
                        'delay': ((delay * 10).round() - 1).clamp(0, 10) / 10,
                      });
                    }
                  },
                  const SingleActivator(LogicalKeyboardKey.keyK): () {
                    if (color != null) {
                      controller.configure({'kingside': !kingside});
                    }
                  },
                  const SingleActivator(LogicalKeyboardKey.keyQ): () {
                    if (color != null) {
                      controller.configure({'queenside': !queenside});
                    }
                  },
                },
          child: Focus(
            autofocus: true,
            child: Scaffold(
              backgroundColor: _compactSetup ? const Color(0xff373737) : null,
              body: SafeArea(
                child: ListView(
                  padding: _compactSetup
                      ? EdgeInsets.zero
                      : const EdgeInsets.symmetric(
                          horizontal: 15,
                          vertical: 12,
                        ),
                  children: [
                    if (!_compactSetup) ...[
                      _header(),
                      const SizedBox(height: 12),
                    ],
                    if (_showSetup) ...[_setup(), const SizedBox(height: 12)],
                    if (!_showSetup ||
                        controller.state!['engine_ready'] == true && !busy) ...[
                      if (controller.isAndroid) ...[
                        _phoneSetup(),
                        const SizedBox(height: 12),
                      ],
                      _controls(),
                    ],
                  ],
                ),
              ),
            ),
          ),
        );
}
