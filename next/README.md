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
* Flutter test checks the 380×520 layout, color selection, keyboard depth adjustment and Escape. Move/Auto controls are disabled until the real pipeline is connected.
* Persistent Rust Stockfish service: UCI handshake, config options, depth/evaluation progress, best move, updated FEN, stop/cancel deadlines, stderr draining, process cleanup and restart on the next request after failure.
* Resource lookup and portable/user config creation preserve existing user files. Engine options and FEN input are validated before entering the UCI protocol.
* Subprocess fixtures cover silent/crashed/unresponsive engines, invalid output, stderr flooding, cancellation, and persistence. The local real Stockfish passed opening/checkmate analysis and persistent-process reuse.
* Flutter now uses the real Rust runtime DLL through a length-delimited C ABI. Rust owns settings, color/session state, engine work and progress; Dart renders snapshots. Engine operations run on a native worker, and changing color/Stop invalidates old results.
* Native buffer ownership, invalid requests, transactional settings and isolated sessions have tests. Dart integration tests exercise the compiled library and local Stockfish, not a mocked backend.
* Native Windows primary-monitor GDI capture and `SetCursorPos`/`SendInput` mouse delivery. Per-thread physical-pixel DPI context is restored after each operation; capture retains its signed monitor origin and timestamp.
* Windows click/drag sequencing preserves Python's rounding, intermediate point and timing. Stop/failure attempts button release, and delivery errors distinguish a move not dispatched from uncertain delivery. Recording tests inject cancellation/failure throughout each sequence.
* A real Windows integration test creates its own temporary window, checks captured RGB colors/top-down rows, repeated-capture GDI resource cleanup, and received click/drag events. It restores the cursor afterward. This proves adapter delivery, not chess move verification or full-app operation.

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

`CHESSPILOT_DESKTOP_TEST=1` explicitly enables a real interactive Windows test: it briefly creates a topmost colored target window and moves/clicks only inside that owned window. It refuses input if another window covers the target. Run it on an unlocked desktop with the mouse released; sandbox desktop restrictions may require running the test outside the sandbox. No desktop image is saved. Unit tests do not need desktop access, the model or an engine.

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
4. Connect the native Windows capture/observation and ONNX lifecycle to the session/UI. The shared observation function already feeds a captured RGB frame into normal/refined search and keeps its coordinate metadata; lifecycle/controller integration is still pending.
5. Connect tested Windows input to the move controller, port the existing Wayland virtual-pointer behavior and X11/portal adapters, then verify moves/castling/promotion through actual frames. Input offsets/humanization, cursor relocation and chess verification are not connected yet.
6. Implement Android capture foreground service, AccessibilityService/JNI gestures and floating controls.
7. Finish shortcuts, UI lifecycle/stop/recovery, offline packages and platform acceptance.

See `../docs/automation-plan.md` and `../docs/android-pc-migration-plan.md` for the full scope and release gates. This is not yet an automation-capable replacement. The Windows Rust runtime DLL is built and exercised, but no complete phone or desktop app binary has been built, and native window behavior has not been observed on a real desktop.

## Deliberate differences recorded during the port

* Engine reads use real receive deadlines and drain stderr; a silent subprocess no longer defeats a timeout by blocking `readline`.
* Latest centipawn/mate evaluation replaces an earlier score. It is not reported as a confirmed game outcome by the native service.
* Missing kings, malformed FEN and multi-line commands are rejected before starting/searching; malformed or missing updated-FEN responses are errors rather than silently continuing to input.
* Existing `setoption` configuration lines remain supported. Arbitrary commands in the options file are rejected, and an existing file is never overwritten with defaults.
* Stockfish's `d`/`Fen:`/`Checkers:` output contract is retained for updated positions, matching Python. Full rules-library position application has not replaced it yet.
* Refined search stops with an error after 64 inferences per observation, preventing an excessive number of false board candidates from stalling capture. Frame sizes and resize intermediates are capped at 64 megapixels.
