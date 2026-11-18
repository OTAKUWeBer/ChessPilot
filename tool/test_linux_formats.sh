#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
appimage="$(realpath -e -- "$1")"
deb="$(realpath -e -- "$2")"
version="$(sed -nE 's/^version: *([^+]+)\+[0-9]+ *$/\1/p' "$repo/app/pubspec.yaml")"
mkdir -p "$repo/native/target"
work="$(mktemp -d "$repo/native/target/linux-formats-test.XXXXXX")"
[[ "$work" = "$repo"/native/target/linux-formats-test.* ]] || exit 1
trap 'rm -rf -- "$work"' EXIT
for artifact in "$appimage" "$deb"; do
  (cd -- "$(dirname -- "$artifact")" && sha256sum -c "$(basename -- "$artifact").sha256")
done
# Exercise the real runtime without depending on FUSE or installing into the host.
env -u CHESSPILOT_DATA_HOME -u CHESSPILOT_ENGINE_HOME XDG_DATA_HOME="$work/profile" \
  xvfb-run -a "$appimage" --appimage-extract-and-run --help
mkdir "$work/image"
(cd "$work/image" && "$appimage" --appimage-extract >/dev/null)
image="$work/image/squashfs-root"
[ -f "$image/.chesspilot-portable" ]
CHESSPILOT_BUNDLE_TEST="$image" cargo test --manifest-path "$repo/native/Cargo.toml" --test resources relocated_bundle_resolves_default_assets_without_checkout_paths -- --ignored

[ "$(dpkg-deb -f "$deb" Package)" = chesspilot ]
[ "$(dpkg-deb -f "$deb" Version)" = "${version/-/~}" ]
[ "$(dpkg-deb -f "$deb" Architecture)" = amd64 ]
dpkg-deb -x "$deb" "$work/deb"
installed="$work/deb/opt/chesspilot"
[ -f "$installed/.chesspilot-portable" ]
grep -Fqx 'exec /opt/chesspilot/AppRun "$@"' "$work/deb/usr/bin/chesspilot"
desktop-file-validate "$work/deb/usr/share/applications/io.github.otakuweber.chesspilot.desktop"
env -u CHESSPILOT_DATA_HOME -u CHESSPILOT_ENGINE_HOME XDG_DATA_HOME="$work/profile" \
  xvfb-run -a "$installed/AppRun" --help
CHESSPILOT_BUNDLE_TEST="$installed" cargo test --manifest-path "$repo/native/Cargo.toml" --test resources relocated_bundle_resolves_default_assets_without_checkout_paths -- --ignored
for payload in "$image" "$installed"; do
  expected="$(cut -d' ' -f1 "$repo/assets/models/chess_detection.onnx.sha256")"
  printf '%s  %s\n' "$expected" "$payload/chess_detection.onnx" | sha256sum -c -
  [ ! -e "$payload/stockfish" ] && [ ! -e "$payload/engine_config.txt" ]
done
[ ! -e "$work/profile/applications/io.github.otakuweber.chesspilot.desktop" ]
printf 'AppImage and Debian package checks passed.\n'
