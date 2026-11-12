# Flutter / Rust migration — work in progress

Branch: `rust`. Python v2.3.1 remains the runnable reference in `src/`.

## Implemented and checked

* Flutter Windows/Linux/Android scaffold; green/dark selection and play screens.
* 380×520 desktop client area and native always-on-top request on Windows/Linux. Wayland window managers may ignore keep-above; real desktop validation is pending.
* Rust configuration, board/square geometry, move notation, FEN expansion/flipping, placement-based castling compatibility, game state and normal/castling/promotion/en-passant verification.
* Native ONNX inference with a persistent session, Pillow-compatible RGB Lanczos/letterbox preprocessing, model-output validation, detection-to-FEN and class/promotion mappings.
* Normal inference automatically retries board crops and overlapping tiles when a board is unreadable; crop coordinates are restored to the captured frame. Promotion detection retains the raw, unrefined path. Cancellation and a 64-inference limit bound each observation.
* Frozen Python vision fixtures check four complete preprocessing tensors byte for byte. Real native ONNX tests match all box coordinates/classes and FENs for normal capture, small-board recovery and an unreadable board.
* Frozen Python parity cases for 128 orientation mappings, 128 geometry points and eight castling combinations, plus Rust domain tests. Invalid inputs return errors instead of Python's invalid-square-to-a8 fallback.
* Flutter tests check the 380×520 layout, color selection, mode/delay/depth/castling shortcuts, Play readiness, Auto start/stop and Escape. Windows Play and Auto are connected to the native controller. Auto is available after a verified manual move establishes the turn/history baseline.
* Persistent Rust Stockfish service: UCI handshake, config options, depth/evaluation progress, best move, updated FEN, stop/cancel deadlines, stderr draining, process cleanup and restart on the next request after failure.
* Resource lookup and portable/user config creation preserve existing user files. Engine options and FEN input are validated before entering the UCI protocol.
* Subprocess fixtures cover silent/crashed/unresponsive engines, invalid output, stderr flooding, cancellation, and persistence. The local real Stockfish passed opening/checkmate analysis and persistent-process reuse.
* Flutter now uses the real Rust runtime DLL through a length-delimited C ABI. Rust owns settings, color/session state, engine work and progress; Dart renders snapshots. Engine operations run on a native worker, and changing color/Stop invalidates old results.
* Native buffer ownership, invalid requests, transactional settings and isolated sessions have tests. Dart integration tests exercise the compiled library and local Stockfish, not a mocked backend.
* Native Windows primary-monitor GDI capture and `SetCursorPos`/`SendInput` mouse delivery. Per-thread physical-pixel DPI context is restored after each operation; capture retains its signed monitor origin and timestamp.
* Windows click/drag sequencing preserves Python's rounding, intermediate point and timing. Stop/failure attempts button release, and delivery errors distinguish a move not dispatched from uncertain delivery. Recording tests inject cancellation/failure throughout each sequence.
* A real Windows integration test creates its own temporary window, checks captured RGB colors/top-down rows, repeated-capture GDI resource cleanup, and received click/drag events. It restores the cursor afterward. This proves adapter delivery, not chess move verification or full-app operation.
* The shared manual controller now connects capture, persistent ONNX, Stockfish, fresh pre-input board/geometry validation, native dispatch and visual confirmation. Session history commits only a verified outcome. Duplicate Play is rejected; Stop and settings/color changes invalidate ongoing work.
* Castling checks whether the target moved the rook automatically, and dispatches a rook fallback only after a fresh, exact king-only transition. Promotion uses raw detections and selects one of four distinct aligned menu pieces near the destination. All castlings and all promotion types/colors have controller tests; pure promotion candidates match frozen Python fixtures.
* A controlled native Windows board receives real mouse events and redraws its pieces. Through the actual session API, the complete capture → ONNX → Stockfish → input → visual verification path passes in drag/click modes and both orientations. This tests the native runtime; it does not establish a packaged Flutter desktop build or real target-site promotion/castling calibration.
* One native Auto worker waits for stable board changes, matches one legal opponent reply using Stockfish, preserves full FEN metadata and runs the same verified move path. Unchanged frames do not trigger a search/move. Stop/settings/color changes cancel work; uncertain delivery invalidates the Auto history baseline.
* The controlled Windows test now runs two Auto responses after each manual opening, in both colors and both input modes. It checks no move on an unchanged board, exactly one response per opponent move, visual confirmation and Stop without an extra move. Native unit tests cover lost castling rights, en passant metadata, illegal/unstable changes, terminal positions and late callbacks.

