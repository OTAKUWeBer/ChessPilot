#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
mkdir -p "$repo/native/target"
testroot="$(mktemp -d "$repo/native/target/linux-installer-test.XXXXXX")"
[[ "$testroot" = "$repo"/native/target/linux-installer-test.* ]] || exit 1
trap 'rm -rf -- "$testroot"' EXIT
payload="$testroot/payload"
data="$testroot/data with spaces"
app="$data/chesspilot/app"
desktop="$data/applications/io.github.otakuweber.chesspilot.desktop"
mkdir -p "$payload/AppDir/lib" "$payload/AppDir/data" "$payload/AppDir/apprun-hooks"
cp "$repo/packaging/linux/install.sh" "$payload/install.sh"
cp "$repo/packaging/linux/AppRun" "$payload/AppDir/AppRun"
cat > "$payload/AppDir/chesspilot" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = --help ]; then echo 'fixture help'; exit 0; fi
printf '%s\n' "$LD_LIBRARY_PATH" "${WAYLAND_DISPLAY:-}" "${XDG_RUNTIME_DIR:-}" "${PACKAGE_HOOK:-}" "$@" > "$CHESSPILOT_PACKAGE_TEST_TRACE"
printf 'bundle=%s\nprofile=%s\nengine=%s\n' "$APPDIR" "${CHESSPILOT_DATA_HOME:-}" "${CHESSPILOT_ENGINE_HOME:-}" >> "$CHESSPILOT_PACKAGE_TEST_TRACE"
if [ -n "${CHESSPILOT_ENGINE_HOME:-}" ]; then
  mkdir -p "$CHESSPILOT_ENGINE_HOME"
  [ -f "$CHESSPILOT_ENGINE_HOME/stockfish" ] || printf 'engine\n' > "$CHESSPILOT_ENGINE_HOME/stockfish"
  [ -f "$CHESSPILOT_DATA_HOME/engine_config.txt" ] || printf 'options\n' > "$CHESSPILOT_DATA_HOME/engine_config.txt"
fi
EOF
printf 'export PACKAGE_HOOK=loaded\n' > "$payload/AppDir/apprun-hooks/test.sh"
printf 'model\n' > "$payload/AppDir/chess_detection.onnx"
printf 'old library\n' > "$payload/AppDir/lib/old.so"
chmod +x "$payload/install.sh" "$payload/AppDir/AppRun" "$payload/AppDir/chesspilot"
install_fixture() { XDG_DATA_HOME="$data" bash "$payload/install.sh" "$@"; }
install_fixture
[ -x "$app/AppRun" ] && [ -f "$desktop" ]
grep -Fqx "Exec=\"$app/AppRun\"" "$desktop"
CHESSPILOT_PACKAGE_TEST_TRACE="$testroot/trace" WAYLAND_DISPLAY=wayland-test XDG_RUNTIME_DIR="$testroot/runtime" "$app/AppRun" 'argument with spaces'
grep -Fqx "$app/lib:$app/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$testroot/trace"
grep -qx wayland-test "$testroot/trace"
grep -Fqx "$testroot/runtime" "$testroot/trace"
grep -qx loaded "$testroot/trace"
grep -qx 'argument with spaces' "$testroot/trace"

printf 'user engine\n' > "$app/stockfish"
printf 'custom options\n' > "$app/engine_config.txt"
mkdir "$app/download-cache"
printf 'cached download\n' > "$app/download-cache/user.archive"
printf 'user file\n' > "$app/my-note.txt"
rm "$payload/AppDir/lib/old.so"
printf 'new library\n' > "$payload/AppDir/lib/new.so"
install_fixture
[ ! -e "$app/lib/old.so" ] && [ -f "$app/lib/new.so" ]
grep -qx 'user engine' "$app/stockfish"
grep -qx 'custom options' "$app/engine_config.txt"
grep -qx 'cached download' "$app/download-cache/user.archive"
grep -qx 'user file' "$app/my-note.txt"

printf 'sentinel\n' > "$testroot/sentinel"
cp "$app/.chesspilot-package-files" "$testroot/manifest"
printf './../../../sentinel\n' >> "$app/.chesspilot-package-files"
if install_fixture --uninstall; then echo 'Unsafe manifest accepted' >&2; exit 1; fi
[ -f "$app/chess_detection.onnx" ] && grep -qx sentinel "$testroot/sentinel"
cp "$testroot/manifest" "$app/.chesspilot-package-files"
mkdir -p "$testroot/outside"
printf 'outside\n' > "$testroot/outside/file"
ln -s "$testroot/outside" "$app/escape"
if [ -L "$app/escape" ]; then
  printf './escape/file\n' >> "$app/.chesspilot-package-files"
  if install_fixture --uninstall; then echo 'Escaping symlink accepted' >&2; exit 1; fi
  grep -qx outside "$testroot/outside/file"
  rm "$app/escape"
else
  printf 'Directory symlink check requires native symlink support; Linux CI runs it.\n'
  rm -rf -- "$app/escape"
fi
cp "$testroot/manifest" "$app/.chesspilot-package-files"

