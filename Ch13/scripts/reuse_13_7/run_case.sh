#!/usr/bin/env bash
set -eo pipefail
bt_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bt_repo="$(cd "$bt_scripts/../../.." && pwd)"
bt_case=${1:?normal/cancel/low_battery/held_cancel}
bt_out=${2:?new evidence directory}
case "$bt_case" in normal|cancel|low_battery|held_cancel) ;; *) exit 2;; esac
if [[ -e "$bt_out" ]]; then echo 'new evidence directory required' >&2; exit 2; fi
mkdir -p "$bt_out"
bt_freeze=${CH13_REUSE_FREEZE:-$bt_repo/Ch13/dependencies/section_13_7_bt_v5.json}
bash "$bt_scripts/env.sh" "$bt_scripts/freeze_runtime.py" verify "$bt_freeze" > "$bt_out/freeze_audit.json" 2>&1
bash "$bt_scripts/env.sh" "$bt_scripts/audit_install.py" "$bt_out/install_audit.json" > "$bt_out/audit.log" 2>&1
bash "$bt_scripts/env.sh" "$bt_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$bt_out/pre_residual.json" > "$bt_out/pre_residual.log" 2>&1
bt_rc=0
bash "$bt_scripts/env.sh" "$bt_scripts/run_mission.py" --repo-root "$bt_repo" --evidence "$bt_out/run" --case "$bt_case" > "$bt_out/probe.log" 2>&1 || bt_rc=$?
bash "$bt_scripts/env.sh" "$bt_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$bt_out/post_residual.json" > "$bt_out/post_residual.log" 2>&1 || bt_rc=$?
if [[ -f "$bt_out/run/bt_summary.json" ]]; then
 bash "$bt_scripts/env.sh" "$bt_scripts/verify_mission.py" "$bt_out" > "$bt_out/verification.log" 2>&1 || bt_rc=$?
fi
printf 'BT_CASE %s EXIT %s EVIDENCE %s\n' "$bt_case" "$bt_rc" "$bt_out"
exit "$bt_rc"
