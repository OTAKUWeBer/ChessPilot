<p align="center">
  <img src="assets/logo.png" alt="ChessPilot logo" width="150" />
</p>

# ChessPilot — v3.0.0-beta.1

Local chess board detection, Stockfish analysis and optional move automation, rebuilt with **Flutter and Rust** for Windows, Linux and Android.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-F48041?style=for-the-badge" alt="MIT license" /></a>
  <a href="https://github.com/OTAKUWeBer/ChessPilot/tree/rust"><img src="https://img.shields.io/badge/version-3.0.0--beta.1-0E80C0?style=for-the-badge" alt="3.0.0-beta.1" /></a>
  <img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge" alt="Windows" />
  <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux" />
  <img src="https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=black" alt="Android" />
</p>

**Read a 2D on-screen chessboard, evaluate locally with Stockfish, and optionally play the move.** Detection and analysis run on your device after setup.

This standalone `rust` branch contains the Flutter UI, Rust core/runtime and native platform integrations. **Python is not included or required.** The original Python app remains on [main](https://github.com/OTAKUWeBer/ChessPilot/tree/main).

---

## Current status

This is a beta, with working Windows, Linux and Android pipelines and the remaining checks recorded below. Source, portable engineering bundles and a single-file Windows setup builder are available. Windows CI publishes an unsigned installer artifact; a signed stable release is not published yet.

| Platform | Implemented | Verification so far |
| --- | --- | --- |
| Windows x64 | Flutter desktop UI, native capture/input, bundled ONNX, CPU-compatible Stockfish downloader, manual/Auto moves | Release build, startup/downloader/window/exit integration, controlled-board Drag/Click and Auto in both orientations, real ONNX and Stockfish tests |
| Android ARM64 | Flutter dashboard, native capture/touch services, movable logo overlay, packaged model and Stockfish 19 | Android 14 physical-phone checks over a Brave/Lichess bot game: Drag/Click, Auto, Stop, overlap rejection, lock invalidation and Exit cleanup |
| Linux | Flutter packaging, X11 and the Python app's wlroots Wayland capture/input path, desktop downloader | Windows/Linux CI regressions, complete Linux bundle build, real ONNX parity and an Xvfb X11 capture probe; maintainer-reported Linux gameplay and castling passed on November 18, 2026; broader compositor/monitor coverage remains open |

Android currently packages `arm64-v8a` and targets API 24 or newer. That build minimum does not establish compatibility with every device. GNOME/KDE Wayland portal capture/control, macOS and iOS are not implemented.

## ⚡ Highlights

- **Flutter UI, Rust pipeline:** the existing green/dark design, compact desktop controls, color selection, depth/delay/mode settings, castling controls, diagnostics and keyboard shortcuts.
- **Native, in-memory processing:** capture buffers feed the persistent ONNX detector, then Stockfish, input and fresh visual verification. Gameplay does not save screenshots to disk or start a Python subprocess.
- **The exact Python ONNX model:** `assets/models/chess_detection.onnx` is tracked with its [SHA-256 manifest](assets/models/chess_detection.onnx.sha256) and included in desktop bundles and the APK. Piece/board/promotion mappings and RGB letterbox preprocessing have Python comparison fixtures.
- **Zoom/small-board recovery:** unreadable normal detection automatically tries refined board crops/tiles. If bounded refinement still fails, the app reports a detection error and sends no move. Promotion-menu detection retains its separate raw path.
- **Manual and Auto play:** Drag and Click, initial Auto play on your turn, stable legal opponent-reply tracking, castling and promotion handling, and cancellation-aware waits. Manual Play stays disabled while Auto is enabled.
- **Automatic castling controls:** confirmed king moves untick both sides; moving or losing an original rook unticks that side, for White and Black. Returning a piece home does not restore lost rights. Manually disabled rights stay off.
- **Reliability fixes:** Windows timer oversleep handling, bounded detector jitter, delayed-animation verification, turn/history resynchronization and castling rook-animation checks. An uncertain move is never blindly dispatched again.
- **Windows installer:** one setup EXE installs the model/runtime files, Start menu shortcut and uninstaller without requesting administrator access. Updates preserve existing Stockfish/settings/cache. The portable ZIP remains an alternative. See [Windows packaging](packaging/windows/README.md).
- **Desktop engine setup:** a compact progress view prepares Stockfish before the main controls. Every launch checks beside the app; missing engines are downloaded, hash/architecture/UCI checked and installed in that same folder. An existing engine is reused rather than updated on every launch.
- **Android support:** full-screen capture consent, user-enabled accessibility gestures, visible foreground notification controls, a movable app-logo bubble and a shallow control panel. Phone help omits desktop keyboard shortcuts.
- **Cleanup and diagnostics:** Stop cancels work; Exit closes capture, workers and the engine. Rotating native logs and Android log sharing help investigate failures.

The [source inventory](docs/migration-code-inventory.md), [76-call Python timing ledger](docs/python-timing-parity.md) and [engineering guide](docs/ENGINEERING.md) document the port. The native implementation intentionally adds validation and verified history rather than copying Python's unsafe retry/unverified-success behavior literally.

## Engine and model packaging

| Component | Windows / Linux | Android |
| --- | --- | --- |
| ONNX model | Exact Python model included with the app's native assets | Same model inside the APK; private copy checked by SHA-256 at startup |
| ONNX Runtime | Pinned native CPU runtime packaged with the desktop bundle | Native CPU runtime packaged with the APK |
| Stockfish | Downloads a compatible official prebuilt when missing; stored beside the app | Stockfish 19 built from pinned official sources for Android compatibility and packaged in the APK |
| Engine selection | Native CPU features choose a compatible official asset | Baseline NEON or dot-product build, with startup fallback |
| Network needed | First engine download, unless supplied offline; build preparation also downloads dependencies | Build preparation; normal installed gameplay uses packaged assets |

**Stockfish is CPU-only.** ONNX GPU/NPU acceleration is not enabled in this beta. Android uses packaged native executables because its execution rules differ from desktop; engine updates currently arrive through an updated APK. Both Android variants share a verified NNUE network.

## Windows / Linux setup

1. On Windows, run the single **setup EXE**, choose a writable install folder and launch ChessPilot from the Start menu. For portable Windows or Linux, extract the **entire desktop bundle** and keep its executable, data, model, native libraries and licenses together.
2. Launch ChessPilot. If Stockfish is missing beside the app, let the compact downloader finish. For offline setup, place a compatible `stockfish.exe` (Windows) or executable `stockfish` (Linux) beside the app first.
3. Keep the whole 2D board visible and choose your bottom-side color. On Windows/X11, capture currently selects the primary monitor; put the board there.
4. Choose Drag or Click, depth, screenshot delay and applicable castling rights. Start **Play Next Move** or **Auto on your turn**.
5. Use Stop to pause. Escape stops and returns to color selection; reselect the color when changing games or boards.

The desktop main view has a 380 × 520 logical-pixel baseline and scales within the monitor's usable area. Setup uses a separate, content-sized download view. Always-on-top behavior depends on the window manager, particularly on Wayland.

| Desktop shortcut | Action |
| --- | --- |
| W / B | Choose White / Black |
| Left / Right | Adjust depth |
| Up / Down | Adjust screenshot delay |
| D / C | Choose Drag / Click before color selection |
| P / A | Play next move / toggle Auto |
| K / Q | Toggle castling rights |
| Esc | Stop and change color |

On supported wlroots Wayland sessions, install `grim` and use a compositor exposing screencopy and `zwlr_virtual_pointer_manager_v1`. Keep the normal Wayland environment variables. See [Linux setup and live checks](linux-testing.md); this is not universal Wayland support.

## Android setup and controls

1. Open ChessPilot and choose the actual bottom-side color.
2. Enable **ChessPilot touch control** in Android's accessibility settings. It declares gesture capability without retrieving accessibility window content.
3. Choose **Share entire display** and approve Android's per-session screen-sharing consent. Allow notifications for visible running/Stop/Exit controls.
4. Switch to the board. Tap the **48 dp app-logo bubble** to expand; drag the bubble or metadata/status area to reposition and dock it away from the board.
5. Use Play or Auto on your turn. The panel keeps readable color/depth/status lines and distinct **Play / Auto / Stop / Exit** controls, with at least 48 dp action targets. While working, the collapsed bubble becomes a red Stop control.
6. Stop pauses moves. Exit also ends screen sharing, closes Stockfish and removes the dashboard. Opening the dashboard or dragging the overlay pauses automation.

The overlay uses the accessibility window already provided by touch control, so it needs no separate general draw-over-other-apps permission. The native bridge masks measured control bounds and rejects covered boards or gesture paths through them. Screen lock, display geometry changes or lost touch/capture permission invalidate the session's capture/history; share the display again when requested.

| Setting | Desktop default / range | Android default / range |
| --- | --- | --- |
| Analysis depth | 15 / 10–30 | **10 / 8–30** |
| Screenshot delay | 0.4 seconds / 0–1 | 0.4 seconds / 0–1 |
| Move mode | Drag | Drag |

Depth 8 is available for faster phone analysis; higher depths remain selectable. Lower depth trades search strength for speed. Total response time still includes capture, board checks, movement, animation and verification. The new depth-10 default has not yet had a full latency benchmark. Earlier single-phone observations and their limits are in [Android testing](android-testing.md).

## Stockfish configuration

Desktop reads `engine_config.txt`, preferring an existing portable file. Put one beside the executable to customize options; existing files are preserved. For example:

```ini
setoption name Hash value 512
setoption name Threads value 2
```

Restart after editing. Android keeps its configuration in app-private storage and starts with 128 MB Hash and two threads; updates preserve existing configuration. Settings files accept engine options, not arbitrary UCI commands.

## 🛠️ Build from source

**[Complete Windows, Linux/Arch and Android build instructions](docs/BUILDING.md)** include prerequisites, SDK/JDK setup, engine preparation, commands, output paths and phone installation. Flutter 3.38.6 is pinned in `app/.fvmrc` and shared with CI and the Linux launcher; use that project SDK rather than a different global version. Use Rust 1.92.0 or a compatible stable toolchain. FVM users can run `fvm install` and `fvm flutter` from `app`. Build Windows on Windows and Linux on Linux; Android preparation currently uses a Windows host.

Build commands and output paths below start at the **repository root**, containing `app/`, `native/`, `tool/`, `assets/` and `packaging/`.

Start each platform block from the repository root. After changing into `app/`, return to the root before using another block.

Windows (PowerShell):

```powershell
cmake -P tool/prepare_desktop.cmake
Set-Location app
flutter pub get
flutter build windows --release
# Optional: build one setup EXE (requires Inno Setup 6.3+):
../tool/build_windows_installer.ps1
```

Linux (after installing the prerequisites in the full guide):

```sh
bash tool/build_linux.sh
```

This uses a project-local Flutter/Dart SDK rather than a possibly mixed system SDK, prepares the pinned ONNX Runtime with the official NuGet fallback, and records a complete report in `native/target/linux-build-report.log`.

Android (PowerShell; set `ANDROID_SDK_ROOT` and `JAVA_HOME` first as shown in the full guide):

```powershell
rustup target add aarch64-linux-android
./tool/prepare_android.ps1 -AndroidSdk $env:ANDROID_SDK_ROOT
Set-Location app
flutter pub get
flutter build apk --debug --target-platform android-arm64
# For optimized local testing: flutter build apk --release --target-platform android-arm64
```

| Output | Path |
| --- | --- |
| Windows x64 installer | `app/build/windows/installer/ChessPilot-3.0.0-beta.1-windows-x64-setup.exe` |
| Windows x64 bundle | `app/build/windows/x64/runner/Release/` |
| Linux x64 bundle | `app/build/linux/x64/release/bundle/` |
| Android debug APK | `app/build/app/outputs/flutter-apk/app-debug.apk` |
| Android local release-mode APK | `app/build/app/outputs/flutter-apk/app-release.apk` |

Windows users can download one setup EXE; it installs the required DLLs/assets in the selected app folder. Portable desktop users must keep the whole bundle directory. Android installs as one APK. The current release-mode APK uses a debug signing key for local testing; production signing is unfinished. See [desktop build details](desktop-building.md), [Android evidence](android-testing.md) and [the engineering guide](docs/ENGINEERING.md) for deeper checks.

The [beta GitHub Actions run](https://github.com/OTAKUWeBer/ChessPilot/actions/runs/44147469834) passed complete Windows/Linux builds, packaged-runtime Flutter tests, real ONNX/refined-search checks, model integrity and the Xvfb X11 capture probe. Its desktop bundle artifacts are available on that run while retained. Subsequent Windows runs also build/check the installer and publish a separate `ChessPilot-windows-x64-installer` artifact; the exact installer checks are described in [Windows packaging](packaging/windows/README.md). Live Wayland and broader device acceptance remain separate.

## Verification and remaining work

### Screen sizes and engine lifecycle

The desktop window starts at **380×520 logical pixels**, with a baseline minimum of **360×480**. High-resolution sizing grows gently; initial dimensions and minimums shrink to fit the monitor's usable area. There is no fixed maximum supported monitor resolution. Sizing checks cover 720p through 8K and 100%–300% scaling; this checks the sizing logic, not every physical display. Windows also refits after monitor/DPI changes. Flutter controls scroll when space is limited, with widget checks at 320×568 and 380×520, including enlarged text.

Android uses density-independent sizes: a movable **48 dp** bubble and a **216 dp** expanded panel, positioned within system-bar/cutout bounds. One Android 14 phone has physical capture/input/overlay evidence. Other phones, foldables, unusual aspect ratios and sustained sessions still need testing.

Stockfish checks cover initialization, persistent reuse, cancellation, invalid-position recovery and shutdown. Normal desktop close awaits native cleanup; Android Exit ends capture and closes the engine. The engine sends `quit`, then kills and reaps an unresponsive child after a bounded wait. Stop pauses automation and may keep the engine ready for the next move. These checks support beta use; they do not establish complete security or long-run memory acceptance.

Native regression checks:

```sh
cargo test --manifest-path native/Cargo.toml --workspace --locked
```

Flutter checks, from `app`, after building/selecting the native library as described in the engineering guide:

```sh
flutter test
flutter analyze
```

The tests cover domain/Python fixtures, engine protocol failures/cancellation, actual inference, controller transitions, native buffer ownership, configuration, installers, diagnostics and platform adapters. Asset-, engine-, desktop- and network-dependent integration tests are explicit opt-ins; a normal unit-test pass does not establish those cases. Frozen comparison tools use Python only during development.

Still open before stable acceptance:

- Longer Windows/Android sessions, additional target sites/monitors/phones, release-mode performance/memory and broader security review.
- Physical-phone black orientation, castling/all promotions, Stop during gesture delivery, rotation/large text and permission-denial/revocation recovery.
- More Linux compositor/monitor coverage, non-wlroots Wayland portal support, Linux distribution packages and signed release/clean-install checks. The maintainer reports working Linux gameplay and castling on November 18, 2026.

A screenshot cannot reconstruct earlier castling or en-passant history, and the selected color is not automatic turn detection. Start on your turn with appropriate rights. After a verified baseline, Auto tracks legal opponent replies. On unreadable frames, changed geometry or uncertain delivery, the app pauses; it does not blindly repeat a move.

## 🔧 Troubleshooting and logs

- **Board not detected:** keep it 2D and unobstructed, move the app/overlay clear, then retry. Refined search is automatic; an unreadably small board still fails with an error.
- **Phone says to restart sharing:** unlock the screen, enable the required touch service if disconnected, and share the entire display again. Projection tokens are not silently reused after loss.
- **Desktop engine setup fails:** check the app folder is writable and the network is available, or supply a compatible Stockfish beside the executable. Keep its license/source information when redistributing it.
- **Play disabled:** choose a color and finish engine/capture setup. Stop Auto before requesting a manual move. After checkmate or stalemate, choose **New game**, then select your color again.
- **Game finished:** checkmate and stalemate appear as normal results. Position errors stay in the game controls with a short explanation and technical details; they do not reopen the Stockfish downloader.
- **Need diagnostics:** open Help/Shortcuts → Diagnostics / logs. Desktop can open the log folder; Android can share recent logs through its chooser.

Native logs are named `chesspilot-native.log`, with rotation. Windows normally uses `%LOCALAPPDATA%/ChessPilot/logs`; Linux prefers `$XDG_STATE_HOME/chesspilot/logs`, then `$XDG_DATA_HOME/chesspilot/logs` or `~/.local/share/chesspilot/logs`. Android logs remain in app-private storage until shared. The Python `chesspilot.log` is preserved separately. Gameplay captures/model tensors are not written to these logs; development UI screenshots are separate, opt-in test artifacts.

When reporting a problem, include the app version/build, OS/device/display server, board/browser, move mode/depth and relevant diagnostics. Include a board screenshot only if you choose to share it.

## License and acknowledgments

ChessPilot's source is [MIT licensed](LICENSE). Bundled dependencies retain their own licenses: Stockfish is GPL-3.0-or-later, and ONNX Runtime includes its license/notices. Android packaging includes Stockfish license/source information; desktop downloaded engines retain release/source metadata. Review all dependency/model redistribution requirements before publishing binaries.

Thanks to [Zai-Kun's 2D chess detector](https://github.com/Zai-Kun/2d-chess-pieces-detection), the [Stockfish team](https://stockfishchess.org/), Flutter, Rust, ONNX Runtime and the project's contributors/testers.
