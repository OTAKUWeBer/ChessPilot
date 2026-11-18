# Install ChessPilot

Choose the package for your device. Installing a downloaded app does not require Flutter, Rust, Visual Studio, an Android SDK or ADB. If you want to compile it yourself, use [the build guide](BUILDING.md).

## Get the app

Desktop packages are attached to [successful rust-branch builds](https://github.com/OTAKUWeBer/ChessPilot/actions/workflows/native.yml?query=branch%3Arust). GitHub may require sign-in to download artifacts, and older artifacts may expire. Check that the build/version matches the one you intend to install.

| Device | Package |
| --- | --- |
| Windows x64 | `ChessPilot-windows-x64-installer` artifact; unzip it to find the setup EXE |
| Windows portable | `ChessPilot-windows-x64` artifact; unzip it, then extract the enclosed `ChessPilot-windows-x64.zip` |
| Linux x64 | `ChessPilot-linux-x64` artifact; unzip it, then extract the enclosed `.tar.gz` |
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

1. Unzip the downloaded GitHub artifact to obtain `ChessPilot-linux-x64.tar.gz`.
2. In the folder containing that archive, extract it and launch the app:

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

**Update:** close the app, retain your existing engine/configuration/cache, and replace application files with the newer complete bundle. **Remove:** close the app and remove the extracted folder when you no longer need its contents; keep any settings you want to reuse.

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

- **Engine setup:** confirm the desktop app folder is writable and first-launch downloads have internet access, or supply a compatible offline engine.
- **No board/capture:** keep the board unobstructed, check the supported Linux session or restart full-display sharing on Android.
- **No moves:** choose the correct color, start on your turn, stop Auto before manual Play, and check touch-control/capture readiness.
- **Need details:** open Help/Shortcuts → Diagnostics / logs. Desktop can open the log folder; Android can share logs. Include your app version, OS/device/display server and relevant error when reporting a problem.
