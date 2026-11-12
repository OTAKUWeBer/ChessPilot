# Native runtime boundary

The `chesspilot-runtime` cdylib exports four C ABI functions. Dart's `native_client.dart` is the current caller; both sides are built from the same revision.

```c
uint8_t *chesspilot_alloc(size_t length);
char *chesspilot_request(const uint8_t *input, size_t length);
void chesspilot_free_input(uint8_t *input, size_t length);
void chesspilot_free_response(char *response);
```

Allocate input in Rust, copy initialized UTF-8 JSON bytes, call synchronously, and release both buffers exactly once with their matching Rust functions. Requests are length-delimited (maximum 1 MiB); responses are NUL-terminated JSON. Do not free Rust allocations with the Dart or C allocator. Invalid pointers are outside the ABI's safety contract; invalid JSON, UTF-8, session IDs and request fields return structured errors. Panics in request dispatch are contained at the boundary.

Responses are `{"ok":true,"result":...}` or `{"ok":false,"error":"..."}`. `open` returns a session ID and initial state. Other commands include `session`:

* `configure`: optional `color` (`w`, `b`, null), `depth` (10-30), `delay` (0-1), `mode` (`drag`, `click`), and castling booleans. All fields validate before committing.
* `initialize_engine`: optional explicit `engine_path` and `config_path`. Returns quickly; a native worker owns engine initialization. Default engine lookup uses installed/development resource locations and PATH. Android library-based engine integration is not implemented yet.
* `initialize`: engine initialization followed by persistent ONNX/model initialization and a primary-monitor capture probe. Accepts the engine arguments plus optional `model_path` and `runtime_path`. This is Flutter's startup command. Capture failure preserves a successfully initialized engine.
* `initialize_capture`: retries only model/runtime/capture setup; accepts `model_path` and `runtime_path`.
* `play`: after color selection and initialization, launches the native capture/analyze/dispatch/verify controller. No pixels, FEN or input points are supplied by Dart. Duplicate work is rejected. The selected player color supplies the active side, matching the current Python manual behavior.
* `set_auto`: requires `enabled` boolean. Enabling starts one native Auto worker from a verified history/geometry baseline; no baseline returns an error asking for one verified manual move. Disabling requests Stop immediately. `auto_mode` reports the selected state and `auto_available` reports readiness to start/resume.
* `analyze`: internal full-FEN analysis command, retained for engine integration tests. It does not dispatch input and is not a manual-FEN UI flow.
* `status`: current settings, color, busy/error/status, capability flags, latest analysis and `confirmed_fen`. Analysis is a prediction; `confirmed_fen` changes only after visual verification.
* `stop`: invalidates queued/ongoing analysis generation immediately and requests engine stop. Busy remains true until the worker acknowledges completion.
* `close`: removes the session from the registry, cancels and joins work, and disposes the engine. It can block, so Dart performs it in a background isolate. Desktop-window exit must eventually await this operation through the platform close lifecycle.

Capture/automation flags become true only after the model and Windows/Linux backend initialize. Linux probes XTEST or wlroots virtual-pointer capability as well as capture; unsupported compositors report an error. Flags remain false for unconnected platforms. Progress/analysis includes a session generation; Stop and settings/color changes invalidate move work. Startup initialization is independent of color/settings. Multiple clients can own separate sessions, but one session admits only one native job at a time. Native state is authoritative; Dart snapshots contain no separate chess rules or engine state.

Within one native process, a desktop input owner also excludes overlapping Play transactions from different sessions, matching Python's global processing lock. A competing session reports an error before capture/analysis/input; it does not wait and later send an obsolete move.

The UI polls status while a native operation is busy, including Auto's wait loop; capture frames and model tensors never cross this JSON UI boundary. Logging installation/download, Wayland portals, desktop shutdown and Android service ownership remain migration work.

## Perception module

`vision::BoardReader<OnnxPredictor>` owns a persistent native ONNX session and consumes checked packed RGB frames. It ports Python's 640×640 Pillow Lanczos letterbox, RGB/CHW float32 normalization, output decoding, board-crop refinement and overlapping tile search. All boxes return in capture-frame coordinates. Raw detection for promotion dialogs can disable refinement.

ONNX Runtime is loaded explicitly from a shared library, using the 1.20 C API; no Python interpreter is involved. One process pins one runtime-library path. Model shape/type mismatches and unreadable positions return errors or no result. Cancellation is checked before and after each inference; an in-flight native inference completes before cancellation takes effect. Search is capped at 64 inferences per observation.

The module has independent inference tests and is also exercised through real Windows capture/controller tests. See `tests/fixtures/vision/README.md` for Python reference provenance and real-model parity checks. The resampling contract follows Pillow; its license is retained in `third_party/Pillow-LICENSE.txt`.

## Windows desktop adapters

`desktop::windows::WindowsCapture` captures the primary monitor, matching the current Python monitor choice. It returns packed RGB, signed physical desktop origin and a capture timestamp. GDI resources and per-thread DPI context are scoped and restored on every return path. `desktop::observe` feeds one captured frame through the persistent board reader and retains the source bounds; model/crop offsets stay in frame space until `CaptureBounds::input_point` adds the monitor origin exactly once.

`desktop::input::windows_move` preserves the Python Windows drag/click event order and delays, using ties-to-even rounding. `WindowsPointer` checks native API results and detects clipped pointer coordinates. Gesture cancellation is checked between events and in 5 ms wait slices. Once a button press has been attempted, an OS error is reported as uncertain delivery. Cleanup attempts release without retrying the chess move; OS delivery alone is never confirmed chess success.

