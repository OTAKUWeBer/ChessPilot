# Release maintenance

## One version command

From the repository root, with the pinned Dart/Flutter SDK installed:

```sh
dart tool/version.dart 3.0.1+4
dart tool/version.dart --check
```

`app/pubspec.yaml` is the release authority. The helper updates the Flutter version/build, the Rust workspace version and only the two local Cargo lockfile package versions. Both Rust crates inherit the workspace version. Android and Windows derive their application versions from Flutter; the Windows installer reads the same pubspec. Do not hand-edit generated runner/Gradle version files.

The version is `MAJOR.MINOR.PATCH[-prerelease]+BUILD`. Increase BUILD for each distributed Android update. Numeric fields are bounded to fit the shared Windows file-version representation. The helper validates the complete update plan before writing and does not update dependencies. CI checks consistency and exercises the version helper. SDK/runtime pins are independent of the product version.

Product docs use version-neutral output paths, and the README release badge reads GitHub's latest stable release, so a normal bump needs no manual version-badge edits. Update the What's new highlights when release behavior changes. Installer filenames contain the release version at build time. Platform native sources, Flutter assets and Rust runtime must all come from the same revision.

The README CodeFactor badge explicitly targets `main`. In CodeFactor repository Settings, choose `main` as the default branch, and enable its inspection under Branches. GitHub branch renaming alone does not establish that CodeFactor is analyzing the new application. Check that its latest reviewed revision matches the intended source before citing a grade; GitHub CI remains the build/test gate.

## Before publishing a stable release

Run the checks in [the engineering guide](ENGINEERING.md), build all intended platforms using [the build guide](BUILDING.md), and verify the packaged model and complete payload. Desktop CI builds Windows/Linux bundles, checks real inference and validates both desktop installers. Android release assembly must also pass on the release host.

The release assets are the Windows `ChessPilot-VERSION-windows-x64-setup.exe` and `ChessPilot-VERSION-windows-x64.zip`, Android `ChessPilot-VERSION-android-{armv7,arm64,x86_64,universal}.apk`, and Linux `ChessPilot-VERSION-linux-x86_64`, `ChessPilot-VERSION-linux-x86_64.AppImage`, `chesspilot_VERSION_amd64.deb` and optional `ChessPilot-VERSION-linux-x64-setup.run`. Use the release notes in [releases/3.0.0.md](releases/3.0.0.md).

Build all intended platforms from the release revision. Linux release artifacts must come from the Ubuntu 22.04 CI build, not an Arch-local build. CI checks the portable app, installer, AppImage and DEB, including checksums, GTK startup and relocated model/runtime discovery. Keep checksums and build-info files locally for verification; upload only the intended app packages, without `.sha256` sidecars. Never upload loose DLLs, `.so` files, personal engines/configuration, imported helper scripts or the intermediate Linux `bundle/chesspilot` executable.

Build Android variants with `tool/build_android.ps1`; it checks that every APK has all native components for its declared ABIs. APK variants must share the same signing identity. Packaging changes do not prove that Google Play Protect or manufacturer-specific accessibility restrictions are resolved; complete device acceptance before publishing.

Keep local artifacts under ignored `dist/VERSION/windows`, `dist/VERSION/linux` and `dist/VERSION/android` folders. An imported package is a build candidate until its checksum, architecture, version, library baseline and payload have been checked. Published asset names must match the release revision and version. The source remains in Git; binaries belong in GitHub Releases.

Finish production signing (the current Windows installer is unsigned and Android release-mode APK uses a local debug key), clean-install/update checks, device/monitor coverage and sustained memory/performance/security checks. Include required dependency licenses, engine source information and model redistribution review. Platform test evidence and remaining cases stay in [TESTING.md](TESTING.md).

Describe the actual tested platforms and limitations in the release notes. GitHub records uploaded asset digests; standalone checksum files are not release assets. Do not publish SDK caches, personal screenshots, logs, credentials or debug signing keys. The README includes a recorded demo from `assets/`; retain its version/session context when updating it.
