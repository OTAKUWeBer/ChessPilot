#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
bundle="$(realpath -e -- "${1:-$repo/app/build/linux/x64/release/bundle}")"
output="${2:-$repo/app/build/linux/installer}"
[[ "$(uname -s)" = Linux && "$(uname -m)" = x86_64 ]] || { echo 'Build this installer on x86_64 Linux.' >&2; exit 1; }
for tool in curl sha256sum file pkg-config readelf dpkg-deb; do
  command -v "$tool" >/dev/null || { echo "Missing packaging tool: $tool; see docs/BUILDING.md." >&2; exit 1; }
done
command -v dpkg-query >/dev/null || command -v pacman >/dev/null || { echo 'Package on an Ubuntu/Debian or Arch build host so dependency notices can be collected.' >&2; exit 1; }
pkg-config --exists gtk+-3.0 librsvg-2.0 gobject-introspection-1.0
version="$(sed -nE 's/^version: *([0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?)\+[0-9]+ *$/\1/p' "$repo/app/pubspec.yaml")"
[ -n "$version" ] || { echo 'Invalid pubspec release version.' >&2; exit 1; }
for required in chesspilot lib/libflutter_linux_gtk.so lib/libchesspilot_runtime.so lib/libonnxruntime.so lib/libapp.so data/icudtl.dat data/flutter_assets chess_detection.onnx ChessPilot-LICENSE.txt licenses; do
  [ -e "$bundle/$required" ] || { echo "Incomplete release bundle: $required" >&2; exit 1; }
