# Linux setup and verification

Native X11 and the existing wlroots Wayland path connect to shared Play/Auto. The [beta Ubuntu CI run](https://github.com/OTAKUWeBer/ChessPilot/actions/runs/44147469834) passed the complete Linux GTK bundle build, regressions, real ONNX/refined-search parity and an Xvfb X11 capture/capability probe. Protocol fixtures also exercise a fake compositor. The maintainer reports working Linux gameplay and castling on November 18, 2026. CI does not establish physical Wayland calibration on other machines.

## Build prerequisites

Commands and output paths start in the Rust project root, the folder containing `app/`, `native/` and `tool/`. On November 18, 2026, the maintainer reported working Linux gameplay and castling. Broader compositor/monitor combinations still need coverage.

For `Wrong full snapshot version`, use [the one-session Arch recovery/build recipe](docs/BUILDING.md#one-session-arch-build--snapshot-error-recovery). It bypasses the broken global SDK and records `native/target/linux-build-report.log`. Flutter is pinned to 3.38.6 in `app/.fvmrc`; the app version remains 3.0.0-beta.1/build 2 on both desktops.

Follow the [complete build guide](docs/BUILDING.md#linux-x64-including-arch) for Ubuntu/Arch packages, Flutter/Rust prerequisites, release build/run commands and archive output. This page covers runtime acceptance. Check `flutter doctor -v` before building.

Provide these native resources:

* Stockfish is checked beside the executable and automatically downloaded there when missing. Use a writable app folder. For offline startup, put a CPU-compatible Linux `stockfish` executable beside the app with execute permission; include its license/source information. Explicit native engine paths are also supported. The Windows `.exe` cannot be reused on Linux.
* The existing `assets/models/chess_detection.onnx` model.
* Prepare the pinned native ONNX Runtime with `cmake -P tool/prepare_desktop.cmake`, then build with Flutter as described in [desktop builds](desktop-building.md). CMake includes the exact Python model, native runtime, ONNX Runtime and licenses in the bundle; the Rust process does not start Python. A manual development launch can instead provide `libonnxruntime.so` under `src/`.
* On X11, an accessible X server with XTEST; RandR 1.5 selects the primary monitor, with a root-screen fallback on older servers.
* On supported wlroots Wayland desktops, `grim` on PATH and a compositor exposing screencopy plus `zwlr_virtual_pointer_manager_v1`. Normal `XDG_RUNTIME_DIR`/`WAYLAND_DISPLAY` settings must be preserved. GNOME/KDE portal-based capture/control is pending, so those Wayland sessions may report unsupported capability.

From the Rust project root:

```sh
cargo build --manifest-path native/Cargo.toml -p chesspilot-runtime
cargo test --manifest-path native/Cargo.toml --workspace
cd app
flutter pub get
flutter run -d linux
```

The development loader finds `native/target/debug/libchesspilot_runtime.so`. `CHESSPILOT_LIBRARY_PATH` can select an explicit compiled runtime library. Keep all native components from the same revision.

## Probe capture without moving the mouse

From the Rust project root on the actual desktop:

```sh
CHESSPILOT_LINUX_CAPTURE_TEST=1 cargo test \
  --manifest-path native/Cargo.toml -p chesspilot-runtime \
  --test linux_live -- --ignored --nocapture
```

This opens the capture and input protocol connections, captures two frames and prints dimensions/origin. It sends no tap, drag or pointer motion and writes no screenshot. Keep the mouse button released during capability initialization.

## Interactive check

Use a local test board with the whole board visible and the ChessPilot window beside it. On X11, start on the primary monitor. On Wayland, capture uses the full layout at logical scale; custom compositor mapping of virtual devices can change input coordinates and needs calibration.

1. Choose the actual bottom-side color and request one move on that side's turn. Check both drag and click modes.
2. Confirm the visible board changes before `Move Played` appears; test both enabling Auto directly on your turn and resuming after a verified manual move.
3. Leave the board unchanged: Auto should wait. Make one legal opponent move: it should answer once. Stop it while waiting and during analysis.
4. Check both orientations, zoom, monitor/scale changes, captures, both castling sides and all promotions on the controlled board. An unreadable or changed source must pause rather than blindly repeat input.
5. Check that the desktop window starts at 380×520 and stays above other windows. Wayland may require a compositor window rule for keep-above.

The initial manual position still uses the selected color and placement-based history assumptions inherited from Python. Escape and reselect the color when changing games/boards. Linux build rules preserve the portable Stockfish/config/cache across rebuilds and replace generated Flutter assets. The complete GTK bundle builds in CI. Relocated Linux runtime behavior, sustained-play acceptance and portal support remain unverified or unfinished; Android device checks are separate.
