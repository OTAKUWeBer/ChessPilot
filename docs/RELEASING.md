# Release maintenance

## One version command

From the repository root, with the pinned Dart/Flutter SDK installed:

```sh
dart tool/version.dart 3.0.1+4
dart tool/version.dart --check
```

`app/pubspec.yaml` is the release authority. The helper updates the Flutter version/build, the Rust workspace version and only the two local Cargo lockfile package versions. Both Rust crates inherit the workspace version. Android and Windows derive their application versions from Flutter; the Windows installer reads the same pubspec. Do not hand-edit generated runner/Gradle version files.

The version is `MAJOR.MINOR.PATCH[-prerelease]+BUILD`. Increase BUILD for each distributed Android update. Numeric fields are bounded to fit the shared Windows file-version representation. The helper validates the complete update plan before writing and does not update dependencies. CI checks consistency and exercises the version helper. SDK/runtime pins are independent of the product version.

Product docs use version-neutral output paths, so a normal bump needs no README edits. Installer filenames contain the release version at build time. Platform native sources, Flutter assets and Rust runtime must all come from the same revision.

## Before publishing a stable release

Run the checks in [the engineering guide](ENGINEERING.md), build all intended platforms using [the build guide](BUILDING.md), and verify the packaged model and complete payload. Desktop CI builds Windows/Linux bundles, checks real inference and validates the Windows installer. Android release assembly must also pass on the release host.

Finish production signing (the current Windows installer is unsigned and Android release-mode APK uses a local debug key), clean-install/update checks, device/monitor coverage and sustained memory/performance/security checks. Include required dependency licenses, engine source information and model redistribution review. Platform test evidence and remaining cases stay in [TESTING.md](TESTING.md).

Publish checksums and describe the actual tested platforms and limitations. Do not publish SDK caches, personal screenshots, logs, credentials or debug signing keys. No trailer or demo media is currently included; add that separately when it is ready.
