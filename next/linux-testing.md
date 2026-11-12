# Linux setup and verification

The source now contains native X11 and the existing wlroots Wayland path, connected to shared Play/Auto. It was compile/lint checked for Linux and tested against synthetic frames and a fake compositor on Windows. You will test the actual Linux desktop later; these checks do not claim that live verification has happened.

## Build prerequisites

Install Rust and Flutter's [Linux desktop prerequisites](https://docs.flutter.dev/platform-integration/linux/setup), then check `flutter doctor -v`.

Provide these native resources:

* A Linux `stockfish` executable on PATH or at `src/stockfish` with execute permission. The Windows `.exe` cannot be reused on Linux.
* The existing `src/chess_detection.onnx` model.
* A compatible ONNX Runtime 1.20 CPU shared library, named `libonnxruntime.so` under `src/` for development. Include any native libraries its distribution requires. Release bundling is still migration work; the Rust process does not start Python.
* On X11, an accessible X server with XTEST; RandR 1.5 selects the primary monitor, with a root-screen fallback on older servers.
* On supported wlroots Wayland desktops, `grim` on PATH and a compositor exposing screencopy plus `zwlr_virtual_pointer_manager_v1`. Normal `XDG_RUNTIME_DIR`/`WAYLAND_DISPLAY` settings must be preserved. GNOME/KDE portal-based capture/control is pending, so those Wayland sessions may report unsupported capability.

From the repository root:

```sh
cargo build --manifest-path next/native/Cargo.toml -p chesspilot-runtime
cargo test --manifest-path next/native/Cargo.toml --workspace
cd next/app
flutter pub get
flutter run -d linux
```

The development loader finds `next/native/target/debug/libchesspilot_runtime.so`. `CHESSPILOT_LIBRARY_PATH` can select an explicit compiled runtime library. Keep all native components from the same revision.

## Probe capture without moving the mouse

From the repository root on the actual desktop:

```sh
CHESSPILOT_LINUX_CAPTURE_TEST=1 cargo test \
  --manifest-path next/native/Cargo.toml -p chesspilot-runtime \
  --test linux_live -- --ignored --nocapture
```

This opens the capture and input protocol connections, captures two frames and prints dimensions/origin. It sends no tap, drag or pointer motion and writes no screenshot. Keep the mouse button released during capability initialization.

## Interactive check

Use a local test board with the whole board visible and the ChessPilot window beside it. On X11, start on the primary monitor. On Wayland, capture uses the full layout at logical scale; custom compositor mapping of virtual devices can change input coordinates and needs calibration.

1. Choose the actual bottom-side color and request one move on that side's turn. Check both drag and click modes.
2. Confirm the visible board changes before `Move Played` appears; enable Auto only after a verified manual move.
3. Leave the board unchanged: Auto should wait. Make one legal opponent move: it should answer once. Stop it while waiting and during analysis.
4. Check both orientations, zoom, monitor/scale changes, captures, both castling sides and all promotions on the controlled board. An unreadable or changed source must pause rather than blindly repeat input.
5. Check that the desktop window starts at 380×520 and stays above other windows. Wayland may require a compositor window rule for keep-above.

The initial manual position still uses the selected color and placement-based history assumptions inherited from Python. Escape and reselect the color when changing games/boards. A complete packaged build, sustained-play acceptance, portal support and Android services remain unfinished.