The adapter test uses only its own temporary target window. It verifies capture colors/row direction, DPI restoration, repeated capture resource cleanup, and actual received button events. Run with `CHESSPILOT_DESKTOP_TEST=1` and `--test windows_desktop -- --include-ignored` on an interactive Windows desktop. Frame contents remain in memory.

## Shared move controller

`controller::play` owns one manual transaction. It obtains a board with bounded read-only retries, prepares the same placement-based castling flags as Python, analyzes it with the persistent engine, then rechecks placement, capture bounds, geometry and freshness before any input. It uses square centers and source origin mapping; jitter/humanization and cursor relocation remain pending.

King castling is followed by a new observation. An automatic rook move needs no extra gesture. A rook fallback is permitted only for a fresh exact king-only change with the rook still at its source and its destination empty. Promotion observations bypass board-validity refinement, retain Python's pure candidate filter, and require four distinct aligned menu choices near the destination before one tap. Verification checks the full expected placement, including the chosen underpromotion.

No move is automatically replayed after uncertain delivery or failed visual verification. A predicted position is never committed as confirmed history. A legal immediate opponent reply can confirm the latest board while retaining our move's prediction separately. An observation older than three seconds, a changed source or changed board geometry stops dispatch. These intentional differences from the Python unverified-success/retry behavior are recorded in `next/README.md`.

`tests/controller.rs` covers normal moves, all castlings and promotion choices/colors, pre-input changes/stale frames, cancellation, input uncertainty, capture failure and absent/ambiguous menus. `tests/windows_pipeline.rs` creates an owned temporary full-screen board with sprites derived from the repository demo. Through the real session API it captures, detects, analyzes, receives one OS move, redraws, and verifies the result in both orientations and input modes. It then renders two legal opponent replies and confirms exactly one Auto response to each, including no action on an unchanged board and no extra action after Stop. It also refuses a duplicate Play. Run with the four integration environment variables in `next/README.md`. This does not prove sustained play, real target-site menus, a packaged Flutter window or phone/compositor behavior.

## Auto and legal history

`controller::auto_play` uses the same persistent capture/model/input/engine owners as manual Play; it does not create a worker per frame. A verified manual result seeds full FEN, geometry and capture bounds. While waiting, unchanged placements only poll; changed placements must settle for the configured opponent/screenshot delay and match another fresh observation before reconciliation. Capture/mismatch retries are bounded by the existing settings constants.

`EngineService::legal_moves` uses Stockfish's depth-one perft output. `reconcile_reply` filters legal candidates using the ported move comparisons, applies a candidate through Stockfish and compares the entire resulting placement before accepting its full FEN. Invalid/duplicate rows, inconsistent counts, missing FEN, EOF, timeout and cancellation reject the operation and clean up the subprocess. This extends the existing Stockfish-specific `d` contract; it is not a generic UCI-engine feature. Protocol references: [Stockfish command handling](https://github.com/official-stockfish/Stockfish/blob/master/src/uci.cpp), [root perft output](https://github.com/official-stockfish/Stockfish/blob/master/src/perft.h).

Auto retains castling/en-passant/counter history after the baseline. Castling checkboxes restrict analysis without erasing still-legal rights from canonical history: when preferences filter rights, Stockfish applies the chosen move against the canonical position separately before visual confirmation. King/rook moves and captures remove rights normally; lost rights are never regranted from placement. The initial manual baseline still uses Python's supplied-color/default-history assumptions; pixels cannot reconstruct earlier moves. Auto stops on a terminal legal-move list, uncertain delivery, stale/changed geometry or repeated unreadable/unmatched positions.

Stop immediately clears Auto selection and invalidates the work generation. History remains usable if stopped while waiting or analyzing before input. From dispatch until confirmed completion, Stop/error invalidates it; late results cannot restore it. A new verified manual result is then required. This prevents uncertain delivery from scheduling a repeated move. The Auto `A` shortcut and checkbox route to this native command; Dart does not infer turns.

## Linux desktop adapters

`desktop::open` selects X11 or Wayland from the standard session environment, keeping each capture source paired with its own input adapter. The session worker and controller are shared with Windows. X11 uses `x11rb` to preserve Xauthority authentication, prefer the primary RandR monitor (or root-screen fallback), read a TrueColor ZPixmap and send checked XTEST events. The pixel converter validates masks, stride and byte order. Pointer coordinates are checked after motion, the old corner fail-safe is retained, and X11 gesture timing includes PyAutoGUI's default pauses. Socket replies use bounded polling.

The wlroots path calls `grim -t ppm -s 1 -` without a shell and decodes bounded RGB8 output in memory. The whole captured layout supplies virtual-pointer extents; it no longer combines a full-layout image with the first output's physical resolution. A dimension change aborts the current pairing and requires reconnecting. The client binds only the v1 requests it implements, handles fragmented stream reads and compositor errors/removal, gives sync callbacks fresh IDs, acknowledges released-button sequences, and attempts release/destruction during cleanup. Input preserves Python's 20-step drag and click/frame sequence; completion still requires visual board verification.

This backend requires screencopy plus `zwlr_virtual_pointer_manager_v1`. GNOME/KDE Wayland portal sessions are not implemented yet. `tests/linux_adapters.rs` exercises codecs, helper failure/deadline handling, frozen Python gesture traces and a fake compositor, including denied/removed/unsupported cases. The Linux target compile/lint checks pass from Windows; actual compositor input, mixed-scale layout mapping and Flutter keep-above behavior are left for the user's later Linux test. `tests/linux_live.rs` supplies an explicit capture/capability probe with no gestures. See `next/linux-testing.md` for setup and commands.
