#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
section="${1:-}"; [[ $# -gt 0 ]] && shift
case "$section" in
 14.[1-9]) n="${section#14.}";;
 *) echo 'Usage: run_lab.sh 14.1..14.9 [--guide | --headless ...]';exit 2;;
esac
if [[ "${1:-}" == --guide && $# == 1 ]];then cat "$root/docs/LAB_14_${n}_GUIDE_KO.md";exit 0;fi
case "$section" in
14.4) exec bash "$root/scripts/verify_ch14.sh" --check perception "$@";;
14.8) sim="${1:-}"; [[ "$sim" == --sim ]] || exit 2;sim="${2:-}";shift 2; [[ "$sim" == mujoco || "$sim" == gazebo ]] || exit 2;exec bash "$root/scripts/verify_ch14.sh" --check "$sim" "$@";;
14.9) exec bash "$root/scripts/verify_ch14.sh" "$@";;
*) echo "BLOCKED automatic route not verified for $section; use --guide and manual commands" >&2;exit 2;;
esac
