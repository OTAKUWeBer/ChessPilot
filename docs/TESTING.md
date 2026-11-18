# Testing and platform evidence

All commands start at the repository root unless stated otherwise. Build prerequisites and commands live in [BUILDING.md](BUILDING.md); end-user setup lives in [INSTALLING.md](INSTALLING.md). Recorded physical tests describe the build and device used at the time, not universal compatibility.

## Automated checks

```sh
dart tool/version.dart --check
dart --enable-asserts tool/tests/version_test.dart
cargo fmt --manifest-path native/Cargo.toml --all --check
cargo clippy --manifest-path native/Cargo.toml --workspace --all-targets --locked -- -D warnings
cargo test --manifest-path native/Cargo.toml --workspace --locked
```

After building the desktop runtime, run `flutter analyze` and `flutter test` from `app/`. `CHESSPILOT_LIBRARY_PATH` selects an explicit runtime library. Optional tests use `CHESSPILOT_STOCKFISH`, `CHESSPILOT_MODEL` and `CHESSPILOT_ORT`; each ignored test explains its prerequisites. Run input tests only against their owned, unobstructed fixture window.

## Windows and desktop packaging

### Isolated packaging check

The CMake fixture builds and installs the same native bundle rules without requiring a Flutter desktop executable:

```sh
cmake -S tool/tests/desktop_bundle -B native/target/bundle-check -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_INSTALL_PREFIX=/absolute/path/to/rust-root/native/target/bundle-check/install
cmake --build native/target/bundle-check
cmake --install native/target/bundle-check --component Runtime
```

Set `CHESSPILOT_BUNDLE_TEST` to the absolute installed fixture directory and run `cargo test --manifest-path native/Cargo.toml --test resources relocated_bundle_resolves_default_assets_without_checkout_paths -- --ignored`. The check relocates its own test executable into the fixture, verifies default model/runtime lookup and removes only that owned executable. It refuses paths outside `native/target`.

Set `CHESSPILOT_MODEL` to the installed model and `CHESSPILOT_ORT` to the installed ONNX Runtime library, then run `cargo test --manifest-path native/Cargo.toml --test vision actual_onnx_inference_and_zoom_search_match_reference -- --ignored`. This tests real normal/zoom/failure inference against reference fixtures. The Flutter client tests can use the installed DLL through `CHESSPILOT_LIBRARY_PATH`.

The complete Flutter Windows release compiles with MSVC 19.44 and Windows SDK 10.0.26100. Fifteen client/widget checks pass, including real Stockfish analysis, small-screen/large-text controls and Play remaining disabled while Auto is selected. The SDK integration runner also exercises the actual Windows window, bundled Rust/model/runtime, root-folder engine setup, compact downloader dimensions, exact main-window restoration, always-on-top flag, shortcuts, color/settings flow, native pointer mapping and WM_CLOSE cleanup. The test keeps the window alive just long enough to assert its real Stockfish child has exited and the native session is closed; it never dispatches chess input.

From the Rust project root, with native assets prepared:

```powershell
$env:CHESSPILOT_UI_TEST_OUTPUT = Join-Path (Get-Location) 'native/target/windows-ui'
$env:CHESSPILOT_DATA_HOME = Join-Path $env:CHESSPILOT_UI_TEST_OUTPUT 'data'
$env:CHESSPILOT_LOG_DIR = Join-Path $env:CHESSPILOT_UI_TEST_OUTPUT 'logs'
Remove-Item Env:/CHESSPILOT_LIBRARY_PATH -ErrorAction SilentlyContinue
cd app
flutter test integration_test/windows_app_test.dart -d windows
```

The runner must load its bundled DLL. A private 16 MB / one-thread config isolates this UI check; no user configuration is replaced. First use downloads Stockfish beside the generated Debug executable, later runs reuse it. The progress-layout fixture also checks the full downloader on warm runs. Only this app's Flutter surface is saved under ignored `target/windows-ui`; other desktop windows are not captured. The maintainer reports working Linux gameplay and castling; additional physical monitor/compositor combinations remain unverified. Limited Android phone results are recorded separately in [Android evidence](#android-physical-device-evidence).

### Recorded Windows checkmate (19 November 2026)

The rebuilt Windows release continued an existing Chess.com computer-bot game as White at depth 15. Auto played through the endgame to `Qg7#` (`g5g7`) in approximately 73 seconds. The browser displayed its checkmate result, ChessPilot displayed its green **Checkmate!** panel, Play/Auto were disabled, and the worker ended cleanly. This is one recorded session, not a general latency or reliability benchmark.

The result popup had previously hidden a pawn and shifted the detector's board outline, producing a geometry error after a successful mating move. The controller now accepts that limited occlusion only for an engine-confirmed mate in one with no legal reply, after two fresh matching observations retain every friendly piece and both kings without contradictory visible pieces. Regression cases cover both colors, a move that did not happen, missing friendly pieces/kings, stale or changed sources, non-mating scores and a single unconfirmed frame. The Rust suite (111 passed, 13 opt-in tests ignored), 15 Flutter tests, formatting and Clippy passed with the rebuilt native library; the live recording exercised the result-overlay verification path.

