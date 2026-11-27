#!/usr/bin/env bash
# Explicitly opt in on a dedicated immutable Ch13 checkout; no asset download.
set -Eeuo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 3 ]] || { echo 'usage: bash run_plant_identification.sh CH13_CHECKOUT LOCAL_APPROVAL_JSON NEW_EVIDENCE_DIR'; exit 2; }
root="$(realpath "$1")"; approval="$(realpath "$2")"; out="$(realpath -m "$3")"
[[ ! -e "$out" ]] || { echo 'new evidence directory required'; exit 2; }
mkdir -p "$out"
adapter="$here/ros2_ws/src/ch15_adapters/ch15_adapters/ch13_basic_adapter.py"
contract="$here/dependencies/ch13_contract.lock.json"
python3 "$adapter" preflight --root "$root" --lock "$here/dependencies/reuse.audit.json" --contract "$contract" --approval "$approval" --out "$out/preflight.json"
: "${CH13_REUSE_BUILD:?separate build required}" "${CH13_REUSE_VENV:?verified native venv required}"
export CH13_REUSE_BUILD CH13_REUSE_VENV
cd "$root"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$out/before.json"
python3 "$adapter" residual --residual "$out/before.json" --out "$out/before-verdict.json"
bash Ch13/scripts/reuse_13_8/build.sh >"$out/build.log" 2>&1
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/audit_install.py "$out/install-audit.json"
freeze="Ch13/dependencies/ch15_plant_$(python3 -c 'import uuid; print(uuid.uuid4().hex)').json"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/freeze_runtime.py write "$freeze" | tee "$out/freeze.log"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/stage_runtime.py --manifest "$freeze" --output "$out/stage.json"
runtime="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runtime_root"])' "$out/stage.json")"
cd "$runtime"
set +e
CH13_CAPTURE_OVERLAP=1 CH13_EXPERIMENTAL_SE2=0 CH13_CALLBACK_TIMING=0 bash Ch13/scripts/reuse_13_8/env.sh -u "$here/scripts/run_plant_identification.py" --repo-root "$runtime" --manifest "$runtime/$freeze" --evidence "$out/native" 2>&1 | tee "$out/native-run.log"
pipeline_rc=("${PIPESTATUS[@]}")
rc=${pipeline_rc[0]}
if ((pipeline_rc[1]!=0));then rc=1;fi
set -e
cd "$root"
set +e
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$out/after.json"
residual_rc=$?
printf '{"runner_exit":%d,"residual_exit":%d}\n' "$rc" "$residual_rc" >"$out/exit-contract.json"
set -e
if ((rc != 0 || residual_rc != 0)); then exit 1; fi
python3 "$adapter" residual --residual "$out/after.json" --out "$out/after-verdict.json"
