#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo"
mkdir -p native/target
report="$repo/native/target/linux-build-report.log"
exec > >(tee "$report") 2>&1
printf 'Build report: %s\n' "$report"
date -u
git status --short --branch
type -a flutter dart || true
for tool in git curl unzip cmake clang ninja pkg-config rustup; do
  if ! command -v "$tool" >/dev/null; then
    echo "Missing build tool: $tool. Install the prerequisites in docs/BUILDING.md." >&2
    exit 1
  fi
done
rustup toolchain install 1.92.0 --profile minimal
export RUSTUP_TOOLCHAIN=1.92.0
cargo --version
cmake --version
cmake -P tool/prepare_desktop.cmake
bash tool/flutter_linux.sh --version
# Android/Chrome doctor warnings do not prevent a Linux desktop build.
bash tool/flutter_linux.sh doctor -v || true
bash tool/flutter_linux.sh pub get
bash tool/flutter_linux.sh build linux --release
printf '\nBuilt: %s/app/build/linux/x64/release/bundle/chesspilot\n' "$repo"
