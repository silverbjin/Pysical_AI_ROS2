#!/usr/bin/env bash
set -eo pipefail
runtime=/home/jinho/ch13_reuse_13_8_build/live_source_dafeaa8e75e24d87be97ec20d6c17f96/repo
original=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_13_8
prep="$original/../section_13_8_preparation_20261104"
evidence="$original/Ch13/evidence/section_13_8_system/dfcd2bc6-d8d1-44f3-b0cc-a0634bbba959"
cd "$runtime"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_REPAIR_L3_V35.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]=="PASS"' "$prep/BEFORE_REPAIR_L3_V35.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]=="PASS"' "$prep/repair_v35_source_match.json"
export CH13_CAPTURE_OVERLAP=0
export CH13_REUSE_STARTUP_TRACE="$evidence/startup_trace"
set +e
bash Ch13/scripts/reuse_13_8/env.sh -u Ch13/scripts/reuse_13_8/run_mission.py --repo-root "$runtime" --evidence "$evidence" --manifest "$runtime/Ch13/dependencies/section_13_8_system_v35.json" --auto-start --scenario level3_house
code=$?
set -e
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/AFTER_REPAIR_L3_V35.json"
if [[ -d "$evidence" ]]; then cp --update=none ../source_stage.json "$evidence/runtime_stage.json"; fi
printf '%s\n' "$code" > "$prep/repair_L3_v35_exit.txt"
exit "$code"