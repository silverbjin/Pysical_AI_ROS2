#!/usr/bin/env bash
set -eo pipefail
reuse_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
reuse_repo="$(cd "$reuse_scripts/../../.." && pwd)"
reuse_case=${1:?hold/expire/old_session/duplicate}
reuse_out=${2:?new evidence directory}
if [[ -e "$reuse_out" ]]; then echo 'Use a new evidence directory' >&2; exit 2; fi
mkdir -p "$reuse_out"
bash "$reuse_scripts/env.sh" "$reuse_scripts/audit_install.py" "$reuse_out/install_audit.json" > "$reuse_out/audit.log" 2>&1
bash "$reuse_scripts/env.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/pre_residual.json" > "$reuse_out/pre_residual.log" 2>&1
reuse_rc=0
bash "$reuse_scripts/env.sh" "$reuse_scripts/run_handoff.py" --repo-root "$reuse_repo" --evidence "$reuse_out/run" --case "$reuse_case" > "$reuse_out/probe.log" 2>&1 || reuse_rc=$?
bash "$reuse_scripts/env.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/post_residual.json" > "$reuse_out/post_residual.log" 2>&1 || reuse_rc=$?
printf 'CASE %s EXIT %s EVIDENCE %s\n' "$reuse_case" "$reuse_rc" "$reuse_out"
exit "$reuse_rc"
