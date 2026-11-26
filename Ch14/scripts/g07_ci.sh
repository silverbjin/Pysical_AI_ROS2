#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=environment
trap 'rc=$?; printf "{\"status\":\"%s\",\"stage\":\"%s\",\"exit_code\":%d}\n" "$(if ((rc==0));then echo PASS;else echo FAIL;fi)" "$stage" "$rc" > "$out/result.json"' EXIT
source /ch14/scripts/g07_env.sh "$out"
export ROS_DOMAIN_ID=97 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
stage=colcon
mkdir -p /tmp/rl_ws/src
cp -a /ch14/ros2_ws/src/ch14_rl_deployment /tmp/rl_ws/src/
(cd /tmp/rl_ws && python "$(command -v colcon)" build --packages-select ch14_rl_deployment) 2>&1 | tee "$out/colcon.log"
set +u
source /tmp/rl_ws/install/setup.bash
set -u
stage=training
if [[ -f /reuse/smoke-receipt.json ]];then
 cp /reuse/smoke-receipt.json "$out/"
 mkdir -p "$out/smoke_bundle"
 cp /reuse/smoke_bundle/{final_model.zip,manifest.json,result.json} "$out/smoke_bundle/"
else
 python /ch14/scripts/g07_train_smoke.py --out "$out"
fi
# Only the exact new owner-source smoke model and metadata are retained for reuse.
readarray -t hashes < <(python -c 'import json;d=json.load(open("/evidence/smoke-receipt.json"));print(d["checkpoint_sha256"]);print(d["manifest_sha256"])')
stage=export
python /ch14/python/export_rl_policy.py --bundle "$out/smoke_bundle" --checkpoint-sha256 "${hashes[0]}" --manifest-sha256 "${hashes[1]}" --out "$out/export" --scope SMOKE_ONLY
stage=contracts
G07_EXPORT="$out/export" python -m pytest -q -p no:cacheprovider /ch14/tests/test_g07_contracts.py --junitxml="$out/contracts.xml"
stage=shadow
python /ch14/scripts/g07_shadow_probe.py --export "$out/export" --out "$out"
stage=complete
