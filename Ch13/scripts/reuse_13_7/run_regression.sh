#!/usr/bin/env bash
# Developer-only check of the legacy default runner with BT hooks disabled.
set -eo pipefail
bt_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bt_repo="$(cd "$bt_scripts/../../.." && pwd)"
bt_out=${1:?new evidence directory}
if [[ -e "$bt_out" ]]; then echo 'new evidence directory required' >&2; exit 2; fi
mkdir -p "$bt_out"
bash "$bt_scripts/env.sh" "$bt_scripts/freeze_runtime.py" verify "$bt_repo/Ch13/dependencies/section_13_7_bt_v5.json" > "$bt_out/freeze_audit.json" 2>&1
bash "$bt_scripts/env.sh" "$bt_scripts/audit_install.py" "$bt_out/install_audit.json" > "$bt_out/audit.log" 2>&1
bash "$bt_scripts/env.sh" "$bt_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$bt_out/pre_residual.json" > "$bt_out/pre_residual.log" 2>&1
bt_rc=0
bash "$bt_scripts/env.sh" "$bt_repo/Ch13/scripts/reuse_13_5/run_navigation_probe.py" --repo-root "$bt_repo" --evidence "$bt_out/run" --case free > "$bt_out/probe.log" 2>&1 || bt_rc=$?
bash "$bt_scripts/env.sh" "$bt_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$bt_out/post_residual.json" > "$bt_out/post_residual.log" 2>&1 || bt_rc=$?
bash "$bt_scripts/env.sh" "$bt_repo/Ch13/scripts/reuse_13_6/verify_navigation.py" "$bt_out" > "$bt_out/verification.log" 2>&1 || bt_rc=$?
printf 'LEGACY_FREE EXIT %s EVIDENCE %s\n' "$bt_rc" "$bt_out"
exit "$bt_rc"