## Commands

Build the Rust runtime library first (use the GNU settings below on this workstation), then start Flutter:

```powershell
cargo build --manifest-path next/native/Cargo.toml -p chesspilot-runtime
cd next/app
flutter pub get
flutter test
flutter analyze
flutter run -d windows
```

In development the Dart loader finds `next/native/target/debug/chesspilot_runtime.dll` (or `libchesspilot_runtime.so` on Linux). `CHESSPILOT_LIBRARY_PATH` can select an explicit library for tests. Release app bundling of this library and Android native-library packaging are still pending; a missing native component is reported rather than replaced by simulated state. The real-engine Dart test requires `CHESSPILOT_STOCKFISH`, just like the native integration test below.

Flutter startup initializes the engine, model and capture on the Rust worker. In Windows development, model/runtime lookup includes `src/chess_detection.onnx` and the existing environment's ONNX Runtime DLL; release lookup expects native assets beside the executable. Play becomes available after initialization and color selection. Capture initialization can be retried independently of a ready engine. The runtime still uses the supplied player color as the active side, matching Python; the user must request a move on that side's turn.

After one visually verified manual move, enable Auto with its checkbox or `A`. The native worker waits for one legal opponent reply, then analyzes and plays once. `A`, Stop or Escape stops it; settings/color changes also cancel it. Stopping while waiting preserves the baseline. Uncertain input requires another verified manual move before Auto can resume. Escape and reselect the color to clear history when switching games/boards. Initial manual metadata retains Python's placement-based assumptions; the screenshot cannot recover earlier castling/en-passant history. Once a baseline exists, legal transitions preserve metadata instead of reinferring it each tick.

With a normal native Rust toolchain:

```powershell
cargo test --manifest-path next/native/Cargo.toml
```

The real-engine and ONNX integration tests are explicit, so they cannot silently pass without native assets:

```powershell
$env:CHESSPILOT_STOCKFISH = (Resolve-Path src/stockfish.exe).Path
$env:CHESSPILOT_MODEL = (Resolve-Path src/chess_detection.onnx).Path
$env:CHESSPILOT_ORT = (Resolve-Path venv/Lib/site-packages/onnxruntime/capi/onnxruntime.dll).Path
$env:CHESSPILOT_DESKTOP_TEST = '1'
cargo test --manifest-path next/native/Cargo.toml --workspace -- --include-ignored
```

On Linux set these paths to the native `stockfish`, model and ONNX Runtime shared library. The local Windows test reuses ONNX Runtime 1.20's DLL from the existing environment; the Rust runtime never starts Python. Release bundles must ship a compatible native library. On this workstation use the GNU linker settings below for both commands.

`CHESSPILOT_DESKTOP_TEST=1` explicitly enables real interactive Windows tests: an owned colored window for adapter checks and an owned temporary full-screen chessboard for complete native pipeline checks. They refuse input if another window covers their target and restore the cursor afterward. Run on an unlocked desktop with the mouse released; sandbox desktop restrictions may require running the tests outside the sandbox. No desktop image is saved. Unit tests do not need desktop access, the model or an engine.

This workstation lacks the Visual C++ desktop workload. Rust tests can currently run with its already-installed GNU toolchain and bundled LLVM linker:

