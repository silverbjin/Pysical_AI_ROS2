#!/usr/bin/env bash
# Download this exact file at the same full PIN; run without sudo.
set -Eeuo pipefail
: "${CH15_SOURCE_SHA:?40 hex source PIN required}"
: "${CH15_BOOTSTRAP_SHA256:?published bootstrap digest required}"
pin="$CH15_SOURCE_SHA"
[[ "$pin" =~ ^[0-9a-f]{40}$ && "$CH15_BOOTSTRAP_SHA256" =~ ^[0-9a-f]{64}$ ]] || exit 2
actual="$(sha256sum "${BASH_SOURCE[0]}" | cut -d' ' -f1)"
[[ "$actual" == "$CH15_BOOTSTRAP_SHA256" ]] || { echo CH15_BOOTSTRAP_SHA_DRIFT >&2; exit 2; }
export GIT_LFS_SKIP_SMUDGE=1
work="${CH15_WORK_ROOT:-$HOME/ch15-owner}"
mkdir -p "$work/sources"
work="$(realpath "$work")"
src="$work/sources/$pin"
if [[ ! -e "$src" ]]; then
  tmp="$(mktemp -d "$work/sources/.fetch.XXXXXXXX")"
  trap 'rm -rf -- "$tmp"' EXIT
  git -C "$tmp" init -q
  git -C "$tmp" remote add origin https://github.com/silverbjin/Pysical_AI_ROS2.git
  git -C "$tmp" -c core.autocrlf=false fetch --depth=1 --filter=blob:none origin "$pin"
  [[ "$(git -C "$tmp" rev-parse FETCH_HEAD)" == "$pin" ]] || exit 2
  git -C "$tmp" sparse-checkout init --cone
  git -C "$tmp" sparse-checkout set Ch15
  git -C "$tmp" -c core.autocrlf=false checkout --detach "$pin"
  [[ ! -e "$src" ]] || exit 2
  mv -T "$tmp" "$src"
  trap - EXIT
fi
[[ "$(git -C "$src" rev-parse HEAD)" == "$pin" ]] || { echo CH15_SOURCE_SHA_DRIFT >&2; exit 2; }
[[ "$(git -C "$src" remote get-url origin)" == https://github.com/silverbjin/Pysical_AI_ROS2.git ]] || exit 2
cmp "${BASH_SOURCE[0]}" "$src/Ch15/scripts/bootstrap_ch15.sh" || exit 2
export CH15_WORK_ROOT="$work"
export CH15_BOOTSTRAP_VERIFIED_SHA256="$actual"
exec bash "$src/Ch15/scripts/verify_ch15.sh" "$@"
