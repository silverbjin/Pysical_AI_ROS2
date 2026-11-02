#!/usr/bin/env bash
set -e
reuse_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
reuse_case=$1
reuse_out=$2
if [[ -d "$reuse_out" && -n "$(ls -A "$reuse_out")" ]]; then echo "Use a new evidence directory" >&2; exit 2; fi
mkdir -p "$reuse_out"
export MUJOCO_GL=egl
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/audit_r2_install.py" "$reuse_out/install_audit.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/pre_residual.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/run_navigation_probe.py" --repo-root "$reuse_repo" --evidence "$reuse_out" --case "$reuse_case" --vision-hz "${3:-10}" > "$reuse_out/probe_stdout.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/verify_navigation.py" "$reuse_out" > "$reuse_out/verification.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/residual_processes.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/write_run_report.py" "$reuse_out"
