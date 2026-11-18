#!/usr/bin/env bash
set -euo pipefail

fail() { printf 'ChessPilot setup: %s\n' "$*" >&2; exit 1; }
case "${1:-}" in ''|--uninstall) ;; *) fail 'Usage: installer.run [-- --uninstall]' ;; esac
[ -n "${HOME:-}" ] && [[ "$HOME" = /* ]] || fail 'HOME must be an absolute path.'
data="${XDG_DATA_HOME:-$HOME/.local/share}"
[[ "$data" = /* && "$data" != / && "$data" != *$'\n'* && "$data" != *$'\r'* ]] || fail 'Invalid XDG_DATA_HOME.'
mkdir -p -- "$data/chesspilot" "$data/applications"
base="$(cd -- "$data/chesspilot" && pwd -P)"
app="$base/app"
desktop="$data/applications/io.github.otakuweber.chesspilot.desktop"
manifest=.chesspilot-package-files
marker=.chesspilot-installed
[[ ! -L "$app" && ! -L "$desktop" ]] || fail 'Installation paths must not be symbolic links.'
if [ -e "$app" ]; then
  [ -f "$app/$marker" ] && [ ! -L "$app/$marker" ] && [ -f "$app/$manifest" ] && [ ! -L "$app/$manifest" ] || fail 'Refusing to replace an unrelated app directory.'
fi
if [ -f "$desktop" ]; then
  grep -qx 'X-ChessPilot-Managed=true' "$desktop" || fail 'The existing desktop entry is not managed by this installer.'
fi
mkdir -- "$base/.setup-lock" 2>/dev/null || fail 'Another installer is running; close it before trying again.'
stage=
backup=
cleanup() {
  local result=$?
  if [ -n "$backup" ] && [ -d "$backup" ] && [ ! -e "$app" ]; then mv -- "$backup" "$app"; fi
  if [[ -n "$stage" && "$stage" = "$base"/.setup.* ]]; then rm -rf -- "$stage"; fi
  rmdir -- "$base/.setup-lock" 2>/dev/null || true
  return "$result"
}
trap cleanup EXIT

# Validate every manifest entry before removing anything, including symlink parents.
validate_manifest() {
  local root="$1" entry parent
  while IFS= read -r entry; do
    case "$entry" in ./*) ;; *) fail 'Invalid installed-file manifest.' ;; esac
    case "/$entry/" in */../*|*/././*|*$'\n'*|*$'\r'*) fail 'Unsafe installed-file manifest.' ;; esac
    parent="$(realpath -m -- "$root/$(dirname -- "$entry")")"
    [[ "$parent" = "$root" || "$parent" = "$root"/* ]] || fail 'An installed-file path points outside the app.'
  done < "$root/$manifest"
}

if [ "${1:-}" = --uninstall ]; then
  [ -d "$app" ] || fail 'ChessPilot is not installed here.'
  validate_manifest "$app"
  while IFS= read -r entry; do rm -f -- "$app/$entry"; done < "$app/$manifest"
  : > "$app/$manifest"
  rm -f -- "$desktop"
  find "$app" -depth -type d -empty -delete
  printf 'ChessPilot removed. Engine, settings, caches and other user files are retained in %s\n' "$app"
  exit 0
fi

payload="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/AppDir"
[ -x "$payload/AppRun" ] && [ -f "$payload/chess_detection.onnx" ] || fail 'Installer payload is incomplete.'
stage="$(mktemp -d "$base/.setup.XXXXXX")"
cp -a -- "$payload/." "$stage/"
(cd -- "$stage" && find . \( -type f -o -type l \) -print | LC_ALL=C sort) > "$stage/$manifest"
if [ -d "$app" ]; then
  validate_manifest "$app"
  # New package files win; user-owned engine/config/cache and other files survive upgrades.
  cp -an -- "$app/." "$stage/"
  while IFS= read -r entry; do
    if ! grep -Fxq -- "$entry" "$stage/$manifest"; then
      parent="$(realpath -m -- "$stage/$(dirname -- "$entry")")"
      [[ "$parent" = "$stage" || "$parent" = "$stage"/* ]] || fail 'Unsafe obsolete package path.'
      rm -f -- "$stage/$entry"
    fi
  done < "$app/$manifest"
fi
printf 'ChessPilot\n' > "$stage/$marker"

# Desktop entry string escaping precedes Exec argument unquoting.
exec_path="$app/AppRun"
exec_path="${exec_path//\\/\\\\\\\\}"
exec_path="${exec_path//\"/\\\\\"}"
exec_path="${exec_path//\$/\\\\\$}"
exec_path="${exec_path//\`/\\\\\`}"
exec_path="${exec_path//%/%%}"
icon_path="${app//\\/\\\\}/data/chesspilot.png"
cat > "$stage/.desktop-entry" <<EOF
[Desktop Entry]
Type=Application
Name=ChessPilot
Comment=Local chessboard detection and Stockfish analysis
Exec="$exec_path"
Icon=$icon_path
Terminal=false
Categories=Game;BoardGame;
StartupWMClass=io.github.otakuweber.chesspilot
X-ChessPilot-Managed=true
EOF
if [ -d "$app" ]; then
  backup="$base/.previous-$$"
  [ ! -e "$backup" ] || fail 'An earlier setup backup needs attention.'
  mv -- "$app" "$backup"
fi
mv -- "$stage" "$app"
stage=
mv -- "$app/.desktop-entry" "$desktop"
if [ -n "$backup" ]; then rm -rf -- "$backup"; backup=; fi
command -v update-desktop-database >/dev/null && update-desktop-database "$data/applications" || true
printf 'ChessPilot installed in %s\nOpen ChessPilot from your applications menu, or run:\n  "%s/AppRun"\nFirst launch downloads Stockfish when missing.\n' "$app" "$app"
