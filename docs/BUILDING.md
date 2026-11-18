# Build ChessPilot

Build the Windows app on Windows, the Linux app on Linux, and the Android APK on Windows using the preparation script below. Android asset preparation currently uses Windows tools; a native Linux/macOS Android preparation script is not provided.

The exact ONNX model is already in this repository. First-time builds need internet for SDK/dependency/runtime/Stockfish preparation; normal gameplay is local after setup.

## Shared tools and checkout

Use the **Flutter 3.38.6** pin in [`app/.fvmrc`](../app/.fvmrc), **Rust 1.92.0 or a compatible installed stable toolchain**, and Git. CI and the Linux launcher read the same exact Flutter pin. `pubspec.yaml` declares the minimum supported Flutter version; pub itself does not enforce an upper Flutter SDK bound. The desktop CI pins Rust 1.92.0. Install Flutter from its [official SDK archive](https://docs.flutter.dev/install/archive) and Rust through [rustup](https://rustup.rs/). Add Flutter's `bin` and Cargo's `bin` to your terminal's PATH.

For project SDK management, [FVM](https://fvm.app/documentation/getting-started/installation) reads the committed `.fvmrc`. From `app`, run `fvm install`, then use `fvm flutter` in place of `flutter`. When the system Dart/Flutter installation is broken, use FVM's standalone installer rather than installing it through that broken Dart. FVM is a development tool; the application does not include it.

Linux users can instead use the self-contained recovery/build recipe below. It needs no FVM installation and does not use the system Flutter cache.

Start a new terminal after installing tools, then verify:

```sh
git --version
flutter --version
rustc --version
cargo --version
```

For a new checkout:

```sh
git clone --single-branch --branch rust https://github.com/OTAKUWeBer/ChessPilot.git ChessPilot-rust
cd ChessPilot-rust
```

The standalone Rust branch starts with a new history. For a checkout from before this cleanup, keep that working folder and use the fresh clone above; `git pull --ff-only` cannot join the old history to the new root commit. Do not reset away local changes.

For an existing checkout of the standalone branch:

```sh
git switch rust
git pull --ff-only origin rust
```

All build commands and output paths below start in the **repository root**, containing `app/`, `native/` and `tool/`. After a block changes into `app/`, return to the root before starting another platform's block. Do not replace existing user engine/configuration files to rebuild the app.

## Windows x64

### Prerequisites

- Windows with Visual Studio or Build Tools and the **Desktop development with C++** workload, MSVC x64 tools and Windows SDK. Visual Studio Code alone does not supply these. See [Flutter's Windows tooling guide](https://docs.flutter.dev/platform-integration/windows/setup).
- Rust's Windows MSVC host toolchain. Normal Windows rustup installation selects it; GNU-only hosts need the MSVC toolchain installed for this build.
- CMake 3.18 or newer available as `cmake`. The Visual Studio C++ CMake tools or a separate CMake installation can supply it.

To select the pinned Windows MSVC Rust host explicitly for this terminal:

```powershell
rustup toolchain install 1.92.0-x86_64-pc-windows-msvc --profile minimal
$env:RUSTUP_TOOLCHAIN = '1.92.0-x86_64-pc-windows-msvc'
```

```powershell
flutter config --enable-windows-desktop
flutter doctor -v
flutter devices
```

Resolve the Windows/Visual Studio issues reported by `flutter doctor` before building. `flutter devices` should list Windows.

On the project's current workstation, Build Tools is installed on X:. If CMake is not on PATH, this session-only command makes the installed copy available:

```powershell
$env:PATH = 'X:\BuildTools\VisualStudio\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:PATH
```

On another machine, use that machine's actual CMake path.

### Build and run

```powershell
cmake -P tool/prepare_desktop.cmake
if ($LASTEXITCODE -ne 0) { throw 'Native asset preparation failed' }
Set-Location app
flutter pub get
flutter build windows --release
```

Run from `app`:

```powershell
& ./build/windows/x64/runner/Release/chesspilot.exe
```

Output: **`app/build/windows/x64/runner/Release/`**. Copy/archive the whole directory, including DLLs, `data/`, model and licenses. On startup, Stockfish is reused beside the app or downloaded into that writable folder when absent. Supply a compatible `stockfish.exe` there for offline engine setup.

### Build one Windows setup EXE

Install [Inno Setup 6.3 or newer](https://jrsoftware.org/inno-setup) on the build machine. After the release build above, run from the Rust project root:

```powershell
./tool/build_windows_installer.ps1
```

Output: **`app/build/windows/installer/ChessPilot-VERSION-windows-x64-setup.exe`**. Users run this one file and launch the app through its Start menu shortcut. The installer keeps the DLLs, Flutter data and model inside the selected installation folder. The default is per-user, without an administrator prompt; another writable folder can be selected. First launch downloads a CPU-compatible Stockfish beside the app when missing.

This unsigned setup excludes the developer's Stockfish, options, caches and logs. Existing installed engine/settings/cache files are preserved across reinstall and uninstall. See [installation behavior](INSTALLING.md#windows-x64) and [isolated installer checks](TESTING.md#windows-installer-lifecycle). The CI installer artifact is separate from the portable ZIP.

## Linux x64, including Arch

### One-session Arch build / snapshot-error recovery

`Wrong full snapshot version` from `flutter pub get` occurs before the app builds. It indicates incompatible Dart/tool snapshot files in the selected SDK; changing the app version or ONNX model does not repair it. The [Flutter SDK launcher](../tool/flutter_linux.sh) uses a private exact-tag checkout under ignored `native/target/flutter-sdk/`, with its own bundled Dart. It leaves the system Flutter SDK alone. Existing global tool paths and build diagnostics are recorded in one report.

From the Rust project root, run this whole block:

```sh
git pull --ff-only
sudo pacman -S --needed base-devel git curl unzip zip xz clang cmake ninja pkgconf gtk3 grim rustup librsvg gobject-introspection file
bash tool/build_linux.sh
```

If pulling fails, resolve the Git state before building; the helper does not reset or stash changes. The first SDK/toolchain setup can take longer and needs internet. Subsequent runs reuse the private pinned SDK. The helper installs/selects Rust 1.92.0, prepares the hash-checked ONNX Runtime, prints SDK/doctor information, runs pub get, builds the release bundle and packages the one-file portable app plus optional installer. Android/Chrome doctor warnings are not Linux build requirements. It does not run the app or send input.

Report: `native/target/linux-build-report.log`. Portable release upload: **`app/build/linux/installer/ChessPilot-VERSION-linux-x86_64`**. The optional installer is **`app/build/linux/installer/ChessPilot-VERSION-linux-x64-setup.run`**. The intermediate executable at `app/build/linux/x64/release/bundle/chesspilot` requires its whole bundle; do not copy it alone into Downloads or Releases.

If you need to run an individual Flutter command using that SDK from any working directory:

```sh
bash /path/to/rust-root/tool/flutter_linux.sh --version
bash /path/to/rust-root/tool/flutter_linux.sh pub get
bash /path/to/rust-root/tool/flutter_linux.sh build linux --release
```

The launcher always uses `app` as the Flutter project. Do not copy generated SDK caches between Windows and Linux. The `flutter` and `dart` commands from an unrelated system installation can keep showing the old error; use the project launcher or `fvm flutter`.

### Prerequisites

Install the tools for your distribution. CI uses Ubuntu 22.04 as the Linux release build baseline; the Arch package names are listed separately.

Ubuntu / Debian:

```sh
sudo apt-get update
sudo apt-get install -y build-essential git curl unzip zip xz-utils \
  clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev libstdc++-12-dev
```

Arch:

```sh
sudo pacman -S --needed base-devel git curl unzip zip xz clang cmake ninja pkgconf gtk3 rustup
```

For the existing wlroots Wayland capture path on Arch:

```sh
sudo pacman -S --needed grim
```

These are build dependencies plus the wlroots capture helper. See [Flutter's Linux prerequisites](https://docs.flutter.dev/platform-integration/linux/setup) and the Arch packages for [GTK3](https://archlinux.org/packages/extra/x86_64/gtk3/), [Ninja](https://archlinux.org/packages/extra/x86_64/ninja/) and [grim](https://archlinux.org/packages/extra/x86_64/grim/).

After installing Flutter/Rust and adding them to PATH:

```sh
rustup toolchain install 1.92.0 --profile minimal
export RUSTUP_TOOLCHAIN=1.92.0
flutter config --enable-linux-desktop
flutter doctor -v
flutter devices
```

Resolve the Linux toolchain issues first. The device list should include Linux.

### Build and run

```sh
cmake -P tool/prepare_desktop.cmake
cd app
flutter pub get
flutter build linux --release
./build/linux/x64/release/bundle/chesspilot
```

Output: **`app/build/linux/x64/release/bundle/`**. Keep its `lib/`, `data/`, model and licenses with the executable. The folder must be writable for the first automatic Stockfish installation. For offline setup, put a compatible executable named `stockfish` beside `chesspilot` and give that engine execute permission.

To make a portable archive, from `app`:

```sh
tar -czf ChessPilot-linux-x64.tar.gz -C build/linux/x64/release/bundle .
```

This archive remains an optional complete portable bundle. For the one-file installer, use the packaging command below. The current GTK launcher may run through XWayland even when board capture/input uses the native wlroots protocols. Keep the session's normal `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY` values; the compositor must expose screencopy and `zwlr_virtual_pointer_manager_v1`. GNOME/KDE portal-based automation is unfinished. A successful Linux build does not establish live Wayland calibration. Follow [Linux capture and gameplay checks](TESTING.md#linux-capture-and-gameplay) on the actual desktop.

### Build the Linux one-file app and installer

After a release build, run from the repository root (return from `app` first). Ubuntu/Debian packaging prerequisites:

```sh
sudo apt-get install -y libgtk-3-dev libgtk-3-bin librsvg2-dev \
  libgirepository1.0-dev libgdk-pixbuf2.0-bin file dpkg-dev
bash tool/build_linux_installer.sh
```

Arch packaging prerequisites are `gtk3 librsvg gobject-introspection file`, in addition to the normal build tools. The script fetches hash-pinned official linuxdeploy, GTK plugin and Makeself tools into ignored `native/target/linux-packaging-tools`; no system Makeself or FUSE installation is needed. Ubuntu 22.04 is the CI release build baseline. Build on the oldest supported distribution because bundling does not remove glibc/kernel/driver requirements; an Arch-built executable is not an older-Ubuntu compatibility build.

Packaging exports `NO_STRIP=1` for linuxdeploy and its GTK subprocesses because its bundled strip cannot parse modern Arch `.relr.dyn` sections. It uses the 512px Linux packaging icon; the full-resolution app logo is retained. If an older checkout reports either `.relr.dyn` strip errors or an invalid 1024px icon, update and rerun the packaging command; rebuilding Flutter is unnecessary for these packaging-only fixes.

Output: **`app/build/linux/installer/ChessPilot-VERSION-linux-x64-setup.run`** and its `.sha256` sidecar. Upload the `.run` as the Linux application installer. It contains the complete native/Flutter/model payload plus GTK dependencies, adds a per-user launcher, preserves downloaded engines/configuration/cache across upgrades, and supports `-- --uninstall`. Packaging checks the bundled model, excludes maintainer engine/config/cache/logs, retains dependency notices, and embeds a SHA-256 integrity check. This is a per-user shell installer, not a DEB/RPM or AppImage.

The same command also outputs **`app/build/linux/installer/ChessPilot-VERSION-linux-x86_64`** plus its checksum. This is the one-file portable app: it self-extracts and runs `AppRun` directly, then cleans up its temporary application directory. Its launcher directs engine downloads and options to persistent user data. It installs no menu entry and needs no other package format. No `.deb` or AppImage is generated.

Test the installer on Linux without touching your real installation:

```sh
bash tool/test_linux_installer.sh app/build/linux/installer/*-setup.run app/build/linux/installer/ChessPilot-*-linux-x86_64
```

The real-package check needs Xvfb (`xvfb` on Ubuntu, `xorg-server-xvfb` on Arch). CI runs it automatically against temporary installation paths.

## Android ARM64 APK, built on Windows

### Prerequisites

- Flutter 3.38.6 and Rust, with working Visual Studio C++/Windows SDK tools for Rust's MSVC host, as above.
- JDK **17 or 21**. Set `JAVA_HOME` to that installation, not its `bin` folder.
- Android SDK platform **36**, Build Tools **36.0.0**, Platform Tools/ADB, command-line tools, **NDK 28.2.13676358**, and **CMake 3.22.1** with Ninja. Install these through Android Studio's SDK Manager or the Android command-line SDK Manager. See [Flutter's Android tooling guide](https://docs.flutter.dev/platform-integration/android/setup).

Set these paths to your actual SDK/JDK installations in PowerShell. The JDK path below is an example; it is not downloaded by the build script.

```powershell
$env:ANDROID_SDK_ROOT = 'C:\Android\Sdk'
$env:JAVA_HOME = 'X:\Tools\jdk-21'
$env:PATH = "$env:JAVA_HOME\bin;$env:ANDROID_SDK_ROOT\platform-tools;$env:PATH"
```

If command-line tools are already installed in the usual `latest` folder, install the required SDK components with:

```powershell
& "$env:ANDROID_SDK_ROOT\cmdline-tools\latest\bin\sdkmanager.bat" 'platform-tools' 'platforms;android-36' 'build-tools;36.0.0' 'ndk;28.2.13676358' 'cmake;3.22.1'
flutter doctor --android-licenses
flutter doctor -v
```

Complete the interactive license prompts yourself. If Flutter selects another JDK, use `flutter config --jdk-dir` with your actual JDK 17/21 directory and recheck `flutter doctor -v`.

### Prepare the engines and build

From the Rust project root:

```powershell
$ErrorActionPreference = 'Stop'
rustup toolchain install 1.92.0-x86_64-pc-windows-msvc --profile minimal
$env:RUSTUP_TOOLCHAIN = '1.92.0-x86_64-pc-windows-msvc'
rustup target add aarch64-linux-android
./tool/prepare_android.ps1 -AndroidSdk $env:ANDROID_SDK_ROOT
if ($LASTEXITCODE -ne 0) { throw 'Android engine preparation failed' }
Set-Location app
flutter pub get
flutter build apk --debug --target-platform android-arm64
```

The preparation step downloads pinned official Stockfish sources/network, verifies hashes, builds the baseline/dot-product Android executables, and saves them under ignored `native/target/`. It can take longer on the first run. Gradle then builds the Rust ARM64 library using the NDK linker and packages everything; a separate manual `cargo build` is not required.

The standard Windows MSVC host path has been checked locally. The earlier GNU host/linker helper setup is an alternative, not a prerequisite on a machine with working MSVC tools. If deliberately selecting that alternative, follow the engineering guide and set `ORG_GRADLE_PROJECT_rustToolchain` explicitly.

Debug output: **`app/build/app/outputs/flutter-apk/app-debug.apk`**.

For an optimized local APK, from `app`:

```powershell
flutter build apk --release --target-platform android-arm64
```

Release-mode output: **`app/build/app/outputs/flutter-apk/app-release.apk`**. The project currently signs this with the debug key for local testing. Configure your own release keystore/signing before public distribution; this is not a store-ready signed release.

Use the normal build command shown above when changing build modes. With Flutter 3.38.6, adding `--no-pub` can retain development-plugin registration from a previous debug build and fail release compilation. The normal command regenerates the plugin registration. The release-mode APK has built locally; physical-phone acceptance so far refers to the earlier debug engineering build.

## Install or verify a build

Use [INSTALLING.md](INSTALLING.md) for installation and first launch. Developer ADB/device checks, installer smoke tests and platform evidence are in [TESTING.md](TESTING.md). Release signing/version maintenance is in [RELEASING.md](RELEASING.md).

## Desktop asset preparation details

The preparation script pins ONNX Runtime 1.20.1 and verifies cached archives. If the GitHub release download fails, it uses the hash-pinned official Microsoft.ML.OnnxRuntime NuGet package through two endpoints. Runtime/model changes require real inference regression checks; dependencies do not float to latest.

`-DCHESSPILOT_DESKTOP_PLATFORM=windows-x64`, `windows-arm64`, `linux-x64` or `linux-arm64` selects prepared assets before `-P`. This does not supply cross-compilers or Flutter cross-build support. `CHESSPILOT_DESKTOP_ASSETS`, `CHESSPILOT_RUST_TARGET` and `CHESSPILOT_RUST_TOOLCHAIN` select the corresponding CMake inputs. Prepared downloads remain under ignored `native/target/`; ordinary Flutter/CMake builds do not download them implicitly.

The Windows installer builder locates Inno Setup on PATH or in its usual installation folders; `-IsccPath` selects a custom compiler. It verifies executable version/architecture, required runtime files and model checksum before building. Installer output excludes developer-local engines, configuration, caches and logs. See the installation guide for end-user update/uninstall behavior and the test guide for payload verification.
