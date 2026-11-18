# ChessPilot 3.0.0-beta.1 — Flutter / Rust engineering guide

Branch: `rust`. Start with the [product README](../README.md) for setup, defaults and platform status. The runnable Python reference is on [main](https://github.com/OTAKUWeBer/ChessPilot/tree/main). The new app does not bundle or run Python: Flutter renders the UI, Rust owns the pipeline, and native ONNX Runtime loads the same model file. Python comparison tools are development-only.

## Implemented and checked

Build/test commands and output paths in this guide start in this Rust project root, the folder containing `app/`, `native/` and `tool/`. Historical Python reference paths refer to the separate main branch.

* Flutter Windows/Linux/Android scaffold; green/dark selection and play screens.
* 380×520 baseline desktop client area, dampened high-resolution sizing and monitor-bounded minimums, plus native always-on-top requests on Windows/Linux. Shared sizing has C++ checks. Wayland window managers may ignore keep-above; The maintainer reports working Linux gameplay and castling; broader desktop/monitor coverage remains open. Windows native size/topmost/close checks pass through the SDK integration runner.
* Rust configuration, board/square geometry, move notation, FEN expansion/flipping, placement-based castling compatibility, game state and normal/castling/promotion/en-passant verification.
* Native ONNX inference with a persistent session, Pillow-compatible RGB Lanczos/letterbox preprocessing, model-output validation, detection-to-FEN and class/promotion mappings.
* Normal inference automatically retries board crops and overlapping tiles when a board is unreadable; crop coordinates are restored to the captured frame. Promotion detection retains the raw, unrefined path. Cancellation and a 64-inference limit bound each observation.
* Frozen Python vision fixtures check four complete preprocessing tensors byte for byte. Real native ONNX tests match all box coordinates/classes and FENs for normal capture, small-board recovery and an unreadable board.
* Frozen Python parity cases for 128 orientation mappings, 128 geometry points and eight castling combinations, plus Rust domain tests. Invalid inputs return errors instead of Python's invalid-square-to-a8 fallback.
* Flutter tests check the 380×520 layout, color selection, mode/delay/depth/castling shortcuts, Play readiness, Auto start/stop and Escape. Windows Play and Auto are connected to the native controller. Auto can play the initial move for the selected color, then wait for legal opponent replies.
* Persistent Rust Stockfish service: UCI handshake, config options, depth/evaluation progress, best move, updated FEN, stop/cancel deadlines, stderr draining, process cleanup and restart on the next request after failure.
* Verified mate-in-one and terminal mate/stalemate produce a normal game-result panel with New game. Play/Auto stay disabled until a new game is selected. Position failures remain in the game controls; the engine restarts on the next request without reopening setup.
* Resource lookup and portable/user config creation preserve existing user files. Engine options and FEN input are validated before entering the UCI protocol.
* Every desktop launch checks for Stockfish beside the app. If missing, a compact, cancellable downloader opens before the controls and installs the engine into the same app folder. Native CPU detection selects a compatible official build, checks archive size/SHA256, extracts only the engine, checks executable architecture and completes a real UCI handshake before installing without replacing existing files. Verified downloads are cached; engines placed beside the app, explicit engine paths and offline setup still work. Unwritable app folders report an error rather than relocating the engine. Stockfish uses the CPU.
* Native diagnostics records engine, capture, controller and frontend errors through a bounded asynchronous logger. Logs rotate at 5 MiB with five backups, preserve the Python log and escape control characters. Help opens diagnostics/system information and the desktop log folder; Android can share recent logs through its system chooser.
* The timing ledger in [Python timing parity](python-timing-parity.md) accounts for all 76 Python sleep/single-shot calls, including explicit differences and remaining work.
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
* Linux X11 and wlroots adapters are now connected to the same Play/Auto controller. X11 uses Rust protocol bindings for capture, primary-monitor selection and XTEST input. Wayland preserves grim plus virtual-pointer input, with PPM capture, full-layout coordinates, exact fragmented reads, bounded replies, fresh callback IDs and held-button cleanup.
* Windows/Linux [hosted CI](https://github.com/OTAKUWeBer/ChessPilot/actions/runs/44147469834) passed complete desktop bundles, native/Flutter regressions and real ONNX/refined-search parity. Linux also passed an Xvfb X11 capture/capability probe. Protocol tests use synthetic inputs/a fake compositor. The maintainer reports working Linux gameplay and castling; broader Wayland/compositor coverage remains open; see [Linux setup and checks](../linux-testing.md). GNOME/KDE Wayland portal input is unfinished.
* Android MediaProjection foreground service, callback-confirmed accessibility tap/drag and the shared Rust Play/Auto pipeline are connected. The process owns one session across Flutter activity recreation. Consent, lock, source rotation/resize and accessibility loss invalidate capture/history. Static frames request a new surface buffer; old pixels are not relabeled as fresh.
* Phone controls use a draggable 48 dp app-logo bubble or shallow 216 × 111 dp panel with readable metadata/status, Play / Auto / Stop / Exit and saved edge docking. Busy mode replaces the logo with a red Stop control. Large text stacks buttons; system-bar/cutout insets bound placement. Dragging/opening the dashboard pauses automation. Rust masks controls, rejects covered boards and rejects intersecting gesture paths; input waits for measured bounds. Android starts at depth 10 and permits 8–30; desktop retains depth 15 and 10–30. See [phone overlay design](phone-overlay-plan.md).
* Android ARM64 packaging builds Rust and baseline/dot-product Stockfish 19 PIE from pinned official sources/networks. Native CPU features select the optimized engine; startup failure retries the baseline. Both share one hash-checked NNUE network installed on a setup thread. The exact Python model and ONNX Runtime Android 1.23.2 are included; startup checks replace stale/corrupt model copies and preserve configuration. Broker, asset-installation and Flutter channel/session tests pass. On an Android 14 RMX3392, real Brave/Lichess bot-game checks passed Drag/Click, four Auto responses, Stop, overlap rejection, lock invalidation and Exit cleanup. Repeat-launch cleanup and private-component access checks also passed. Full device/security/memory acceptance remains open; see [Android evidence and remaining checks](../android-testing.md).
* Shared manual/Auto/castling dispatch and promotion taps preserve Python's random offsets (16 px moves, 8 px promotion choices), scaled to square size and bounded further for tiny boards. Deterministic recording tests retain exact centers; separate checks cover offset bounds and invalid samples.
* Desktop CMake builds Rust and installs the runtime, model, pinned CPU ONNX Runtime and licenses into the Flutter bundle, including MSVC runtime DLLs on Windows. The complete Windows release now compiles with zero warnings/errors. Thirteen Flutter/native-client tests pass against its MSVC release DLL, including real Stockfish analysis. Relocated resource lookup and Python normal/zoom/failure inference fixtures pass. Normal desktop exit awaits native cleanup; repeated close calls share one operation. A real Windows integration test now checks startup/rendering, compact setup/main handoff, always-on-top, native coordinate mapping and WM_CLOSE waiting for the actual Stockfish child to exit. See [desktop builds](../desktop-building.md).
* Touch users can return to color selection without a keyboard while retaining depth/delay/mode. The small-screen flow has a large-text check. Windows/Linux window icons and Android legacy/adaptive launchers reuse the existing ChessPilot artwork.
* Manual Play supplies an optional native-window return target. After a visually verified move, Windows/X11 return the pointer to Play without clicking, while the same native worker still owns input. Window position is queried at return time; hidden/resized/unowned windows, held mouse buttons and Stop skip return. Auto/Android omit it. Flutter tests cover pending mapping/Stop/duplicate requests; an owned Windows target verifies actual return after moving the window and zero extra clicks. Windows runner mapping has been checked; live X11 mapping remains unverified.

* Windows packaging now has a single setup EXE using the existing Inno Setup compiler, with per-user installation, shortcuts and uninstall. The builder verifies version/architecture, required payload and the model hash. Installer files exclude the developer's engine/config/cache/logs, and updates preserve user-created data. An isolated identity checks install hashes, Start menu registration, reinstall preservation and uninstall; CI publishes the setup separately. See [Windows installer](../packaging/windows/README.md).

## Commands

For clean-machine prerequisites and separate Windows, Linux/Arch and Android recipes, use the [complete build guide](BUILDING.md). The older GNU-host commands below remain alternatives; the standard MSVC host now also builds Android without helper binaries.

Build the Rust runtime library first with the platform's normal host toolchain, then start Flutter. The GNU settings below are an optional alternative:

```powershell
cargo build --manifest-path native/Cargo.toml -p chesspilot-runtime
cd app
flutter pub get
flutter test
flutter analyze
flutter run -d windows
```

In development the Dart loader finds `native/target/debug/chesspilot_runtime.dll` (or `libchesspilot_runtime.so` on Linux). `CHESSPILOT_LIBRARY_PATH` can select an explicit library for tests. Desktop CMake packages native components after running the asset-preparation command in [desktop builds](../desktop-building.md); Android Gradle packages its native components. A missing native component is reported rather than replaced by simulated state. The real-engine Dart test requires `CHESSPILOT_STOCKFISH`, just like the native integration test below.

Flutter startup initializes the engine, model and capture on the Rust worker. In Windows development, model/runtime lookup includes `assets/models/chess_detection.onnx` and the prepared ONNX Runtime under `native/target/desktop-assets/`; release lookup expects native assets beside the executable. Play becomes available after initialization and color selection. Capture initialization can be retried independently of a ready engine; its retry control remains available while capture is unavailable even if the displayed error clears. UCI startup and readiness waits check cancellation every 25 ms instead of blocking Stop for the full handshake timeout. The runtime still uses the supplied player color as the active side, matching Python; the user must request a move on that side's turn.

Enable Auto with its checkbox or `A` on your turn. With no confirmed history, the same native worker plays and visually verifies the initial move, matching Python; an existing baseline resumes from its known active side. It then waits for one legal opponent reply, analyzes and plays once. `A`, Stop or Escape stops it; settings/color changes also cancel it. Stopping while waiting preserves the baseline. Uncertain input stops the worker and invalidates history. A new explicit Play or Auto action can establish a fresh verified baseline; it never retries input automatically. Escape and reselect the color to clear history when switching games/boards. Initial manual metadata retains Python's placement-based assumptions; the screenshot cannot recover earlier castling/en-passant history. Once a baseline exists, legal transitions preserve metadata instead of reinferring it each tick. Early manual Play waits for one legal opponent reply rather than dropping history and queueing a premove. Position/history mismatches invalidate the rejected baseline so the next explicit Play can resynchronize. Verification allows up to two seconds of fresh read-only observations for delayed redraws; it never repeats input.

With a normal native Rust toolchain:

```powershell
cargo test --manifest-path native/Cargo.toml
```

The real-engine and ONNX integration tests are explicit, so they cannot silently pass without native assets:

```powershell
$env:CHESSPILOT_STOCKFISH = (Resolve-Path app/build/windows/x64/runner/Release/stockfish.exe).Path
$env:CHESSPILOT_MODEL = (Resolve-Path assets/models/chess_detection.onnx).Path
$env:CHESSPILOT_ORT = (Resolve-Path native/target/desktop-assets/windows-x64/onnxruntime.dll).Path
$env:CHESSPILOT_DESKTOP_TEST = '1'
cargo test --manifest-path native/Cargo.toml --workspace -- --include-ignored --skip real_https_download_and_cpu_install_pass_uci --skip default_startup_installs_in_the_app_folder_and_reuses_it_on_the_next_launch_check --skip relocated_bundle_resolves_default_assets_without_checkout_paths --skip actual_reported_image_matches_python
```

The command excludes the separately enabled network installer, relocated-bundle and private-image checks. To exercise the isolated HTTPS/download/cache/UCI path, set `CHESSPILOT_DOWNLOAD_TEST=1` and run `cargo test --manifest-path native/Cargo.toml --test installer real_https_download_and_cpu_install_pass_uci -- --ignored`. Run the bundle check separately as documented in [desktop builds](../desktop-building.md), and the private-image check as documented in the [vision fixtures](../native/runtime/tests/fixtures/vision/README.md).

For isolated checks set `CHESSPILOT_LOG_DIR` and `CHESSPILOT_DATA_HOME` to absolute temporary directories. Normal use retains portable configuration or the OS user directory. Windows logs use `%LOCALAPPDATA%/ChessPilot/logs`; Linux prefers `$XDG_STATE_HOME/chesspilot/logs`, then `$XDG_DATA_HOME/chesspilot/logs`, then `~/.local/share/chesspilot/logs`. Android uses app-private `files/logs`. A logging failure remains visible in diagnostics and does not prevent Stop.

On Linux set these paths to the native `stockfish`, model and ONNX Runtime shared library. The local Windows test reuses ONNX Runtime 1.20's DLL from the existing environment; the Rust runtime never starts Python. Release bundles must ship a compatible native library. On this workstation use the GNU linker settings below for both commands.

`CHESSPILOT_DESKTOP_TEST=1` explicitly enables real interactive Windows tests: an owned colored window for adapter checks and an owned temporary full-screen chessboard for complete native pipeline checks. They refuse input if another window covers their target and restore the cursor afterward. Run on an unlocked desktop with the mouse released; sandbox desktop restrictions may require running the tests outside the sandbox. No desktop image is saved. Unit tests do not need desktop access, the model or an engine.

The approved Visual C++ Build Tools installation is now under `X:/BuildTools/VisualStudio`; the earlier C: Build Tools instance was uninstalled. Downloads/cache/temp use X:, while Microsoft's SDK installer retains Windows Kits under C:. Normal MSVC Rust and Flutter Windows builds now work. The GNU toolchain remains an alternative for the earlier checks:

```powershell
$rustGnuRoot = (rustup run stable-x86_64-pc-windows-gnu rustc --print sysroot)
$env:RUSTFLAGS = "-C linker=$($rustGnuRoot.Replace('\','/'))/lib/rustlib/x86_64-pc-windows-gnu/bin/rust-lld.exe -C linker-flavor=ld.lld -C link-self-contained=yes -C dlltool=C:/Android/Sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-dlltool.exe"
cargo +stable-x86_64-pc-windows-gnu test --manifest-path native/Cargo.toml --offline
```

The Windows release is `app/build/windows/x64/runner/Release/chesspilot.exe`; distribute its whole directory. Android compilation works with a local JDK 21 under ignored `native/target/android-tools/`; SDK/NDK dependencies are installed and the ARM64 debug APK builds. No machine-wide Java setting was changed.

## Next work, in order

1. Extend differential fixtures for remaining domain/detection behavior, preserving current valid-input contracts. Record intentional deviations individually.
2. Extend Android engine/performance acceptance beyond the tested ARM64 phone. Optional ONNX acceleration must prove equivalent results and lower end-to-end latency before activation.
3. Finish release/clean-install and additional-monitor acceptance. Windows packaged window/WM_CLOSE cleanup and Android Exit teardown have passed. Live Linux window behavior remains a device check.
4. Finish recovery/calibration and sustained-play acceptance for the connected Windows manual/Auto pipeline. It now reconciles a legal immediate opponent reply during visual verification; complete history before the initial verified baseline is still unavailable from pixels alone.
5. Add portal capture/control for Wayland compositors without wlroots protocols, then calibrate actual platform castling/promotion menus. X11 and the existing wlroots path are implemented; the maintainer reports working Linux gameplay and castling. More compositor/monitor combinations remain to be tested. Windows/X11 pointer return and bounded move/promotion offsets are implemented; Wayland pointer return is omitted because the app surface has no reliable global position.
6. Extend Android checks to black orientation, physical castling/all promotions, Stop during a delivered gesture, rotation/large text, permission denial/revocation, long runs and another phone. Finish release-mode performance/memory checks and distribution/signing.
7. Finish UI lifecycle/stop/recovery, offline packages and platform acceptance; log-folder/share shortcuts are connected.

See `../docs/automation-plan.md` and `../docs/android-pc-migration-plan.md` for scope and release gates. This beta does not claim complete platform acceptance. The Windows runtime/manual/Auto pipeline and Flutter startup/cleanup checks pass; Android capture, ONNX, Stockfish and actual moves now have limited physical-phone evidence. Broader target-site, monitor/device and long-run acceptance remains pending. Signed stable distribution and broader Linux compositor/monitor acceptance are unfinished.

## Deliberate differences recorded during the port

* Engine reads use real receive deadlines and drain stderr; a silent subprocess no longer defeats a timeout by blocking `readline`.
* Latest centipawn/mate evaluation replaces an earlier score. It is not reported as a confirmed game outcome by the native service.
* Missing kings, malformed FEN and multi-line commands are rejected before starting/searching; malformed or missing updated-FEN responses are errors rather than silently continuing to input.
* Existing `setoption` configuration lines remain supported. Arbitrary commands in the options file are rejected, and an existing file is never overwritten with defaults.
* Stockfish's `d`/`Fen:`/`Checkers:` output contract is retained for updated positions, matching Python. Full rules-library position application has not replaced it yet.
* Refined search stops with an error after 64 inferences per observation, preventing an excessive number of false board candidates from stalling capture. Frame sizes and resize intermediates are capped at 64 megapixels.
* The controller re-observes before input and stops on a changed position, capture bounds or board geometry; a dispatch observation older than three seconds is rejected. All board corners tolerate detector jitter up to 4% of a square, bounded to 2–6 pixels; capture bounds still must match. This accepts the recorded 3-pixel wobble without accepting a relocated/rescaled board.
* A dispatched move is never repeated solely because verification failed. Expected engine FEN stays separate from confirmed history. The Python unverified-success option and speculative history update are intentionally not retained.
* Promotion candidate discovery retains Python's mapping/filter/sort contract. Actual selection additionally requires four distinct aligned menu choices near the promotion destination; ordinary detected pieces alone do not authorize a tap. Only one menu tap is sent, then the exact requested promotion must appear in a fresh board observation.
* Auto does not interpret the detector's supplied active-color field as turn detection. After its initial verified move, it requires a stable placement reachable by one legal opponent move. Stockfish's depth-one `go perft 1` and `d` output provide legal transitions and full FEN metadata; malformed/unsupported output pauses the job. Castling rights lost after the baseline are never regained merely because pieces return to their initial squares.
* Castling controls affect the analysis position separately from canonical history. Turning a checkbox off does not itself erase a still-legal right, so it can be enabled later; actual king/rook moves or rook captures still remove rights through Stockfish. Predicted analysis FEN and visually confirmed canonical FEN can therefore have different castling fields.
* Optional pointer return follows the complete visually verified manual transaction, rather than moving to Play between physical gestures and verification. It never clicks Play. Wayland retains the working grim/virtual-pointer chess pipeline but omits Python's click-to-return helper; GTK does not supply a reliable global app-window position on Wayland. Return failures are logged and do not discard a verified chess move.
