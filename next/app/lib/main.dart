import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'pilot_controller.dart';

void main() => runApp(const ChessPilotApp());

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
      cardTheme: const CardThemeData(color: Color(0xff373737)),
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
  void refresh() {
    if (mounted) setState(() {});
  }

  @override
  void initState() {
    super.initState();
    controller = widget.controller ?? PilotController();
    controller.addListener(refresh);
    controller.initialize();
  }

  @override
  void dispose() {
    controller.removeListener(refresh);
    if (widget.controller == null) controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => controller.state == null
      ? Scaffold(
          body: Center(
            child: Text(controller.error ?? 'Starting ChessPilot...'),
          ),
        )
      : CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.escape): () {
              controller.command('stop');
              controller.configure({'color': null});
            },
            const SingleActivator(LogicalKeyboardKey.keyW): () =>
                selectColor('White'),
            const SingleActivator(LogicalKeyboardKey.keyB): () =>
                selectColor('Black'),
            const SingleActivator(LogicalKeyboardKey.arrowRight): () =>
                controller.configure({'depth': (depth + 1).clamp(10, 30)}),
            const SingleActivator(LogicalKeyboardKey.arrowLeft): () =>
                controller.configure({'depth': (depth - 1).clamp(10, 30)}),
            const SingleActivator(LogicalKeyboardKey.keyP): () {
              if (canPlay) controller.command('play');
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
              if (color != null) controller.configure({'kingside': !kingside});
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
              body: SafeArea(
                child: ListView(
                  padding: const EdgeInsets.all(15),
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'ChessPilot',
                            style: TextStyle(
                              color: Color(0xff4caf50),
                              fontSize: 26,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Shortcuts',
                          icon: const Icon(Icons.keyboard),
                          onPressed: () => showDialog<void>(
                            context: context,
                            builder: (_) => const AlertDialog(
                              title: Text('Keyboard shortcuts'),
                              content: Text(
                                'W / B — choose color\n← / → — analysis depth\n↑ / ↓ — screenshot delay before choosing color\nD / C — drag / click before choosing color\nP — play next move\nA — toggle Auto after a verified move\nK / Q — castling rights\nEsc — stop and return to color selection',
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (controller.isAndroid) ...[
                      const Text(
                        'Share the entire display and enable touch control to play in another app.',
                      ),
                      OutlinedButton(
                        onPressed: () =>
                            controller.platformAction('enableTouch'),
                        child: Text(
                          controller.platformState?['touch'] == true
                              ? 'Touch control enabled'
                              : 'Enable touch control',
                        ),
                      ),
                      OutlinedButton(
                        onPressed: () => controller.platformAction(
                          controller.platformState?['capture'] == true
                              ? 'stopCapture'
                              : 'startCapture',
                        ),
                        child: Text(
                          controller.platformState?['capture'] == true
                              ? 'Stop screen sharing'
                              : 'Share entire display',
                        ),
                      ),
                      if (controller.platformState?['error'] != null)
                        Text(
                          controller.platformState!['error'] as String,
                          style: const TextStyle(color: Colors.orangeAccent),
                        ),
                    ],
                    if (controller.error != null)
                      Text(
                        controller.error!,
                        style: const TextStyle(color: Colors.orangeAccent),
                      ),
                    if (controller.state!['engine_ready'] != true &&
                        controller.state!['busy'] != true)
                      OutlinedButton(
                        onPressed: () => controller.command('initialize'),
                        child: const Text('Retry engine'),
                      ),
                    if (controller.state!['engine_ready'] == true &&
                        controller.state!['capture_ready'] != true &&
                        controller.state!['busy'] != true)
                      OutlinedButton(
                        onPressed: () =>
                            controller.command('initialize_capture'),
                        child: const Text('Retry board capture'),
                      ),
                    Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (color == null) ...[
                              const Text(
                                'Select Your Color:',
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 12),
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
                            ] else ...[
                              Text(
                                'Color: $color',
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 12),
                              SizedBox(
                                height: 45,
                                child: FilledButton(
                                  onPressed: canPlay
                                      ? () => controller.command('play')
                                      : null,
                                  child: const Text('Play Next Move'),
                                ),
                              ),
                              const SizedBox(height: 12),
                              const Text('Castling Rights:'),
                              CheckboxListTile(
                                contentPadding: EdgeInsets.zero,
                                title: const Text('Kingside Castle'),
                                value: kingside,
                                onChanged: (v) =>
                                    controller.configure({'kingside': v!}),
                              ),
                              CheckboxListTile(
                                contentPadding: EdgeInsets.zero,
                                title: const Text('Queenside Castle'),
                                value: queenside,
                                onChanged: (v) =>
                                    controller.configure({'queenside': v!}),
                              ),
                              CheckboxListTile(
                                contentPadding: EdgeInsets.zero,
                                title: const Text('Auto Next Moves'),
                                subtitle: canPlay && !canStartAuto
                                    ? const Text(
                                        'Play one verified move to enable Auto',
                                      )
                                    : null,
                                value: autoMode,
                                onChanged: autoMode || canStartAuto
                                    ? (enabled) => controller.command(
                                        'set_auto',
                                        {'enabled': enabled!},
                                      )
                                    : null,
                              ),
                              Text(
                                controller.error ??
                                    controller.state!['status'] as String,
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: Colors.white70),
                              ),
                              if (controller.state!['busy'] == true)
                                OutlinedButton(
                                  onPressed: () => controller.command('stop'),
                                  child: const Text('Stop'),
                                ),
                            ],
                            const SizedBox(height: 16),
                            Text('Stockfish Depth: $depth'),
                            Slider(
                              min: 10,
                              max: 30,
                              divisions: 20,
                              value: depth.toDouble(),
                              semanticFormatterCallback: (v) =>
                                  'Depth ${v.round()}',
                              onChanged: (v) =>
                                  controller.configure({'depth': v.round()}),
                            ),
                            if (color == null) ...[
                              Text(
                                'Screenshot Delay: ${delay.toStringAsFixed(1)} seconds',
                              ),
                              Slider(
                                min: 0,
                                max: 1,
                                divisions: 10,
                                value: delay,
                                semanticFormatterCallback: (v) =>
                                    '${v.toStringAsFixed(1)} seconds',
                                onChanged: (v) =>
                                    controller.configure({'delay': v}),
                              ),
                              const Text('Move Mode:'),
                              const SizedBox(height: 8),
                              SegmentedButton<String>(
                                segments: const [
                                  ButtonSegment(
                                    value: 'drag',
                                    label: Text('Drag'),
                                  ),
                                  ButtonSegment(
                                    value: 'click',
                                    label: Text('Click'),
                                  ),
                                ],
                                selected: {mode},
                                onSelectionChanged: (v) =>
                                    controller.configure({'mode': v.single}),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
}
