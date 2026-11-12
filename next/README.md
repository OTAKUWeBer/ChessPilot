# Flutter / Rust migration — work in progress

Branch: `rust`. Python v2.3.1 remains the runnable reference in `src/`.

## Implemented and checked

* Flutter Windows/Linux/Android scaffold; green/dark selection and play screens.
* 380×520 desktop client area and native always-on-top request on Windows/Linux. Wayland window managers may ignore keep-above; real desktop validation is pending.
* Rust configuration, board/square geometry, move notation, FEN expansion/flipping, placement-based castling compatibility, game state and normal/castling/promotion/en-passant verification.
* Pure detection-to-FEN port and model class/promotion mappings; native ONNX inference is still pending.
* Frozen Python parity cases for 128 orientation mappings, 128 geometry points and eight castling combinations, plus Rust domain tests. Invalid inputs return errors instead of Python's invalid-square-to-a8 fallback.
* Flutter test checks the 380×520 layout, color selection, keyboard depth adjustment and Escape. Move/Auto controls are disabled until the real pipeline is connected.
* Persistent Rust Stockfish service: UCI handshake, config options, depth/evaluation progress, best move, updated FEN, stop/cancel deadlines, stderr draining, process cleanup and restart on the next request after failure.
* Resource lookup and portable/user config creation preserve existing user files. Engine options and FEN input are validated before entering the UCI protocol.
* Subprocess fixtures cover silent/crashed/unresponsive engines, invalid output, stderr flooding, cancellation, and persistence. The local real Stockfish passed opening/checkmate analysis and persistent-process reuse.

## Commands

```powershell
cd next/app
flutter pub get
flutter test
flutter analyze
flutter run -d windows
```

With a normal native Rust toolchain:

```powershell
cargo test --manifest-path next/native/Cargo.toml
```

The real-engine integration test is explicit, so it cannot silently pass without an engine:

```powershell
$env:CHESSPILOT_STOCKFISH = (Resolve-Path src/stockfish.exe).Path
cargo test --manifest-path next/native/Cargo.toml --workspace -- --include-ignored
```

On Linux set `CHESSPILOT_STOCKFISH` to the actual native `stockfish` executable. On this workstation use the GNU linker settings below for both commands.

This workstation lacks the Visual C++ desktop workload. Rust tests can currently run with its already-installed GNU toolchain and bundled LLVM linker:

```powershell
$rustGnuRoot = (rustup run stable-x86_64-pc-windows-gnu rustc --print sysroot)
$env:RUSTFLAGS = "-C linker=$($rustGnuRoot.Replace('\','/'))/lib/rustlib/x86_64-pc-windows-gnu/bin/rust-lld.exe -C linker-flavor=ld.lld -C link-self-contained=yes"
cargo +stable-x86_64-pc-windows-gnu test --manifest-path next/native/Cargo.toml --offline
```

Flutter desktop compilation still needs Visual C++ Build Tools; Android compilation needs a working JDK and verified SDK license/setup. Neither has been installed or modified by this migration.

## Next work, in order

1. Extend differential fixtures for remaining domain/detection behavior, preserving current valid-input contracts. Record intentional deviations individually.
2. Finish resource installation/download and rotating file logging; the persistent desktop Stockfish service and resource/config resolution are ported and tested.
3. Connect the Rust runtime to Flutter; move settings/session ownership out of temporary Dart UI state. No duplicated engine or chess logic in Dart.
4. Port capture/ONNX preprocessing, model inference and normal/refined search using the existing model.
5. Port native Windows automation and existing Wayland virtual-pointer behavior, add X11/portal adapters, then verify moves/castling/promotion through actual frames.
6. Implement Android capture foreground service, AccessibilityService/JNI gestures and floating controls.
7. Finish shortcuts, UI lifecycle/stop/recovery, offline packages and platform acceptance.

See `../docs/automation-plan.md` and `../docs/android-pc-migration-plan.md` for the full scope and release gates. This is not yet an automation-capable replacement. No phone or desktop binary has been built, and native window behavior has not been observed on a real desktop.

## Deliberate differences recorded during the port

* Engine reads use real receive deadlines and drain stderr; a silent subprocess no longer defeats a timeout by blocking `readline`.
* Latest centipawn/mate evaluation replaces an earlier score. It is not reported as a confirmed game outcome by the native service.
* Missing kings, malformed FEN and multi-line commands are rejected before starting/searching; malformed or missing updated-FEN responses are errors rather than silently continuing to input.
* Existing `setoption` configuration lines remain supported. Arbitrary commands in the options file are rejected, and an existing file is never overwritten with defaults.
* Stockfish's `d`/`Fen:`/`Checkers:` output contract is retained for updated positions, matching Python. Full rules-library position application has not replaced it yet.
