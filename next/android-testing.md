# Android build and later device checks

Android now has a Kotlin MediaProjection foreground service, accessibility gesture service and movable controls connected to the same Rust session/controller used on desktop. The code builds as an ARM64 debug APK. Physical-phone testing is deferred until the user connects ADB; this document does not claim device acceptance.

## Build

Use JDK 17/21, Flutter 3.38.6, Rust, Android SDK 36, NDK 28.2.13676358 and CMake/Ninja 3.22.1. The current minimum is API 24 and only `arm64-v8a` is packaged. This minimum is a build setting, not a tested-device support claim.

From the repository root on Windows:

```powershell
rustup target add aarch64-linux-android
./next/tool/prepare_android.ps1 -AndroidSdk C:/Android/Sdk
cd next/app
flutter build apk --debug --target-platform android-arm64
```

Set `JAVA_HOME` to the working JDK and add its `bin` to PATH. `android/local.properties` supplies the SDK/Flutter locations. The preparation script downloads a pinned official Stockfish 17.1 archive and two hash-checked NNUE files, then builds unmodified sources with the NDK. Baseline ARMv8 and optional ARMv8.2 dot-product PIE executables have 16 KB load alignment; the original downloaded prebuilt executable is not packaged. Native CPU features select the optimized build where supported. Startup failure retries the baseline. Both engines share a single NNUE asset set, verified and copied to app-private storage on a background setup thread. GPL license/source information is included in APK assets. CMake switches follow the release Makefile.

Gradle builds Rust, copies engines/model/networks and includes ONNX Runtime Android 1.23.2 from Maven. The Rust binding uses its compatible C API rather than the Java inference wrapper. Native libraries are extracted at installation so engines run from `nativeLibraryDir`, not a writable downloaded-executable directory. Stockfish's working directory contains the shared default NNUE files. Model/config live under app-private storage; phone defaults use 128 MB Hash and two engine threads. Existing config files are preserved. Engine updates currently require an updated APK; the desktop executable downloader is intentionally unavailable on Android.

The current workstation uses the GNU Rust host because Visual C++ is unavailable. Select it with Gradle's `-PrustToolchain=stable-x86_64-pc-windows-gnu` (or `ORG_GRADLE_PROJECT_rustToolchain`) and use the host linker/dlltool setup from `README.md`. The Android linker is derived from the configured SDK/NDK. Native dependencies are cached under ignored `next/native/target/`; they are not committed binaries.

Debug APK: `next/app/build/app/outputs/flutter-apk/app-debug.apk`. This is an engineering build. Release signing, full distribution/source-offer review, sustained-play checks and final support claims remain unfinished.

## Phone flow

1. Open the dashboard and choose color/settings.
2. Enable **ChessPilot touch control** in the system accessibility settings. The service declares gesture capability and does not retrieve accessibility window content.
3. Tap **Share entire display**. Grant the per-session capture consent; Android 14+ requests the default full display. Notification permission is requested where needed so Play / Auto / Stop are visible there too.
4. Switch to the board. A draggable 48 dp bubble appears. Tap to expand; drag its bubble/header to reposition. The panel contains Play / Auto / Stop; tap its status header to return to settings. While busy, the collapsed bubble becomes a one-tap Stop button.
5. Play one visually verified manual move before enabling Auto. Settings/turn/history remain owned by Rust. Reopening the dashboard pauses automation and hides the overlay. Dragging or configuration changes pause it too; resume deliberately.
6. Screen-sharing stop, screen lock, display size/rotation changes or accessibility loss invalidate capture/history. Restart capture rather than reusing the projection token. Backgrounding/recreating the Flutter activity does not create another native session. Process death starts stopped.

The overlay is an accessibility window, so it needs no separate general overlay permission. It stays within system-bar/cutout insets and remembers an edge/relative vertical position. Larger text stacks the action buttons vertically. Rust masks its actual pixel bounds, rejects covered boards and rejects a gesture path intersecting the controls. Moving/resizing/removing controls discards old frames; input waits for measured bounds and a fresh observation.

Capture timestamps remain real. If a static display has stopped producing frames, Rust requests a fresh buffer and the service reattaches the existing virtual display's surface; it does not create a second virtual display or relabel an old image. A missing/old/blocked frame stops the move. Accessibility callbacks carry capture/action IDs, and missing completion keeps the in-flight action owned until a callback or teardown. OS delivery still requires visual verification.

## Deferred until ADB is connected

Check installation/startup, actual consent/revocation, native engine/ONNX loading and static-screen refresh first. Then use a controlled board for both colors, click/drag, castling, all promotions, Auto/opponent replies, Stop during analysis/input and no duplicate moves. Check small portrait/landscape screens, cutouts, gesture navigation, magnification rejection, large text, overlay dragging/docking, no gesture through controls, locked/secure screens, activity recreation and process death. Include both 4 KB and 16 KB page-size devices/images and two physical phones of different performance. Do not infer any of these results from compilation or broker tests.

The compact surface requirements are in [the phone overlay plan](../docs/phone-overlay-plan.md). Linux live testing remains separately deferred in [linux-testing.md](linux-testing.md).
