import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() => runApp(const ChessPilotApp());

class ChessPilotApp extends StatelessWidget {
  const ChessPilotApp({super.key});
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
    home: const PilotControls(),
  );
}

class PilotControls extends StatefulWidget {
  const PilotControls({super.key});
  @override
  State<PilotControls> createState() => _PilotControlsState();
}

class _PilotControlsState extends State<PilotControls> {
  String? color;
  String mode = 'drag';
  int depth = 15;
  double delay = 0.4;
  bool kingside = false, queenside = false;
  void selectColor(String value) => setState(() => color = value);

  @override
  Widget build(BuildContext context) => CallbackShortcuts(
    bindings: {
      const SingleActivator(LogicalKeyboardKey.escape): () =>
          setState(() => color = null),
      const SingleActivator(LogicalKeyboardKey.keyW): () =>
          selectColor('White'),
      const SingleActivator(LogicalKeyboardKey.keyB): () =>
          selectColor('Black'),
      const SingleActivator(LogicalKeyboardKey.arrowRight): () =>
          setState(() => depth = (depth + 1).clamp(10, 30)),
      const SingleActivator(LogicalKeyboardKey.arrowLeft): () =>
          setState(() => depth = (depth - 1).clamp(10, 30)),
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
                          'W / B — choose color\n← / → — analysis depth\nEsc — color selection',
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
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
                        Text('Playing as $color', textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        const SizedBox(
                          height: 45,
                          child: FilledButton(
                            onPressed: null,
                            child: Text('Play Next Move'),
                          ),
                        ),
                        const SizedBox(height: 12),
                        const Text('Castling Rights:'),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Kingside Castle'),
                          value: kingside,
                          onChanged: (v) => setState(() => kingside = v!),
                        ),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Queenside Castle'),
                          value: queenside,
                          onChanged: (v) => setState(() => queenside = v!),
                        ),
                        const CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('Auto Next Moves'),
                          value: false,
                          onChanged: null,
                        ),
                        const Text(
                          'Move controls become available when engine and capture are connected.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white70),
                        ),
                      ],
                      const SizedBox(height: 16),
                      Text('Stockfish Depth: $depth'),
                      Slider(
                        min: 10,
                        max: 30,
                        divisions: 20,
                        value: depth.toDouble(),
                        semanticFormatterCallback: (v) => 'Depth ${v.round()}',
                        onChanged: (v) => setState(() => depth = v.round()),
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
                          onChanged: (v) => setState(() => delay = v),
                        ),
                        const Text('Move Mode:'),
                        const SizedBox(height: 8),
                        SegmentedButton<String>(
                          segments: const [
                            ButtonSegment(value: 'drag', label: Text('Drag')),
                            ButtonSegment(value: 'click', label: Text('Click')),
                          ],
                          selected: {mode},
                          onSelectionChanged: (v) =>
                              setState(() => mode = v.single),
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
