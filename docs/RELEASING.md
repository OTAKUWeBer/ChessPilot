# Release maintenance

## One version command

From the repository root, with the pinned Dart/Flutter SDK installed:

```sh
dart tool/version.dart 3.0.1+4
dart tool/version.dart --check
```

`app/pubspec.yaml` is the release authority. The helper updates the Flutter version/build, the Rust workspace version and only the two local Cargo lockfile package versions. Both Rust crates inherit the workspace version. Android and Windows derive their application versions from Flutter; the Windows installer reads the same pubspec. Do not hand-edit generated runner/Gradle version files.

The version is `MAJOR.MINOR.PATCH[-prerelease]+BUILD`. Increase BUILD for each distributed Android update. Numeric fields are bounded to fit the shared Windows file-version representation. The helper validates the complete update plan before writing and does not update dependencies. CI checks consistency and exercises the version helper. SDK/runtime pins are independent of the product version.

Product docs use version-neutral output paths, and the README source-version badge reads `app/pubspec.yaml`, so a normal bump needs no manual version-badge edits. Update the What's new highlights when release behavior changes. Installer filenames contain the release version at build time. Platform native sources, Flutter assets and Rust runtime must all come from the same revision.

## Before publishing a stable release

Run the checks in [the engineering guide](ENGINEERING.md), build all intended platforms using [the build guide](BUILDING.md), and verify the packaged model and complete payload. Desktop CI builds Windows/Linux bundles, checks real inference and validates both desktop installers. Android release assembly must also pass on the release host.

The user-facing release files are the Windows `ChessPilot-VERSION-windows-x64-setup.exe`, Linux **`ChessPilot-VERSION-linux-x86_64`** portable app, and Android `app-release.apk`. The optional Linux `ChessPilot-VERSION-linux-x64-setup.run` installs a menu launcher. Linux CI publishes separate `ChessPilot-linux-x64-portable` and `ChessPilot-linux-x64-installer` artifacts and checks both formats and relocated runtime discovery. Each one-file app/installer contains its libraries/model; do not upload loose DLLs, `.so` files or the intermediate `bundle/chesspilot` executable. Include the checksum sidecars when publishing checksums. Linux releases are built on Ubuntu 22.04; Arch-local builds are not the cross-distro release baseline.

Finish production signing (the current Windows installer is unsigned and Android release-mode APK uses a local debug key), clean-install/update checks, device/monitor coverage and sustained memory/performance/security checks. Include required dependency licenses, engine source information and model redistribution review. Platform test evidence and remaining cases stay in [TESTING.md](TESTING.md).

Publish checksums and describe the actual tested platforms and limitations. Do not publish SDK caches, personal screenshots, logs, credentials or debug signing keys. The README includes a recorded demo from `assets/`; retain its version/session context when updating it.