```powershell
$rustGnuRoot = (rustup run stable-x86_64-pc-windows-gnu rustc --print sysroot)
$env:RUSTFLAGS = "-C linker=$($rustGnuRoot.Replace('\','/'))/lib/rustlib/x86_64-pc-windows-gnu/bin/rust-lld.exe -C linker-flavor=ld.lld -C link-self-contained=yes -C dlltool=C:/Android/Sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-dlltool.exe"
cargo +stable-x86_64-pc-windows-gnu test --manifest-path next/native/Cargo.toml --offline
```

Flutter desktop compilation still needs Visual C++ Build Tools; Android compilation needs a working JDK and verified SDK license/setup. Neither has been installed or modified by this migration.

## Next work, in order

1. Extend differential fixtures for remaining domain/detection behavior, preserving current valid-input contracts. Record intentional deviations individually.
2. Finish resource installation/download and rotating file logging; the persistent desktop Stockfish service and resource/config resolution are ported and tested.
3. Complete native-library build/bundling and window-close lifecycle integration. Flutter is connected to the Rust session/engine; settings/session ownership is native, not duplicated in Dart. Desktop application exit and Android service teardown still need real platform verification.
4. Finish recovery/calibration and sustained-play acceptance for the connected Windows manual/Auto pipeline. It now reconciles a legal immediate opponent reply during visual verification; complete history before the initial manual baseline is still unavailable from pixels alone.
5. Port the existing Wayland virtual-pointer behavior and X11/portal adapters, then calibrate actual platform castling/promotion menus. Move offsets/humanization and pointer relocation remain to be ported; current dispatch uses square centers.
6. Implement Android capture foreground service, AccessibilityService/JNI gestures and floating controls.
7. Finish log-folder shortcuts, UI lifecycle/stop/recovery, offline packages and platform acceptance.

See `../docs/automation-plan.md` and `../docs/android-pc-migration-plan.md` for the full scope and release gates. This is not yet a complete replacement. The Windows Rust runtime DLL and manual/Auto pipeline are built and exercised, but no complete phone or desktop app binary has been built, and the Flutter window behavior has not been observed on a real desktop.

## Deliberate differences recorded during the port

* Engine reads use real receive deadlines and drain stderr; a silent subprocess no longer defeats a timeout by blocking `readline`.
* Latest centipawn/mate evaluation replaces an earlier score. It is not reported as a confirmed game outcome by the native service.
* Missing kings, malformed FEN and multi-line commands are rejected before starting/searching; malformed or missing updated-FEN responses are errors rather than silently continuing to input.
* Existing `setoption` configuration lines remain supported. Arbitrary commands in the options file are rejected, and an existing file is never overwritten with defaults.
* Stockfish's `d`/`Fen:`/`Checkers:` output contract is retained for updated positions, matching Python. Full rules-library position application has not replaced it yet.
* Refined search stops with an error after 64 inferences per observation, preventing an excessive number of false board candidates from stalling capture. Frame sizes and resize intermediates are capped at 64 megapixels.
* The controller re-observes before input and stops on a changed position, capture bounds or board geometry; a dispatch observation older than three seconds is rejected. Geometry tolerates up to two detector pixels (0.25 pixels of square size) of jitter.
* A dispatched move is never repeated solely because verification failed. Expected engine FEN stays separate from confirmed history. The Python unverified-success option and speculative history update are intentionally not retained.
* Promotion candidate discovery retains Python's mapping/filter/sort contract. Actual selection additionally requires four distinct aligned menu choices near the promotion destination; ordinary detected pieces alone do not authorize a tap. Only one menu tap is sent, then the exact requested promotion must appear in a fresh board observation.
* Auto does not interpret the detector's supplied active-color field as turn detection. It requires a verified baseline and a stable placement reachable by one legal opponent move. Stockfish's depth-one `go perft 1` and `d` output provide legal transitions and full FEN metadata; malformed/unsupported output pauses the job. Castling rights lost after the baseline are never regained merely because pieces return to their initial squares.
* Castling controls affect the analysis position separately from canonical history. Turning a checkbox off does not itself erase a still-legal right, so it can be enabled later; actual king/rook moves or rook captures still remove rights through Stockfish. Predicted analysis FEN and visually confirmed canonical FEN can therefore have different castling fields.
