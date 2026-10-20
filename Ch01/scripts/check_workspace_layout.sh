#!/usr/bin/env bash
# Ch01 §1.4: non-destructive inspection (does not build, clean or source).
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
  echo "Usage: $0 <absolute-workspace-path>" >&2; exit 2
fi
workspace="$1"
if [[ "$workspace" != /* ]]; then
  echo 'BLOCKED: provide absolute workspace path' >&2; exit 2
fi
if [[ ! -d "$workspace/src" ]]; then
  echo "BLOCKED: workspace src directory missing: $workspace/src" >&2; exit 2
fi
printf 'WORKSPACE=%s\n' "$workspace"
for directory in src build install log; do
  if [[ -d "$workspace/$directory" ]]; then
    printf '%s=present\n' "$directory"
  else
    printf '%s=absent (normal before first build)\n' "$directory"
  fi
done
if [[ -r "$workspace/install/setup.bash" ]]; then
  echo 'OVERLAY=install/setup.bash exists'
else
  echo 'OVERLAY=not yet built; build the workspace before sourcing'
fi
printf 'CURRENT_AMENT_PREFIX_PATH=%s\n' "${AMENT_PREFIX_PATH:-unset}"
if command -v colcon >/dev/null 2>&1; then
  colcon list --base-paths "$workspace/src" --names-only
else
  echo 'NOTE: colcon not installed; ROS package enumeration NOT_RUN'
fi
echo 'PASS: safe, read-only workspace inspection completed'
