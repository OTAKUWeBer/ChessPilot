# Desktop builds

Commands and output paths in this guide are relative to the Rust project root, the folder containing `app/`, `native/` and `tool/`.

For prerequisite installation and separate copyable Windows/Linux commands, start with the [complete build guide](docs/BUILDING.md).

Flutter and Rust share one Windows/Linux desktop bundle. CMake builds the native runtime with Cargo's locked dependencies, then installs the runtime, detection model, CPU ONNX Runtime and licenses alongside Flutter. The bundle uses native libraries and assets; copying only the executable is insufficient.

Use Flutter 3.38.6, Rust and CMake 3.18 or newer. Windows needs the Visual Studio C++ desktop workload and Windows SDK. Linux needs Flutter's GTK3/compiler/build prerequisites. The exact Python model is tracked at `assets/models/chess_detection.onnx`, with a SHA-256 manifest; no model download is needed. Stockfish is checked beside the app on every launch and downloaded into that same root folder when absent. Use a writable portable/app directory. Existing engines placed beside the app and explicit engine paths remain supported.

## Prepare and build

From the Rust project root:

```sh
cmake -P tool/prepare_desktop.cmake
cd app
flutter pub get
flutter build windows --release
# On Linux, use flutter build linux --release instead.
```

On Windows, CMake can be the executable provided by the Visual Studio workload or Android SDK (`C:/Android/Sdk/cmake/3.22.1/bin/cmake.exe` on this workstation). The preparation script pins ONNX Runtime 1.20.1 by SHA256 and rechecks cached archives before extracting. If GitHub release downloads fail, it tries the official Microsoft.ML.OnnxRuntime 1.20.1 NuGet package through two official endpoints, verifies its separate pinned hash and extracts the matching architecture. The runtime version does not float to latest. The NuGet fallback passed both Windows/Linux CI in [run 44285448168](https://github.com/OTAKUWeBer/ChessPilot/actions/runs/44285448168). It supports `-DCHESSPILOT_DESKTOP_PLATFORM=windows-x64`, `windows-arm64`, `linux-x64` or `linux-arm64` before `-P`. Runtime updates require changing the pins and rerunning inference parity checks. Ordinary Flutter/CMake builds do not perform this download.

Prepared assets and archives live under ignored `native/target/`. CMake reports missing assets at configuration rather than producing an incomplete app. `CHESSPILOT_DESKTOP_ASSETS` can select a prepared asset directory through CMake; `CHESSPILOT_RUST_TARGET` and `CHESSPILOT_RUST_TOOLCHAIN` select a matching Rust target/toolchain when needed. Rust defaults to Windows MSVC or Linux GNU for the target architecture. Install that Rust target before cross-building; these switches do not supply a missing cross-linker or Flutter cross-build toolchain.

Windows output is `app/build/windows/x64/runner/Release/` for x64. Linux output is `app/build/linux/x64/release/bundle/` for x64. Distribute the entire directory. Windows bundles the compiler's redistributable runtime DLLs through CMake's standard runtime installation module. Linux loads libraries from `lib/`; native resource lookup searches that same directory. Existing `engine_config.txt` is never installed over user configuration. Linux rebuilds preserve the bundle root so portable Stockfish, configuration and download cache survive; only generated Flutter assets are cleared before replacement. Optional offline Stockfish can be placed beside the executable, with its corresponding GPL license and source information.

Normal window close awaits native worker/engine cleanup through Flutter's exit lifecycle. Android Activity recreation continues to retain the service-owned session. Forced process termination cannot await cleanup. Desktop sizing retains the 380×520 baseline and dampened high-resolution scaling. Size and minimums are capped to the monitor’s usable area, including small screens and high DPI. The downloader uses a separate compact setup view: 420 logical pixels wide, content-measured height, and monitor bounds. Completion restores the main dimensions, preserving exact physical pixels across the handoff. Windows also fits the window after monitor/DPI/display changes; shared sizing checks cover 720p through 8K and 1×–3× scaling.

## Single-file Windows installer

After the release build, install Inno Setup 6.3+ and run `./tool/build_windows_installer.ps1` from the Rust project root. It validates the release version/architecture, required files and exact model, then creates `app/build/windows/installer/ChessPilot-3.0.0-beta.1-windows-x64-setup.exe`. Users install once and launch from a shortcut; the runtime DLLs/assets remain together under the selected per-user app folder.

The installer payload excludes developer-local Stockfish, configuration, caches and logs. Its stable identity permits in-place updates, and uninstall leaves user-created files alone. The separate `test_windows_installer.ps1` smoke check covers installed hashes, shortcuts, per-user registration, reinstall preservation and uninstall using a distinct test identity. It does not start gameplay. See [Windows packaging](packaging/windows/README.md).

## Isolated packaging check

The CMake fixture builds and installs the same native bundle rules without requiring a Flutter desktop executable:

```sh
cmake -S tool/tests/desktop_bundle -B native/target/bundle-check -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_INSTALL_PREFIX=/absolute/path/to/rust-root/native/target/bundle-check/install
cmake --build native/target/bundle-check
cmake --install native/target/bundle-check --component Runtime
```

This workstation now has Build Tools at `X:/BuildTools/VisualStudio`, and normal MSVC builds work. To repeat earlier GNU-only checks, select `-DCHESSPILOT_RUST_TARGET=x86_64-pc-windows-gnu -DCHESSPILOT_RUST_TOOLCHAIN=stable-x86_64-pc-windows-gnu` and the GNU host linker/dlltool environment documented in [README](docs/ENGINEERING.md). CMake can use the Android SDK Ninja executable through `CMAKE_MAKE_PROGRAM`.

Set `CHESSPILOT_BUNDLE_TEST` to the absolute installed fixture directory and run `cargo test --manifest-path native/Cargo.toml --test resources relocated_bundle_resolves_default_assets_without_checkout_paths -- --ignored`. The check relocates its own test executable into the fixture, verifies default model/runtime lookup and removes only that owned executable. It refuses paths outside `native/target`.

Set `CHESSPILOT_MODEL` to the installed model and `CHESSPILOT_ORT` to the installed ONNX Runtime library, then run `cargo test --manifest-path native/Cargo.toml --test vision actual_onnx_inference_and_zoom_search_match_python -- --ignored`. This tests real normal/zoom/failure inference against Python fixtures. The Flutter client tests can use the installed DLL through `CHESSPILOT_LIBRARY_PATH`.

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

The runner must load its bundled DLL. A private 16 MB / one-thread config isolates this UI check; no user configuration is replaced. First use downloads Stockfish beside the generated Debug executable, later runs reuse it. The progress-layout fixture also checks the full downloader on warm runs. Only this app's Flutter surface is saved under ignored `target/windows-ui`; other desktop windows are not captured. The maintainer reports working Linux gameplay and castling; additional physical monitor/compositor combinations remain unverified. Limited Android phone results are recorded separately in [Android testing](android-testing.md).

## Desktop CI

`.github/workflows/native.yml` builds Windows and Linux bundles with Flutter 3.38.6 and Rust 1.92.0. It verifies the tracked model checksum, native regressions, Flutter checks, actual ONNX/refined-search parity and an Xvfb X11 capture/capability probe. Linux artifacts are tarred to preserve executable permissions. Windows also builds the setup EXE, runs its isolated install/reinstall/uninstall check and uploads a separate installer artifact. The [beta hosted run](https://github.com/OTAKUWeBer/ChessPilot/actions/runs/44147469834) passed both Windows and Linux jobs, including complete bundles, real model parity and the Xvfb probe. This does not replace physical Wayland, phone or live-game tests. Real-engine tests that require an explicit Stockfish path remain opt-in.
