# Stockfish configuration

Hash and Threads are the main settings for normal use. Analysis depth, move mode and capture delay remain app controls. Stockfish runs on the CPU; increasing thread count or memory does not guarantee faster end-to-end moves.

## Location and defaults

On desktop, put `engine_config.txt` beside the executable. Startup preserves existing files; new configs use 256 MB Hash and two threads. Android stores its config privately and creates 128 MB/two-thread defaults. Existing installations keep their values. Restart the app after editing; changing an active engine's configuration is not a UI feature.

The root [engine_config.txt](../engine_config.txt) is the desktop default template and is included directly by Rust, so the template and runtime defaults cannot drift.

```ini
# Leave CPU and memory available for capture, ONNX, the UI and the board/browser.
setoption name Threads value 2
setoption name Hash value 256
```

Hash is megabytes, not total application memory. Choose threads for the device's available CPU/thermal budget; phones can throttle under sustained load. Set Threads before Hash. Do not replace a tuned existing config just to copy these defaults.

## Optional settings

| Setting | Purpose | Notes |
| --- | --- | --- |
| `Skill Level` | Weaker practice play, 0–20 | 20 is full strength; omitted by default |
| `UCI_LimitStrength` / `UCI_Elo` | Approximate strength targeting | Use the range advertised by your installed engine; disable limiting for full strength |
| `SyzygyPath` | Local endgame tablebases | Requires separately supplied tablebases and storage |
| `MultiPV` | Additional analysis lines | Keep 1 for normal automation; higher values add work. Only the primary line updates the app's score |
| `UCI_Chess960` | Chess960 variant | Must remain false: this app currently supports standard chess |

Configuration accepts `setoption name ...` lines, blank lines and `#` comments. Arbitrary UCI commands, embedded control characters, oversized configs and malformed supported numeric settings are rejected. Unknown engine-specific options are passed to Stockfish; an option's presence here does not guarantee your engine supports it. The installed engine's `uci` response is authoritative.

Move Overhead is a clock-management setting; this app sends depth-based searches, so it is not a substitute for capture/verification delays. Evaluation networks are packaged with the selected engine; changing them is unnecessary for normal use.

See [Stockfish's upstream option definitions](https://github.com/official-stockfish/Stockfish/blob/master/src/engine.cpp) for engine option semantics. Model confidence and platform capture settings are separate from Stockfish options.