### Desktop CI

`.github/workflows/native.yml` builds Windows and Linux bundles with Flutter 3.38.6 and Rust 1.92.0. It verifies the tracked model checksum, native regressions, Flutter checks, actual ONNX/refined-search parity and an Xvfb X11 capture/capability probe. Linux artifacts are tarred to preserve executable permissions. Windows also builds the setup EXE, runs its isolated install/reinstall/uninstall check and uploads a separate installer artifact. The [earlier hosted run](https://github.com/OTAKUWeBer/ChessPilot/actions/runs/44147469834) passed both Windows and Linux jobs, including complete bundles, real model parity and the Xvfb probe. This does not replace physical Wayland, phone or live-game tests. Real-engine tests that require an explicit Stockfish path remain opt-in.

### Windows installer lifecycle


```powershell
./tool/test_windows_installer.ps1
```

This builds a separate **ChessPilot Installer Test** identity, installs into an ignored workspace directory with spaces in its path, checks DLL/model hashes and the Start menu shortcut, and confirms developer-local engine/config/cache files were excluded. It then creates user-owned sentinel files, reinstalls, verifies their contents, uninstalls and checks cleanup/preservation. It never launches the app or downloads Stockfish. The test refuses an existing test registration rather than modifying it. It does not install over a real ChessPilot installation. Logs and fixtures remain under `native/target/windows-installer-smoke/`.

The local smoke check passed. Fresh Windows-machine gameplay, SmartScreen reputation and signing acceptance remain separate from this packaging check.

### Linux installer lifecycle

`bash tool/test_linux_installer.sh` exercises an isolated fixture: install, upgrade with stale-library removal, engine/config/cache/custom-file preservation, launcher argument/environment handling, paths with spaces, uninstall/reinstall, and rejection of unrelated folders, concurrent setup, traversal and escaping symlinks. Passing a real `*-setup.run` additionally checks archive integrity, installs it under ignored `native/target`, starts the installed GTK launcher with `--help` under Xvfb, and runs the relocated native resource probe. It never plays a move or replaces a real ChessPilot installation.

The scripts and fixture install/update/uninstall plus an actual self-extracting fixture archive were checked on the Windows host through Git Bash. Native directory-symlink handling and the actual GTK/ELF installer build require Linux; the workflow includes those checks, but no successful Linux installer build is claimed from the Windows-only fixture run.

The portable fixture also runs the extensionless one-file app twice, checks argument forwarding, verifies temporary extraction cleanup, confirms there is no menu installation, and preserves engine/options in its user-data profile. Passing the second argument checks the real portable artifact's checksum, starts its GTK `--help` path and probes model/runtime discovery after extraction. Linux-native tests additionally check engine reuse through the portable profile override. CI's release build baseline is Ubuntu 22.04; this and the other listed distributions still require physical acceptance testing.

## Linux capture and gameplay

The maintainer reported working Linux gameplay and castling on November 18, 2026. CI checks the complete GTK bundle, real ONNX inference and an Xvfb capture/capability probe; broader compositor and monitor combinations remain separate.

### Probe capture without moving the mouse

From the Rust project root on the actual desktop:

```sh
CHESSPILOT_LINUX_CAPTURE_TEST=1 cargo test \
  --manifest-path native/Cargo.toml -p chesspilot-runtime \
  --test linux_live -- --ignored --nocapture
```

This opens the capture and input protocol connections, captures two frames and prints dimensions/origin. It sends no tap, drag or pointer motion and writes no screenshot. Keep the mouse button released during capability initialization.

### Interactive check

Use a local test board with the whole board visible and the ChessPilot window beside it. On X11, start on the primary monitor. On Wayland, capture uses the full layout at logical scale; custom compositor mapping of virtual devices can change input coordinates and needs calibration.

1. Choose the actual bottom-side color and request one move on that side's turn. Check both drag and click modes.
2. Confirm the visible board changes before `Move Played` appears; test both enabling Auto directly on your turn and resuming after a verified manual move.
3. Leave the board unchanged: Auto should wait. Make one legal opponent move: it should answer once. Stop it while waiting and during analysis.
4. Check both orientations, zoom, monitor/scale changes, captures, both castling sides and all promotions on the controlled board. An unreadable or changed source must pause rather than blindly repeat input.
5. Check that the desktop window starts at 380×520 and stays above other windows. Wayland may require a compositor window rule for keep-above.

The initial manual position still uses the selected color and placement-based initial history assumptions. Escape and reselect the color when changing games/boards. Linux build rules preserve the portable Stockfish/config/cache across rebuilds and replace generated Flutter assets. The complete GTK bundle builds in CI. Relocated Linux runtime behavior, sustained-play acceptance and portal support remain unverified or unfinished; Android device checks are separate.

## Android physical-device evidence

### Install a test build with ADB

Build the APK using [BUILDING.md](BUILDING.md#android-arm64-apk-built-on-windows). Enable Android Developer options/USB debugging, connect the phone and accept its debugging prompt. From the repository root:

```sh
adb devices
adb -s YOUR_DEVICE_SERIAL install -r app/build/app/outputs/flutter-apk/app-release.apk
```

Replace `YOUR_DEVICE_SERIAL` with the device reported by `adb devices`, then open ChessPilot on the phone and follow [Android first launch](INSTALLING.md#android). For a debug build, choose `app-debug.apk`. USB debugging/ADB is for development testing and is not required for end-user installation. Record the version/build and whether the APK is debug or release mode with the results.

### Physical-phone checks (17 November 2026)

An Android 14 RMX3392 (1080×2400, 480 dpi) installed and opened the engineering APK. The packaged Stockfish 19 completed its UCI/options handshake with the private 128 MB/two-thread config. The user enabled touch control and screen sharing. Phone help now replaces desktop keyboard instructions; setup explains the missing capability instead of repeating a generic warning.

The original accessibility overlay used `FLAG_SECURE`. On this phone, showing it caused screen capture to fail, including a zero-byte ADB screenshot. Removing that flag from our own controls restored screenshots and actual ONNX-to-Stockfish moves. The bridge still masks measured overlay bounds and refuses covered boards or intersecting input. Other applications' secure-window flags are unchanged.

On a controlled Brave/Lichess game against Stockfish level 1:

- Manual **Drag** played and visually verified `g1f3` at depth 15 in 3.18 seconds, including capture, detection, engine analysis, gesture and verification. Manual **Click** later verified `a4c2` at depth 12 in 2.74 seconds. These are individual observations, not a latency benchmark.
- Auto completed four verified responses with opponent replies during a roughly 28-second run. Manual Play stayed disabled during Auto. Stop ended the active worker about 36 ms after its recorded request during analysis.
- The movable 48 dp bubble and expanded 184 dp panel fit above the board in portrait. Deliberately covering the board rejected Play with “Move floating controls outside the chessboard” before engine/input execution. Moving it clear allowed the next explicit Play to succeed.
- Screen lock invalidated capture. Overlay Exit stopped projection, closed the Rust session and terminated the active Stockfish child. After teardown settled, the dashboard had no activity records, views or view roots, and no capture/session worker remained. The enabled accessibility service stayed bound and idle for a later launch.
- Main-process PSS fell from approximately 322 MiB after capture/analysis to 121 MiB after Exit settled. Two further dashboard launch/Exit cycles left no child processes or activity records, with approximately 148 and 150 MiB PSS. This is a short debug-build cleanup check; it does not establish leak freedom or release memory usage.
- External ADB-shell attempts to start the private projection service, start the accessibility service without its binding permission, and query the private diagnostics provider were denied. These limited component checks are not a full security audit.

The capture fix passed `:app:assembleDebug` and `:app:testDebugUnitTest` and was installed for these checks. Local screenshots/logs are kept only under ignored `native/target/phone-ui/`. Temporary browser-debug forwarding was removed afterward; device sleep settings were unchanged. Testing ended with ChessPilot stopped.

The follow-up overlay redesign uses the existing app logo in white inside the 48 dp bubble, decoded once at reduced resolution. Busy mode uses a separate Stop square on red. The normal expanded panel is about 216 × 111 dp: metadata and status have separate readable lines beside Collapse, with a divider and aligned Play / Auto / Stop / Exit controls below. Auto uses a selected background instead of a wider label; disabled controls are visibly muted. Every action keeps a minimum 48 dp target, and large text stacks the action row. On the same phone, screenshots confirmed the logo and normal-text panel, expansion/collapse and drag/docking were exercised, and Exit stopped capture, removed the dashboard and left no child process. Android assembly/unit tests and lint passed (zero errors; nine advisory warnings). Large-text/landscape acceptance and a new full gameplay run after this visual change remain pending.

Do not run the standard `uiautomator dump` during active capture/input testing: its default automation session suppresses other accessibility services, disconnecting ChessPilot and cancelling capture. This happened during this check. Use screenshots, or an instrumentation session explicitly using `UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES`.

### Remaining device checks

Still check black orientation, castling, all promotions, Stop during gesture delivery, sustained Auto with no duplicate moves, static-screen refresh under long idle, capture-consent revocation and permission denial/recovery. Cover portrait/landscape and rotation, cutouts, gesture navigation, magnification rejection, large text, secure screens, activity recreation and process death. Include both 4 KB and 16 KB page-size devices/images and two physical phones of different performance. Release-mode memory/performance, sustained-play and full security acceptance remain open. Do not infer these results from the limited run above, compilation or broker tests.

The current controls are described in [Android controls](ENGINEERING.md#android-controls). Linux evidence and remaining compositor coverage are recorded separately in [Linux evidence](#linux-capture-and-gameplay).
