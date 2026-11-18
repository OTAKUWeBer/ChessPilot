# Contributing to ChessPilot

This branch builds the standalone Flutter/Rust app. The Python reference is maintained on `main`.

Read [the build guide](docs/BUILDING.md) for Windows, Linux and Android prerequisites and [the engineering guide](docs/ENGINEERING.md) for optional integration checks.

From the repository root:

```sh
cargo fmt --manifest-path native/Cargo.toml --all --check
cargo clippy --manifest-path native/Cargo.toml --workspace --all-targets --locked -- -D warnings
cargo test --manifest-path native/Cargo.toml --workspace --locked
```

After preparing/building the desktop native runtime, run `flutter analyze` and `flutter test` from `app/`. Set `CHESSPILOT_LIBRARY_PATH` when the runtime is not at the default development path. Asset/engine/desktop integration tests are explicit opt-ins; never run input tests against an unrelated window.

Keep changes focused, preserve existing user configuration and assets, and include relevant verification and remaining platform limits in your pull request. Do not commit generated binaries, SDKs, screenshots, logs, engine downloads or signing credentials.
