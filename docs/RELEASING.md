# Release maintenance

## One version command

From the repository root, with the pinned Dart/Flutter SDK installed:

```sh
dart tool/version.dart 3.1.0+5
dart tool/version.dart --check
```

`app/pubspec.yaml` is the release authority. The helper updates the Flutter version/build, the Rust workspace version and only the two local Cargo lockfile package versions. Both Rust crates inherit the workspace version. Android and Windows derive their application versions from Flutter; the Windows installer reads the same pubspec. Do not hand-edit generated runner/Gradle version files.

The version is `MAJOR.MINOR.PATCH[-prerelease]+BUILD`. Increase BUILD for each distributed Android update. Numeric fields are bounded to fit the shared Windows file-version representation. The helper validates the complete update plan before writing and does not update dependencies. CI checks consistency and exercises the version helper. SDK/runtime pins are independent of the product version.

Product docs use version-neutral output paths, and the README release badge reads GitHub's latest stable release, so a normal bump needs no manual version-badge edits. Update the What's new highlights when release behavior changes. Installer filenames contain the release version at build time. Platform native sources, Flutter assets and Rust runtime must all come from the same revision.

The README CodeFactor badge explicitly targets `main`. In CodeFactor repository Settings, choose `main` as the default branch, and enable its inspection under Branches. GitHub branch renaming alone does not establish that CodeFactor is analyzing the new application. Check that its latest reviewed revision matches the intended source before citing a grade; GitHub CI remains the build/test gate.

## Before publishing a stable release

Run the checks in [the engineering guide](ENGINEERING.md), build all intended platforms using [the build guide](BUILDING.md), and verify the packaged model and complete payload. Desktop CI builds Windows/Linux bundles, checks real inference and validates both desktop installers. Android release assembly must also pass on the release host.

The release assets are the Windows `ChessPilot-VERSION-windows-x64-setup.exe` and `ChessPilot-VERSION-windows-x64.zip`, Android `ChessPilot-VERSION-android-{armv7,arm64,x86_64,universal}.apk`, and Linux `ChessPilot-VERSION-linux-x86_64`, `ChessPilot-VERSION-linux-x86_64.AppImage`, `chesspilot_VERSION_amd64.deb` and optional `ChessPilot-VERSION-linux-x64-setup.run`. Use the release notes in [releases/3.1.0.md](releases/3.1.0.md).

Build all intended platforms from the release revision. Linux release artifacts must come from the Ubuntu 22.04 CI build, not an Arch-local build. CI checks the portable app, installer, AppImage and DEB, including checksums, GTK startup and relocated model/runtime discovery. Keep checksums and build-info files locally for verification; upload only the intended app packages, without `.sha256` sidecars. Never upload loose DLLs, `.so` files, personal engines/configuration, imported helper scripts or the intermediate Linux `bundle/chesspilot` executable.

Build Android variants with `tool/build_android.ps1`; it checks that every APK has all native components for its declared ABIs. APK variants must share the same signing identity. Packaging changes do not prove that Google Play Protect or manufacturer-specific accessibility restrictions are resolved; complete device acceptance before publishing.

For CI builds, manually run **Rust and Flutter desktop** with `build_android=true`. The Android job creates all four candidate APKs and verifies their payloads using a temporary runner development key. Do not publish these directly: re-sign each with the retained maintainer key locally using `apksigner sign --out FINAL_APK --ks PRIVATE_KEYSTORE INPUT_APK`, then rerun `tool/test_android_packages.ps1` on the final directory. Compare the final certificate SHA-256 to the existing release before accepting an update build. Keep private keys out of CI artifacts. A freshly generated runner key cannot update the installed release.

Keep local artifacts under ignored `dist/VERSION/windows`, `dist/VERSION/linux` and `dist/VERSION/android` folders. An imported package is a build candidate until its checksum, architecture, version, library baseline and payload have been checked. Published asset names must match the release revision and version. The source remains in Git; binaries belong in GitHub Releases.

Finish production signing (the current Windows installer is unsigned and existing Android APKs use a local debug key), clean-install/update checks, device/monitor coverage and sustained memory/performance/security checks. Include required dependency licenses, engine source information and model redistribution review. Platform test evidence and remaining cases stay in [TESTING.md](TESTING.md).

Describe the actual tested platforms and limitations in the release notes. GitHub records uploaded asset digests; standalone checksum files are not release assets. Do not publish SDK caches, personal screenshots, logs, credentials or debug signing keys. The README includes a recorded demo from `assets/`; retain its version/session context when updating it.

## Android signing and Google review

