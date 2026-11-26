#!/usr/bin/env bash
set -Eeuo pipefail
pin="${CH14_SOURCE_SHA:-}"
[[ "$pin" =~ ^[0-9a-f]{40}$ ]] || { echo 'BLOCKED: CH14_SOURCE_SHA must be exact 40 hex';exit 2; }
command -v git >/dev/null || exit 2
base="$HOME/ch14-owner";mkdir -p "$base"
dest="$(mktemp -d "$base/source_${pin:0:12}_XXXXXX")"
git -C "$dest" init -q
git -C "$dest" remote add origin https://github.com/silverbjin/Pysical_AI_ROS2.git
# Only Chapter 14: avoid downloading historical chapters and large tracked artifacts.
git -C "$dest" config remote.origin.promisor true
git -C "$dest" config remote.origin.partialclonefilter blob:none
git -C "$dest" sparse-checkout init --cone
git -C "$dest" sparse-checkout set Ch14
timeout 180s git -C "$dest" fetch --filter=blob:none --depth=1 --no-tags origin "$pin"
git -C "$dest" checkout --detach -q FETCH_HEAD
[[ "$(git -C "$dest" rev-parse HEAD)" == "$pin" ]] || { echo 'BLOCKED SHA drift';exit 2; }
cmp "$0" "$dest/Ch14/scripts/bootstrap.sh" || { echo 'BLOCKED bootstrap bytes differ from pinned source';exit 2; }
echo "CH14_SOURCE=$dest"
exec bash "$dest/Ch14/scripts/verify_ch14.sh" --source-sha "$pin" "$@"
