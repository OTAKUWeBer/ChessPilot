# Windows installer

Commands and output paths in this guide are relative to the Rust project root, the folder containing `app/`, `native/` and `tool/`.

Users download **one `ChessPilot-<version>-windows-x64-setup.exe`**. Setup installs the Flutter engine, Rust runtime, ONNX Runtime, the exact Python model, Microsoft C++ runtime DLLs, Flutter assets and licenses together. Start menu and optional desktop shortcuts launch `chesspilot.exe`; users do not need to manage its supporting files.

The installed app still needs those DLLs/assets. This is a single installer download, not a statically linked, standalone portable executable. It does not extract a fresh app into a temporary directory on every launch.

## Build

First build the full Windows release as described in [the build guide](../../docs/BUILDING.md#windows-x64). Install [Inno Setup 6.3 or newer](https://jrsoftware.org/inno-setup) on the build machine. This is a build dependency, not something users install.

From the Rust project root:

```powershell
./tool/build_windows_installer.ps1
```

The builder finds `ISCC.exe` on PATH or in the usual Inno Setup 6 install folders. A custom compiler path can be supplied with `-IsccPath`. It checks the release executable's version/architecture, required runtime files and the bundled model checksum before compiling. The version comes from `app/pubspec.yaml`.

Output:

```text
app/build/windows/installer/ChessPilot-3.0.0-beta.1-windows-x64-setup.exe
```

The GitHub Actions Windows job also builds and smoke-tests it, then uploads a separate **ChessPilot-windows-x64-installer** artifact. The portable bundle remains available separately. GitHub Actions wraps artifacts in ZIP downloads; the installer artifact contains one setup EXE.

## Install, update and uninstall

- Windows 10 build 17763 or newer, with x64 execution support. Native Windows x64 is the tested build; ARM64 emulation is not verified.
- Per-user installation defaults to `%LOCALAPPDATA%\Programs\ChessPilot`, without requesting administrator access. The first install lets users choose another writable folder, including a folder on X:.
- The Start menu shortcut is created automatically; the desktop shortcut is optional. Finish can launch the app. Silent installation does not launch it.
- Stockfish is not copied from the developer's machine. First launch checks/downloads the correct compatible official engine into the installed app folder. Subsequent launches and reinstalls reuse it.
- The payload includes only the executable, DLLs, model, Flutter assets and licenses. It excludes local engine options, Stockfish, download caches and logs.
- The stable installer identity supports in-place updates. Existing engine/configuration/cache files are preserved. Setup can ask to close the app when its installed files are in use.
- Uninstall removes installer-owned application files, its shortcut and uninstall registration. User-created engine/settings/cache files and existing user log directories are preserved; remove those yourself only if you want to discard them.

The beta installer is **unsigned**. Authenticode signing requires the publisher's certificate and remains a release task. No installer source change can supply a trusted publisher identity by itself.

## Verify packaging

```powershell
./tool/test_windows_installer.ps1
```

This builds a separate **ChessPilot Installer Test** identity, installs into an ignored workspace directory with spaces in its path, checks DLL/model hashes and the Start menu shortcut, and confirms developer-local engine/config/cache files were excluded. It then creates user-owned sentinel files, reinstalls, verifies their contents, uninstalls and checks cleanup/preservation. It never launches the app or downloads Stockfish. The test refuses an existing test registration rather than modifying it. It does not install over a real ChessPilot installation. Logs and fixtures remain under `native/target/windows-installer-smoke/`.

The local smoke check passed. Fresh Windows-machine gameplay, SmartScreen reputation and signing acceptance remain separate from this packaging check.
