# Install ChessPilot

Choose the package for your device. Installing a downloaded app does not require Flutter, Rust, Visual Studio, an Android SDK or ADB. If you want to compile it yourself, use [the build guide](BUILDING.md).

## Get the app

Desktop packages are attached to [successful rust-branch builds](https://github.com/OTAKUWeBer/ChessPilot/actions/workflows/native.yml?query=branch%3Arust). GitHub may require sign-in to download artifacts, and older artifacts may expire. Check that the build/version matches the one you intend to install.

| Device | Package |
| --- | --- |
| Windows x64 | `ChessPilot-windows-x64-installer` artifact; unzip it to find the setup EXE |
| Windows portable | `ChessPilot-windows-x64` artifact; unzip it, then extract the enclosed `ChessPilot-windows-x64.zip` |
| Linux one-file app | `ChessPilot-linux-x64-portable` artifact; unzip it to find `ChessPilot-VERSION-linux-x86_64` |
| Linux AppImage / Debian package | `ChessPilot-linux-x64-packages` artifact; unzip it to find the `.AppImage` and `.deb` |
| Linux installer | `ChessPilot-linux-x64-installer` artifact; unzip it to find the single `*-setup.run` installer |
| Linux bundle | `ChessPilot-linux-x64` artifact; unzip it, then extract the enclosed `.tar.gz` |
| Android ARM64, API 24+ | `app-release.apk` from a trusted publisher or your own build; desktop CI does not currently publish an APK |

The current Windows installer is unsigned. Android release-mode builds currently use the developer's local debug key; production signing is still a publisher task. A file named “release” is a build mode, not proof of publisher signing. Do not change system security settings globally to install the app.

## Windows x64

The installer requires Windows 10 build 17763 or newer and x64 execution support. Native x64 is the tested build; ARM64 emulation has not been verified.

1. Extract the installer artifact ZIP and run `ChessPilot-VERSION-windows-x64-setup.exe`.
2. Choose the installation folder. The default is `%LOCALAPPDATA%\Programs\ChessPilot`; a different writable folder is supported. Installation is per-user and normally needs no administrator access.
3. Choose whether to add a desktop shortcut. Setup creates a Start menu shortcut.
4. Open ChessPilot from the shortcut. If Stockfish is missing, the compact downloader installs a CPU-compatible official engine in the app folder, then opens the controls. Keep the first launch online and let setup finish.
5. Open a visible 2D board, choose your color and start Play or Auto on your turn. See [first game](#first-game).

The setup EXE installs the supporting DLLs, model, data and licenses together. Keep those files in the installation folder. For a portable package, extract the whole bundle into a writable folder and run `chesspilot.exe` there; do not copy out just that EXE.

**Update:** close ChessPilot and run the newer installer into the same folder. Existing engine, settings and cache are preserved. **Uninstall:** use Windows Installed apps or the Start menu uninstaller. Installer-owned files are removed; user-created engine/settings/cache files and existing logs are preserved.

## Linux x64

### One-file portable app

Download `ChessPilot-VERSION-linux-x86_64`, or extract it from the portable CI artifact. Replace `VERSION` below with the downloaded version:

```sh
chmod +x ./ChessPilot-VERSION-linux-x86_64
./ChessPilot-VERSION-linux-x86_64
```

This is a self-extracting executable file. It starts ChessPilot directly, needs no installer or FUSE, and carries its libraries and detector model. Temporary application files are removed when it exits normally. Keep the file anywhere; no menu entry is installed. Stockfish downloads/cache live under `${XDG_DATA_HOME:-$HOME/.local/share}/chesspilot/native`, and engine options live in the enclosing `chesspilot` folder. They survive moving or replacing the executable.

For an offline first launch, place a compatible executable named `stockfish` in that `native` folder, keep its license/source notices, and make it executable. To update, close ChessPilot and replace the portable executable. Removing that file leaves your engine/settings intact. A complete bundle avoids the extraction work at startup if you prefer that format.

Release CI uses Ubuntu 22.04 as its build baseline for broader compatibility. The host still needs compatible glibc, graphics drivers and a supported display session; this does not cover every distro, Linux architecture or Wayland compositor. Use the CI-built release rather than an Arch-local build when distributing to older systems.

### AppImage

```sh
chmod +x ./ChessPilot-VERSION-linux-x86_64.AppImage
./ChessPilot-VERSION-linux-x86_64.AppImage
```

If FUSE mounting is unavailable, launch with `--appimage-extract-and-run`. The AppImage includes the same application payload and uses the same persistent user-data location as the extensionless portable executable. Replace the file to update; no system installation is required.

### Debian / Ubuntu / Mint

```sh
sudo apt install ./chesspilot_VERSION_amd64.deb
```

Open ChessPilot from the applications menu or run `chesspilot`. The package installs application files in `/opt/chesspilot`; Stockfish and options stay in your user-data folder, so the app needs no administrator privileges. Install a newer DEB to update. `sudo apt remove chesspilot` removes the application while keeping your user data. The package declares the minimum glibc required by its payload; use a release built on the documented Ubuntu baseline rather than an Arch-built DEB on older distributions.

### Optional installer

Download the single `ChessPilot-VERSION-linux-x64-setup.run` file from a published release, or extract it from the installer CI artifact. Close ChessPilot before installing or updating, then run from the download folder:

```sh
sh ./ChessPilot-VERSION-linux-x64-setup.run
```

Replace `VERSION` with the downloaded filename's version. No `sudo`, FUSE, Flutter SDK or manual library copying is needed. Setup shows extraction/integrity progress, installs under `${XDG_DATA_HOME:-$HOME/.local/share}/chesspilot/app`, and adds **ChessPilot** to your applications menu. You can also launch it directly:

```sh
"${XDG_DATA_HOME:-$HOME/.local/share}/chesspilot/app/AppRun"
```

The installer includes the Flutter/Rust libraries, ONNX Runtime, exact detector model and GTK runtime dependencies. It shares the portable app's Ubuntu 22.04 build baseline and host/display requirements.

First launch downloads a CPU-compatible Stockfish beside the installed app and reuses it on later launches. **Update:** close ChessPilot and run the newer installer; your engine, options, download cache and other user files are preserved. **Uninstall:** run an installer again with:

```sh
sh ./ChessPilot-VERSION-linux-x64-setup.run -- --uninstall
```

This removes managed application files and the menu entry. Downloaded engines, settings, caches, custom files and ownership metadata remain in the user data folder. No unrelated installation directory is replaced.

### Optional portable bundle

To use the `.tar.gz` developer/portable package instead, extract the **entire bundle** and keep all its files together:

```sh
mkdir -p ChessPilot
tar -xzf ChessPilot-linux-x64.tar.gz -C ChessPilot
cd ChessPilot
chmod +x chesspilot
./chesspilot
```

Keep `lib/`, `data/`, the model and licenses beside the executable. GTK3 and the platform's standard C/C++ runtime libraries must be available. The folder must be writable for first-launch Stockfish setup. Use a package built for your architecture; the current documented desktop artifact is x64.

- **X11:** the session must provide XTEST input. Start with the board on the primary monitor.
- **wlroots Wayland:** install `grim` and use a compositor exposing screencopy plus `zwlr_virtual_pointer_manager_v1`. On Arch, `sudo pacman -S --needed grim` installs the capture helper. Keep the normal Wayland session environment.
- **GNOME/KDE Wayland:** portal capture/control is not implemented. Use a supported session; successful installation alone does not establish automation support.

On first launch, let Stockfish setup complete. For an offline setup, place a compatible executable named `stockfish` beside `chesspilot` and make that engine executable. Preserve its license/source information.

**Portable update:** close the app, retain your existing engine/configuration/cache, and replace application files with the newer complete bundle. **Portable removal:** close the app and remove the extracted folder when you no longer need its contents; keep any settings you want to reuse.

## Android

1. Copy `app-release.apk` to the phone and open it with the file manager. If Android requests permission to install from that source, allow it specifically for the file manager/browser you are using.
2. Open ChessPilot and choose your color. Enable **ChessPilot touch control** in Android Accessibility when prompted; this lets the app tap and drag pieces.
3. Choose **Share entire display** and approve Android's screen-sharing consent. Sharing only one app can prevent the detector/input coordinates from matching the display.
4. Allow notifications when requested so running controls, Stop and Exit remain accessible. No separate general draw-over-other-apps permission is needed for the accessibility overlay.
5. Switch to the board. Tap the movable logo bubble to expand Play / Auto / Stop / Exit. Drag the bubble or panel header away from the board. While busy, tapping the collapsed Stop icon pauses moves.

Opening the dashboard or dragging the controls pauses automation. **Stop** pauses moves; **Exit** also ends sharing and closes the engine. After capture loss, screen lock or display changes, reconnect screen sharing rather than expecting old permission tokens to be reused.

**Update:** install the newer APK over the existing app using the same signing key; settings are preserved. An APK signed with a different key cannot update the installed app. Use a matching publisher build instead of uninstalling just to work around a key mismatch. **Uninstall:** Android removes the app and its private settings; export anything you need first.

## First game

Keep the whole 2D board visible and clear of the app/overlay. Choose the side you are playing, set applicable castling rights, select Click or Drag, and start **Play Next Move** or **Auto on your turn**. Use **Stop** to pause and **New game** after checkmate/stalemate. Castling rights update after confirmed moves; a screenshot cannot reveal moves made before tracking started.

The model is included on every platform. Desktop downloads Stockfish only when absent; Android packages its engine/network. Capture, detection and analysis work locally after setup. Engine tuning and defaults are in [ENGINE_CONFIG.md](ENGINE_CONFIG.md).

## If setup fails

- **Engine setup:** confirm the desktop app folder (or user-data folder for Linux portable/AppImage/DEB) is writable and first-launch downloads have internet access, or supply a compatible offline engine.
- **No board/capture:** keep the board unobstructed, check the supported Linux session or restart full-display sharing on Android.
- **No moves:** choose the correct color, start on your turn, stop Auto before manual Play, and check touch-control/capture readiness.
- **Need details:** open Help/Shortcuts → Diagnostics / logs. Desktop can open the log folder; Android can share logs. Include your app version, OS/device/display server and relevant error when reporting a problem.
