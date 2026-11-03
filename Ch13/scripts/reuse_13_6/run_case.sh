#!/usr/bin/env bash
set -eo pipefail
reuse_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
reuse_repo="$(cd "$reuse_scripts/../../.." && pwd)"
reuse_case=${1:?hold/expire/old_session/duplicate}
reuse_out=${2:?new evidence directory}
if [[ -e "$reuse_out" ]]; then echo 'Use a new evidence directory' >&2; exit 2; fi
mkdir -p "$reuse_out"
if [[ -f "$reuse_repo/Ch13/dependencies/section_13_6_reuse.lock.json" ]]; then
  bash "$reuse_scripts/env.sh" "$reuse_scripts/freeze_runtime.py" verify "$reuse_repo/Ch13/dependencies/section_13_6_reuse.lock.json" > "$reuse_out/freeze_audit.json" 2>&1
fi
bash "$reuse_scripts/env.sh" "$reuse_scripts/audit_install.py" "$reuse_out/install_audit.json" > "$reuse_out/audit.log" 2>&1
bash "$reuse_scripts/env.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/pre_residual.json" > "$reuse_out/pre_residual.log" 2>&1
reuse_rc=0
reuse_runner=run_handoff.py
reuse_runner_case=$reuse_case
case "$reuse_case" in
  arm_normal|arm_cancel|arm_loss) reuse_runner=run_arm_probe.py; reuse_runner_case=${reuse_case#arm_};;
  moveit) reuse_runner=run_moveit_probe.py;;
  pick) reuse_runner=run_pick.py;;
esac
reuse_options=()
if [[ $reuse_case != moveit && $reuse_case != pick ]]; then reuse_options=(--case "$reuse_runner_case"); fi
bash "$reuse_scripts/env.sh" "$reuse_scripts/$reuse_runner" --repo-root "$reuse_repo" --evidence "$reuse_out/run" "${reuse_options[@]}" > "$reuse_out/probe.log" 2>&1 || reuse_rc=$?
bash "$reuse_scripts/env.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/post_residual.json" > "$reuse_out/post_residual.log" 2>&1 || reuse_rc=$?
printf 'CASE %s EXIT %s EVIDENCE %s\n' "$reuse_case" "$reuse_rc" "$reuse_out"
exit "$reuse_rc"
