#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != Linux ]]; then
  echo 'This SDK launcher is for Linux. On Windows use the pinned Flutter SDK or FVM.' >&2
  exit 1
fi
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
version="$(sed -nE 's/^[[:space:]]*"flutter"[[:space:]]*:[[:space:]]*"([0-9]+\.[0-9]+\.[0-9]+)"[[:space:]]*,?[[:space:]]*$/\1/p' "$repo/app/.fvmrc")"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo 'Expected one exact stable Flutter version in app/.fvmrc.' >&2
  exit 1
fi
sdk="$repo/native/target/flutter-sdk/$version"
if [[ ! -e "$sdk" ]]; then
  mkdir -p "$(dirname -- "$sdk")"
  git clone --depth 1 --branch "$version" https://github.com/flutter/flutter.git "$sdk"
fi
if [[ -L "$sdk" || ! -d "$sdk/.git" ]]; then
  echo "Expected a project-owned SDK checkout at $sdk; inspect that directory before retrying." >&2
  exit 1
fi
expected="$(git -C "$sdk" rev-parse "refs/tags/$version^{commit}")"
if [[ "$(git -C "$sdk" rev-parse HEAD)" != "$expected" ]]; then
  echo "Cached SDK is not checked out at Flutter $version: $sdk" >&2
  exit 1
fi
# Always use the SDK's own Dart and tool snapshots, independently of system Flutter.
export PATH="$sdk/bin:$PATH"
cd "$repo/app"
exec "$sdk/bin/flutter" "$@"
