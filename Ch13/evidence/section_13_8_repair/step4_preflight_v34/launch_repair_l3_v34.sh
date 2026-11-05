#!/usr/bin/env bash
set -eo pipefail
runtime=/home/jinho/ch13_reuse_13_8_build/live_source_e1f5a8d81daa48d2b8337ae08f5253e2/repo
original=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_13_8
prep="$original/../section_13_8_preparation_20261104"
evidence="$original/Ch13/evidence/section_13_8_system/9e160887-cc8a-4f1d-a4e7-83aae4f77818"
cd "$runtime"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_REPAIR_L3_V34.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]=="PASS"' "$prep/BEFORE_REPAIR_L3_V34.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]=="PASS"' "$prep/repair_v34_source_match.json"
export CH13_CAPTURE_OVERLAP=0
export CH13_REUSE_STARTUP_TRACE="$evidence/startup_trace"
set +e
bash Ch13/scripts/reuse_13_8/env.sh -u Ch13/scripts/reuse_13_8/run_mission.py --repo-root "$runtime" --evidence "$evidence" --manifest "$runtime/Ch13/dependencies/section_13_8_system_v34.json" --auto-start --scenario level3_house
code=$?
set -e
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/AFTER_REPAIR_L3_V34.json"
if [[ -d "$evidence" ]]; then cp --update=none ../source_stage.json "$evidence/runtime_stage.json"; fi
printf '%s\n' "$code" > "$prep/repair_L3_v34_exit.txt"
exit "$code"