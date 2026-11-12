# ChessPilot Flutter interface

Flutter renders state owned by the Rust runtime. Desktop controls retain the 380×520 layout and green/dark appearance. Android uses the full dashboard for setup/settings and a small native accessibility overlay while another app is visible.

Build the native runtime before desktop tests. Android Gradle builds/packages its ARM64 native components; Stockfish assets must be prepared first. See [migration progress](../README.md), [Android setup](../android-testing.md), [Linux setup](../linux-testing.md) and [phone overlay design](../../docs/phone-overlay-plan.md).

`native_client.dart` owns C ABI buffers, `pilot_controller.dart` manages snapshots/polling and `android_platform.dart` connects Android setup/lifecycle. Android's process-owned session survives Activity recreation; desktop closes its session on controller disposal. Physical-platform acceptance remains separate from widget/channel tests.
