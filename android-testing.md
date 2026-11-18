# Android build and later device checks

Commands and output paths in this guide are relative to the Rust project root, the folder containing `app/`, `native/` and `tool/`.

Android has a Kotlin MediaProjection foreground service, accessibility gesture service and movable controls connected to the same Rust session/controller used on desktop. The ARM64 engineering APK has passed the limited physical-phone checks below; broader device acceptance remains unfinished.

Android packages the exact `assets/models/chess_detection.onnx` used by Python. The build generates its SHA-256 alongside the model. Startup reuses only matching app-private copies and atomically replaces older/corrupt copies; failed checksum/copy/rename stops setup instead of loading a stale model. The existing NNUE installer shares this path. Run `:app:testDebugUnitTest` for host checks of first install, reuse, upgrade, corruption repair and failed/interrupted installation; these do not require ADB.

## Build

Start with the [complete Windows-host Android build guide](docs/BUILDING.md#android-arm64-apk-built-on-windows) for SDK/JDK installation, environment variables, engine preparation, debug/release-mode commands and ADB installation.

Use JDK 17/21, Flutter 3.38.6, Rust, Android SDK 36, NDK 28.2.13676358 and CMake/Ninja 3.22.1. The current minimum is API 24 and only `arm64-v8a` is packaged. This minimum is a build setting, not a tested-device support claim.

From the Rust project root on Windows:

```powershell
rustup target add aarch64-linux-android
./tool/prepare_android.ps1 -AndroidSdk C:/Android/Sdk
cd app
flutter build apk --debug --target-platform android-arm64
```

Set `JAVA_HOME` to the working JDK and add its `bin` to PATH. `android/local.properties` supplies the SDK/Flutter locations. The preparation script downloads a pinned official Stockfish 19 archive and the hash-checked release NNUE file, then builds unmodified sources with the NDK. Baseline ARMv8 and optional ARMv8.2 dot-product PIE executables have 16 KB load alignment; the original downloaded prebuilt executable is not packaged. Native CPU features select the optimized build where supported. Startup failure retries the baseline. Both engines share a single NNUE file, verified and copied to app-private storage on a background setup thread. GPL license/source information is included in APK assets. CMake switches follow the release Makefile. The inspected official Stockfish 19 ARM64 prebuilt has 4 KB load segments and an Android API 29 note, so it does not meet this app’s API 24 / 16 KB target; the pinned release source is rebuilt without modifying its C++ files.

Gradle builds Rust, copies engines/model/networks and includes ONNX Runtime Android 1.23.2 from Maven. The Rust binding uses its compatible C API rather than the Java inference wrapper. Native libraries are extracted at installation so engines run from `nativeLibraryDir`, not a writable downloaded-executable directory. Stockfish's working directory contains the shared default NNUE files. Model/config live under app-private storage; phone defaults use 128 MB Hash and two engine threads. Existing config files are preserved. Engine updates currently require an updated APK; the desktop executable downloader is intentionally unavailable on Android.

The standard Windows MSVC Rust host has now built the Android debug APK successfully without the older GNU helper setup. Gradle derives the Android target linker from the configured SDK/NDK. A GNU host remains an optional alternative: select `-PrustToolchain=stable-x86_64-pc-windows-gnu` (or `ORG_GRADLE_PROJECT_rustToolchain`) and use the host linker/dlltool setup in the engineering README. Native dependencies are cached under ignored `native/target/`; they are not committed binaries.

Debug APK: `app/build/app/outputs/flutter-apk/app-debug.apk`. This is an engineering build. Release signing, full distribution/source-offer review, sustained-play checks and final support claims remain unfinished.

The standard MSVC host also passed `flutter build apk --release --target-platform android-arm64`, producing `app-release.apk` (about 99 MB). It retains version 3.0.0-beta.1/build 2 and currently uses debug signing for local tests. Run the normal Flutter command when changing build modes: `--no-pub` can leave stale development-plugin registration and fail release compilation with this SDK. Physical-phone results below were collected with the debug build; release-mode device/performance acceptance remains pending.

## Phone flow

1. Open the dashboard and choose color/settings.
2. Enable **ChessPilot touch control** in the system accessibility settings. The service declares gesture capability and does not retrieve accessibility window content.
3. Tap **Share entire display**. Grant the per-session capture consent; Android 14+ requests the default full display. Notification permission is requested where needed so Play / Stop moves / Exit are visible there too.
4. Switch to the board. A draggable 48 dp bubble appears. Tap to expand; drag its bubble/header to reposition. The panel contains Play / Auto / Stop and Exit; tap its status header to return to settings. While busy, the collapsed bubble becomes a one-tap Stop button.
5. On your turn, enable Auto directly and confirm it plays and visually verifies the first move before waiting for the opponent. Also check resuming Auto after a verified manual move. Settings/turn/history remain owned by Rust. Reopening the dashboard pauses automation and hides the overlay. Dragging or configuration changes pause it too; resume deliberately.
6. Screen-sharing stop, screen lock, display size/rotation changes or accessibility loss invalidate capture/history. Restart capture rather than reusing the projection token. Backgrounding/recreating the Flutter activity does not create another native session. Process death starts stopped.

The overlay is an accessibility window, so it needs no separate general overlay permission. It stays within system-bar/cutout insets and remembers an edge/relative vertical position. Larger text stacks the action buttons vertically. Rust masks its actual pixel bounds, rejects covered boards and rejects a gesture path intersecting the controls. Moving/resizing/removing controls discards old frames; input waits for measured bounds and a fresh observation.

Android sessions start at depth 10 for faster analysis; the phone slider allows depth 8 when less search is needed. Higher depths remain selectable. Desktop keeps its depth 15 default and 10–30 range. Capture, animation settling and move-verification safeguards are unchanged; lowering search depth does not eliminate those costs.

The updated engineering APK was installed on the same physical phone: the fresh dashboard displayed depth 10, and selecting the slider minimum displayed depth 8 without a native validation error. Flutter tests (13), analysis, native session tests and Android assembly/unit tests passed. A new end-to-end move latency measurement at these settings remains pending.

Capture timestamps remain real. If a static display has stopped producing frames, Rust requests a fresh buffer and the service reattaches the existing virtual display's surface; it does not create a second virtual display or relabel an old image. A missing/old/blocked frame stops the move. Accessibility callbacks carry capture/action IDs, and missing completion keeps the in-flight action owned until a callback or teardown. OS delivery still requires visual verification.

## Physical-phone checks (17 November 2026)

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

## Remaining device checks

Still check black orientation, castling, all promotions, Stop during gesture delivery, sustained Auto with no duplicate moves, static-screen refresh under long idle, capture-consent revocation and permission denial/recovery. Cover portrait/landscape and rotation, cutouts, gesture navigation, magnification rejection, large text, secure screens, activity recreation and process death. Include both 4 KB and 16 KB page-size devices/images and two physical phones of different performance. Release-mode memory/performance, sustained-play and full security acceptance remain open. Do not infer these results from the limited run above, compilation or broker tests.

The compact surface requirements are in [the phone overlay plan](docs/phone-overlay-plan.md). Linux live testing remains separately deferred in [linux-testing.md](linux-testing.md).