These are three separate requirements: APK signing identifies updates, Android developer verification establishes publisher identity, and Play Protect evaluates app risk. None substitutes for the others. Google documents the reported financial-fraud warning for internet-sideloaded apps using sensitive access including Accessibility. ChessPilot needs user-enabled Accessibility gestures for touch control; changing the signing key does not guarantee removal of that block. See [Google's warning guidance](https://developers.google.com/android/play-protect/warning-dev-guidance).

### Publisher signing

Create a dedicated, private signing key using Android Studio's signing wizard or the JDK's interactive `keytool`. Keep the password out of command-line arguments, chat and Git. For example, after creating a private directory outside this checkout:

```powershell
keytool -genkeypair -v -keystore X:/private-signing/chesspilot-release.jks -alias chesspilot -keyalg RSA -keysize 3072 -validity 10000
```

Copy `app/android/key.properties.example` to `app/android/key.properties` and fill in the real absolute path, alias and passwords locally. Use forward slashes in paths. Gradle validates all four fields and the keystore path; the signing task validates the key/passwords. Both the real properties file and keystores are ignored. Back up the key and credentials securely outside the repo; losing the key can prevent future updates. Never upload them as release assets.

`tool/build_android.ps1` requires this configuration by default. `-AllowDevelopmentSigning` explicitly retains local debug signing for compatibility testing only. Do not use that option for publisher builds. The currently distributed 3.0.0 and locally built 3.0.1 APKs share the old debug certificate. A new unrelated publisher key cannot silently update them: plan and test migration before replacing public APKs, and preserve user data. Do not delete the old key. See [Android's signing and update rules](https://developer.android.com/studio/publish/app-signing).

### Developer identity verification

Use [Android Developer Console](https://developer.android.com/developer-verification/guides/android-developer-console) for distribution exclusively outside Play, or [Play Console](https://developer.android.com/developer-verification/guides/google-play-console) for Play distribution. Complete the publisher's account verification and package/signing-key registration for `io.github.otakuweber.chesspilot`. Account options and regional rollout change; follow the [current official verification guide](https://developer.android.com/developer-verification). Identity verification alone does not establish Play Protect approval.

### Play Protect appeal

Use the exact APK that produced the block; rebuilding or re-signing produces a different hash. Record its filename, SHA-256 (`Get-FileHash -Algorithm SHA256 PATH_TO_APK`), certificate SHA-256 (`apksigner verify --print-certs PATH_TO_APK`), version, download URL, affected Android version/region and warning screenshot. Keep the matching source revision. The [official appeal form](https://support.google.com/googleplay/android-developer/contact/protectappeals) currently requests the APK SHA-256 of the file uploaded to VirusTotal; the publisher should review and upload the intended distributable artifact, then follow the form. Do not upload signing material or private diagnostic data.

Suggested additional information, after confirming it matches the submitted build:

> ChessPilot is an open-source chess-board automation utility. Package: io.github.otakuweber.chesspilot. Source: https://github.com/OTAKUWeBer/ChessPilot. The reported warning is the sensitive-data/financial-fraud installation block. Accessibility is explicitly enabled by the user and used to perform chess-piece taps/drags after the user starts Play or Auto. Stockfish selects moves from the captured board; Play requests one move and Auto continues selecting and performing moves on the user's turn until stopped. The service declares canPerformGestures=true, canRetrieveWindowContent=false and isAccessibilityTool=false. It does not process accessibility events or retrieve window text. Board screenshots use a separate, visible MediaProjection foreground service with Android screen-sharing consent and are processed locally. Stop pauses automation; Exit ends the capture session. The app does not request SMS, contacts, call-log or notification-listener access. Please review the classification of the exact APK identified by the supplied SHA-256. Device/Android version, distribution URL, source revision and screenshots are attached separately.

Google Play distribution also requires an Accessibility API declaration and review. Its [automation policy](https://support.google.com/googleplay/android-developer/answer/10964491) restricts autonomous planning/execution and distinguishes static human-defined scripts. Our engine-selected Auto behavior could fall within that restriction; this is a policy-risk inference, not a Google decision. Do not describe it as merely replaying a fixed script or promise Play acceptance. Publisher identity verification and the sideloaded Play Protect appeal are separate processes.

Only claim behavior actually checked in the submitted artifact. This is an appeal draft, not evidence that Google approved the app or that the complete app passed a security audit. Submission uses the publisher's contact information; completing identity checks and receiving Google's decision cannot be automated by changing code. An installation performed with scanning temporarily disabled is not evidence of successful Play Protect review. Do not falsely declare the app an accessibility tool to avoid the warning. Android's per-app restricted-settings consent remains separate; see [installation guidance](INSTALLING.md#android-installation-and-restricted-settings).