mkdir "$data/chesspilot/.setup-lock"
if install_fixture; then echo 'Concurrent installer accepted' >&2; exit 1; fi
rmdir "$data/chesspilot/.setup-lock"
install_fixture --uninstall
[ ! -e "$desktop" ] && [ ! -e "$app/chesspilot" ] && [ ! -e "$app/lib/new.so" ]
grep -qx 'user engine' "$app/stockfish"
grep -qx 'custom options' "$app/engine_config.txt"
grep -qx 'user file' "$app/my-note.txt"
install_fixture
[ -f "$desktop" ] && [ -f "$app/chesspilot" ]
cp "$app/.chesspilot-package-files" "$testroot/manifest"
mv "$payload/AppDir/chess_detection.onnx" "$testroot/model"
if install_fixture; then echo 'Incomplete payload accepted' >&2; exit 1; fi
cmp "$testroot/manifest" "$app/.chesspilot-package-files"
mv "$testroot/model" "$payload/AppDir/chess_detection.onnx"
mkdir -p "$testroot/unrelated/chesspilot/app"
printf 'keep\n' > "$testroot/unrelated/chesspilot/app/file"
if XDG_DATA_HOME="$testroot/unrelated" bash "$payload/install.sh"; then echo 'Unrelated folder overwritten' >&2; exit 1; fi
grep -qx keep "$testroot/unrelated/chesspilot/app/file"

makeself="${CHESSPILOT_MAKESELF:-$(command -v makeself || true)}"
if [ -n "$makeself" ]; then
  "$makeself" --nox11 --sha256 --nomd5 --nocrc "$payload" "$testroot/fixture.run" 'ChessPilot fixture' ./install.sh
  sh "$testroot/fixture.run" --check
  XDG_DATA_HOME="$testroot/from-archive" sh "$testroot/fixture.run"
  [ -f "$testroot/from-archive/chesspilot/app/chess_detection.onnx" ]
  XDG_DATA_HOME="$testroot/from-archive" sh "$testroot/fixture.run" -- --uninstall

  touch "$payload/AppDir/.chesspilot-portable"
  "$makeself" --nox11 --sha256 --nomd5 --nocrc "$payload/AppDir" "$testroot/ChessPilot-linux-x86_64" 'ChessPilot portable fixture' ./AppRun
  for launch in 1 2; do
    env -u CHESSPILOT_DATA_HOME -u CHESSPILOT_ENGINE_HOME XDG_DATA_HOME="$testroot/portable-profile" \
      CHESSPILOT_PACKAGE_TEST_TRACE="$testroot/portable-trace" \
      sh "$testroot/ChessPilot-linux-x86_64" -- 'argument with spaces'
    grep -Fqx "profile=$testroot/portable-profile/chesspilot" "$testroot/portable-trace"
    grep -Fqx "engine=$testroot/portable-profile/chesspilot/native" "$testroot/portable-trace"
    grep -qx 'argument with spaces' "$testroot/portable-trace"
    extracted="$(sed -n 's/^bundle=//p' "$testroot/portable-trace")"
    [ -n "$extracted" ] && [ ! -e "$extracted" ]
    [ ! -e "$testroot/portable-profile/applications/io.github.otakuweber.chesspilot.desktop" ]
    if [ "$launch" = 1 ]; then
      printf 'saved engine\n' > "$testroot/portable-profile/chesspilot/native/stockfish"
      printf 'custom options\n' > "$testroot/portable-profile/chesspilot/engine_config.txt"
    fi
  done
  grep -qx 'saved engine' "$testroot/portable-profile/chesspilot/native/stockfish"
  grep -qx 'custom options' "$testroot/portable-profile/chesspilot/engine_config.txt"
else
  printf 'Self-extracting archive check requires Makeself; set CHESSPILOT_MAKESELF or run on CI.\n'
fi

if [ -n "${1:-}" ]; then
  installer="$(realpath -e -- "$1")"
  sh "$installer" --check
  XDG_DATA_HOME="$testroot/real" sh "$installer"
  installed="$testroot/real/chesspilot/app"
  [ -f "$installed/chess_detection.onnx" ] && [ -f "$installed/lib/libchesspilot_runtime.so" ]
  [ -f "$installed/usr/lib/libgtk-3.so.0" ]
  file "$installed/usr/share/icons/hicolor/512x512/apps/chesspilot.png" | grep -Fq '512 x 512'
  timeout 30s xvfb-run -a "$installed/AppRun" --help | grep -F 'Usage: chesspilot'
  CHESSPILOT_BUNDLE_TEST="$installed" cargo test --manifest-path "$repo/native/Cargo.toml" --test resources relocated_bundle_resolves_default_assets_without_checkout_paths -- --ignored
  XDG_DATA_HOME="$testroot/real" sh "$installer" -- --uninstall
  [ ! -e "$installed/chesspilot" ]
fi
if [ -n "${2:-}" ]; then
  portable="$(realpath -e -- "$2")"
  sh "$portable" --check
  env -u CHESSPILOT_DATA_HOME -u CHESSPILOT_ENGINE_HOME XDG_DATA_HOME="$testroot/real-portable-profile" \
    timeout 30s xvfb-run -a "$portable" -- --help | grep -F 'Usage: chesspilot'
  sh "$portable" --noexec --target "$testroot/portable-extracted"
  [ -f "$testroot/portable-extracted/.chesspilot-portable" ]
  CHESSPILOT_BUNDLE_TEST="$testroot/portable-extracted" cargo test --manifest-path "$repo/native/Cargo.toml" --test resources relocated_bundle_resolves_default_assets_without_checkout_paths -- --ignored
  [ ! -e "$testroot/real-portable-profile/applications/io.github.otakuweber.chesspilot.desktop" ]
fi
printf 'Linux installer lifecycle and launcher checks passed.\n'
