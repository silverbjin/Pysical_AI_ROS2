#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/observe-cold-clock.py "$1"
python - "$1" <<'PY'
import json,sys
from pathlib import Path
from integrated_robot_navigation.clock_preflight import ClockStabilityGate
roots=list(Path(sys.argv[1]).glob('clock-observation-*'))
assert len(roots)==1
result=json.loads((roots[0]/'result.json').read_text())
gate=ClockStabilityGate()
for line in (roots[0]/'samples.jsonl').read_text().splitlines():
    row=json.loads(line)
    gate.observe((row['wall_before_ns']+row['wall_after_ns'])//2,row['system_ns'])
admission=dict(**gate.snapshot(),same_boot=result['same_boot'],
    policy='original_40s_quiet_within_150s_not_zero_jumps_since_boot',
    original_diagnostic_preserved=True)
(roots[0]/'settling-admission.json').write_text(json.dumps(admission,indent=2))
print(json.dumps(admission),flush=True)
assert result['same_boot'] and gate.state=='READY', 'clock settling failed; no engine attempt'
PY
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
