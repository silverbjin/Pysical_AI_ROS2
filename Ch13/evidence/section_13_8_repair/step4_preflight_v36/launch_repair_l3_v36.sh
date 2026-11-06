#!/usr/bin/env bash
set -eo pipefail
runtime=/home/jinho/ch13_reuse_13_8_build/live_source_e4daf46330e14c6285d2ad879ca878d3/repo
original=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_13_8
prep="$original/../section_13_8_preparation_20261104"
evidence="$original/Ch13/evidence/section_13_8_system/d0611273-5f74-47a8-b108-12d189dbd523"
cd "$runtime"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_REPAIR_L3_V36.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]=="PASS"' "$prep/BEFORE_REPAIR_L3_V36.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]=="PASS"' "$prep/repair_v36_source_match.json"
export CH13_CAPTURE_OVERLAP=0
export CH13_EXPERIMENTAL_SE2=0
export CH13_REUSE_STARTUP_TRACE="$evidence/startup_trace"
set +e
bash Ch13/scripts/reuse_13_8/env.sh -u Ch13/scripts/reuse_13_8/run_mission.py --repo-root "$runtime" --evidence "$evidence" --manifest "$runtime/Ch13/dependencies/section_13_8_system_v36.json" --auto-start --scenario level3_house
code=$?
set -e
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/AFTER_REPAIR_L3_V36.json"
if [[ -d "$evidence" ]]; then cp --update=none ../source_stage.json "$evidence/runtime_stage.json"; fi
printf '%s\n' "$code" > "$prep/repair_L3_v36_exit.txt"
exit "$code"