done
file "$bundle/chesspilot" | grep -q 'ELF 64-bit.*x86-64' || { echo 'Expected an x86-64 Linux executable.' >&2; exit 1; }
expected="$(cut -d' ' -f1 "$repo/assets/models/chess_detection.onnx.sha256")"
printf '%s  %s\n' "$expected" "$bundle/chess_detection.onnx" | sha256sum -c -
mkdir -p -- "$output" "$repo/native/target/linux-packaging-tools"
output="$(cd -- "$output" && pwd -P)"
[[ "$output" != "$bundle" && "$output" != "$bundle"/* ]] || { echo 'Installer output must be outside the bundle.' >&2; exit 1; }
tools="$repo/native/target/linux-packaging-tools"
fetch() {
  local url="$1" destination="$2" checksum="$3"
  if ! printf '%s  %s\n' "$checksum" "$destination" | sha256sum -c - >/dev/null 2>&1; then
    curl --fail --location --retry 3 --proto '=https' --output "$destination.part" "$url"
    printf '%s  %s\n' "$checksum" "$destination.part" | sha256sum -c -
    mv -- "$destination.part" "$destination"
  fi
  chmod +x -- "$destination"
}
fetch 'https://github.com/linuxdeploy/linuxdeploy/releases/download/1-alpha-20251107-1/linuxdeploy-x86_64.AppImage' "$tools/linuxdeploy-x86_64.AppImage" c20cd71e3a4e3b80c3483cef793cda3f4e990aca14014d23c544ca3ce1270b4d
fetch 'https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/7a3fbc31a9e5075073ff8790f26effbac5f84453/linuxdeploy-plugin-gtk.sh' "$tools/linuxdeploy-plugin-gtk.sh" b0f4cbc684a0103a9651f0955b635eaea0096b3a66c0f5a2c2aa337960375171
fetch 'https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/7a3fbc31a9e5075073ff8790f26effbac5f84453/LICENSE.txt' "$tools/gtk-LICENSE.txt" 0718f6cadf38d2662f397591b777884c5389e65b9919aae6aca2bea87a52eac4
fetch 'https://raw.githubusercontent.com/megastep/makeself/release-2.5.0/makeself.sh' "$tools/makeself.sh" ea025ed0be9996885e873e0eafff475ebd5e85cb77dbff858e0c34bd9a1aa85c
fetch 'https://raw.githubusercontent.com/megastep/makeself/release-2.5.0/makeself-header.sh' "$tools/makeself-header.sh" 7d2028696f63f1135611a244f7896003bc7ad4634ec8e26856f0ef686838acf9
fetch 'https://raw.githubusercontent.com/megastep/makeself/release-2.5.0/COPYING' "$tools/makeself-COPYING" 8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643
fetch 'https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage' "$tools/appimagetool-x86_64.AppImage" ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
work="$(mktemp -d "$repo/native/target/linux-package.XXXXXX")"
trap '[[ "$work" = "$repo"/native/target/linux-package.* ]] && rm -rf -- "$work"' EXIT
appdir="$work/payload/AppDir"
mkdir -p -- "$appdir"
# Allowlist application files; never package the maintainer's engine, config, cache or logs.
for item in chesspilot lib data chess_detection.onnx ChessPilot-LICENSE.txt licenses; do cp -a -- "$bundle/$item" "$appdir/"; done
install -m 755 "$repo/packaging/linux/AppRun" "$appdir/AppRun"
install -m 755 "$repo/packaging/linux/install.sh" "$work/payload/install.sh"
mkdir -p "$appdir/usr/bin"
ln -s ../../chesspilot "$appdir/usr/bin/chesspilot"
# linuxdeploy's bundled strip cannot read modern Arch RELR sections; GTK subprocesses inherit this.
export APPIMAGE_EXTRACT_AND_RUN=1 DEPLOY_GTK_VERSION=3 NO_STRIP=1
"$tools/linuxdeploy-x86_64.AppImage" --appdir "$appdir" --deploy-deps-only "$appdir" \
  --executable "$(command -v curl)" \
  --custom-apprun "$repo/packaging/linux/AppRun" --desktop-file "$repo/packaging/linux/chesspilot.desktop" \
  --icon-file "$repo/packaging/linux/chesspilot.png" --plugin gtk

# Retain the distro copyright/source notices for packaged GTK and library dependencies.
mkdir -p "$appdir/licenses/Linux-runtime"
while IFS= read -r -d '' library; do
  name="$(basename -- "$library")"
  if command -v dpkg-query >/dev/null; then
    while IFS= read -r package; do
      package="${package%%:*}"
      if [ -f "/usr/share/doc/$package/copyright" ]; then
        cp -L -- "/usr/share/doc/$package/copyright" "$appdir/licenses/Linux-runtime/$package.txt"
      fi
    done < <(dpkg-query -S "*/$name" 2>/dev/null | sed 's/: \/.*//' | sort -u || true)
  else
    while IFS= read -r package; do
      if [ -d "/usr/share/licenses/$package" ]; then
        cp -LR -- "/usr/share/licenses/$package" "$appdir/licenses/Linux-runtime/"
      fi
    done < <(pacman -Qoq "/${library#"$appdir"/}" "/usr/lib/$name" 2>/dev/null | sort -u || true)
  fi
done < <(find "$appdir" \( -name '*.so*' -o -path "$appdir/usr/bin/curl" \) \( -type f -o -type l \) -print0)
for common in /usr/share/common-licenses /usr/share/licenses/common; do
  [ ! -d "$common" ] || cp -LR -- "$common" "$appdir/licenses/Linux-runtime/"
done
cp "$tools/linuxdeploy-plugin-gtk.sh" "$appdir/licenses/Linux-runtime/linuxdeploy-plugin-gtk-source.sh"
cp "$tools/gtk-LICENSE.txt" "$appdir/licenses/Linux-runtime/linuxdeploy-plugin-gtk-LICENSE.txt"
cp "$tools/makeself.sh" "$tools/makeself-header.sh" "$tools/makeself-COPYING" "$appdir/licenses/Linux-runtime/"
cp "$repo/packaging/linux/AppImage-runtime-LICENSE.txt" "$appdir/licenses/Linux-runtime/"
"$tools/appimagetool-x86_64.AppImage" --appimage-help > "$appdir/licenses/Linux-runtime/AppImage-runtime-notices.txt" 2>&1
printf 'Runtime copied from the hash-pinned appimagetool 1.9.1 executable.\nTool source: https://github.com/AppImage/appimagetool/tree/1.9.1\nRuntime source and dependencies: https://github.com/AppImage/type2-runtime\n' \
  > "$appdir/licenses/Linux-runtime/AppImage-runtime-SOURCE.txt"
# Read version requirements rather than declaring an older libc than the payload uses.
minimum_glibc="$(while IFS= read -r -d '' binary; do
  readelf --version-info "$binary" 2>/dev/null || true
done < <(find "$appdir" -type f \( -name '*.so*' -o -perm /111 \) -print0) |
  sed -nE 's/.*Name: GLIBC_([0-9]+\.[0-9]+).*/\1/p' | sort -Vu | tail -n 1)"
[ -n "$minimum_glibc" ] || { echo 'Could not determine the payload glibc requirement.' >&2; exit 1; }
if [ "$(printf '%s\n' 2.35 "$minimum_glibc" | sort -V | tail -n 1)" != 2.35 ]; then
  echo "Warning: payload requires glibc $minimum_glibc. Rebuild on Ubuntu 22.04 for public releases." >&2
fi
installer="$output/ChessPilot-$version-linux-x64-setup.run"
"$tools/makeself.sh" --nox11 --sha256 --nomd5 --nocrc --tar-format posix "$work/payload" "$installer" "ChessPilot $version" ./install.sh
sh "$installer" --check

# Portable one-file app: extract, run and clean up without installing a menu entry.
touch "$appdir/.chesspilot-portable"
portable="$output/ChessPilot-$version-linux-x86_64"
"$tools/makeself.sh" --nox11 --sha256 --nomd5 --nocrc --tar-format posix "$appdir" "$portable" "ChessPilot $version portable" ./AppRun
sh "$portable" --check

# Reuse the pinned tool's own runtime at its reported ELF boundary; no floating download.
runtime_offset="$("$tools/appimagetool-x86_64.AppImage" --appimage-offset)"
[[ "$runtime_offset" =~ ^[0-9]+$ && "$runtime_offset" -gt 0 ]] || { echo 'Invalid AppImage runtime offset.' >&2; exit 1; }
head -c "$runtime_offset" "$tools/appimagetool-x86_64.AppImage" > "$work/runtime-x86_64"
appimage="$output/ChessPilot-$version-linux-x86_64.AppImage"
ARCH=x86_64 "$tools/appimagetool-x86_64.AppImage" --runtime-file "$work/runtime-x86_64" "$appdir" "$appimage"

debroot="$work/deb"
mkdir -p "$debroot/opt" "$debroot/DEBIAN" "$debroot/usr/bin" \
  "$debroot/usr/share/applications" "$debroot/usr/share/icons/hicolor/512x512/apps" \
  "$debroot/usr/share/doc/chesspilot"
cp -a "$appdir" "$debroot/opt/chesspilot"
printf '#!/bin/sh\nexec /opt/chesspilot/AppRun "$@"\n' > "$debroot/usr/bin/chesspilot"
chmod 755 "$debroot/usr/bin/chesspilot"
install -m 644 "$repo/packaging/linux/chesspilot.desktop" "$debroot/usr/share/applications/io.github.otakuweber.chesspilot.desktop"
install -m 644 "$repo/packaging/linux/chesspilot.png" "$debroot/usr/share/icons/hicolor/512x512/apps/chesspilot.png"
install -m 644 "$repo/LICENSE" "$debroot/usr/share/doc/chesspilot/copyright"
# Debian sorts prereleases before the corresponding stable version.
debversion="${version/-/~}"
cat > "$debroot/DEBIAN/control" <<EOF
Package: chesspilot
Version: $debversion
Section: games
Priority: optional
Architecture: amd64
Installed-Size: $(du -sk "$debroot" | cut -f1)
Maintainer: OTAKUWeBer <137557891+OTAKUWeBer@users.noreply.github.com>
Homepage: https://github.com/OTAKUWeBer/ChessPilot
Depends: bash, libc6 (>= $minimum_glibc), libstdc++6 (>= 12), libgcc-s1, libgl1, libegl1, libx11-6
Description: Local chessboard detection and Stockfish analysis
 Detect on-screen boards, analyze positions and control moves locally.
 The detector and application libraries are included. A CPU-compatible
 official Stockfish release is downloaded to user data on first launch.
EOF
find "$debroot" -type d -exec chmod 755 {} +
chmod 644 "$debroot/DEBIAN/control"
deb="$output/chesspilot_${debversion}_amd64.deb"
dpkg-deb --build --root-owner-group "$debroot" "$deb"

info="$output/ChessPilot-$version-linux-build-info.txt"
printf 'Version: %s\nPackaging revision: %s\nMinimum glibc: %s\nBuild host: %s\n' \
  "$version" "$(git -C "$repo" rev-parse HEAD)" "$minimum_glibc" "$(uname -srmo)" > "$info"
for artifact in "$installer" "$portable" "$appimage" "$deb" "$info"; do
  (cd -- "$output" && sha256sum "$(basename -- "$artifact")" > "$(basename -- "$artifact").sha256")
done
printf '\nPortable app: %s\nAppImage: %s\nDebian package: %s\nOptional installer: %s\n' "$portable" "$appimage" "$deb" "$installer"
