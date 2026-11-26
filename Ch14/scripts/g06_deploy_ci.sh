#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
out="$(realpath "$1")"
work="$(mktemp -d)"
stage=init
single_pid=""
single_cid=""
monitor_cid=""
sensor_cid=""
project="ch14-g06-${GITHUB_RUN_ID:-$$}"
export CH14_IMAGE="ch14-ai:cpu-${GITHUB_RUN_ID:-$$}"
export CH14_WHEELHOUSE="$(realpath "$2")"
export CH14_RUN_ID="${GITHUB_RUN_ID:-$$}"
export CH14_MODELS="$work/models" CH14_BAGS="$work/bags"
export ROS_DOMAIN_ID=89
export CH14_UID="$(id -u)" CH14_GID="$(id -g)"
mkdir -p "$out/single" "$out/compose" "$work/bags" "$work/fixture"
cleanup(){
 rc=$?
 trap - EXIT
 set +e
 if [[ -n "$single_pid" ]] && kill -0 "$single_pid" 2>/dev/null;then kill -TERM "$single_pid";wait "$single_pid";fi
 for cid in "$monitor_cid" "$sensor_cid";do if [[ -n "$cid" ]];then docker stop --signal SIGINT --time 18 "$cid" >/dev/null 2>&1;docker rm "$cid" >/dev/null 2>&1;fi;done
 if [[ -n "$single_cid" ]] && docker inspect "$single_cid" >/dev/null 2>&1;then docker stop --signal SIGINT --time 18 "$single_cid" >/dev/null;docker rm "$single_cid" >/dev/null;fi
 if [[ -n "${MODEL_SHA256:-}" ]];then CH14_EVIDENCE="$out/compose" docker compose -p "$project" -f "$root/docker/compose.yaml" down --timeout 18 > "$out/compose-down.log" 2>&1;fi
 # The bag and model bytes are local evaluation inputs, never upload as evidence.
 rm -rf "$work" || rc=1
 printf '{"status":"%s","stage":"%s","exit_code":%d,"scope":"G06_CPU_DOCKER"}\n' "$(if ((rc==0));then echo PASS;else echo FAIL;fi)" "$stage" "$rc" > "$out/result.json"
 exit "$rc"
}
trap cleanup EXIT
stage=build
docker version > "$out/docker-version.txt"
docker compose version > "$out/compose-version.txt"
bash "$root/docker/build_cpu.sh" 2>&1 | tee "$out/docker-build.log"
imageid="$(docker image inspect "$CH14_IMAGE" --format '{{.Id}}')"
echo "$imageid" > "$out/image-id.txt"
docker image inspect "$CH14_IMAGE" > "$out/image-inspect.json"
docker run --rm --network none "$CH14_IMAGE" bash -ec 'test ! -e /opt/robot_ws/src; test ! -e /opt/robot_ws/build; python -m pip check; ros2 pkg prefix ch14_ai_common; ros2 pkg prefix ch14_ai_interfaces; ros2 pkg prefix ch14_ai_perception; ros2 pkg prefix ch14_performance_monitor; cat /opt/ch14/evidence/dpkg-versions.txt' > "$out/installed-smoke.log"
stage=assets
curl -fsSL --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 90 -o "$work/fixture/000000455085.jpg" https://huggingface.co/datasets/merve/coco/resolve/9e50abcdc1361852f34841af4939cbcd2d37c92f/val2017/000000455085.jpg
echo "022d2068d525b03a753287c333c09026fe22b9ae6d8071d4e8c757cbed32bdc4  $work/fixture/000000455085.jpg" | sha256sum -c -
docker run --rm --user "$CH14_UID:$CH14_GID" -e HOME=/tmp -e ROS_LOG_DIR=/tmp/ch14-ros-logs -v "$work:/work:rw" "$CH14_IMAGE" bash -ec '
 python /opt/ch14/scripts/fetch_models.py yolov8n --cache /work/cache --fetch --acknowledge-agpl
 python /opt/ch14/python/export_yolo.py --manifest /opt/ch14/models/model_manifest.json --cache /work/cache --model yolov8n --output /work/models --threads 1
 python /opt/ch14/scripts/g06_make_bag.py --image /work/fixture/000000455085.jpg --bag /work/bags/ch14_rgbd --receipt /work/bag-receipt.json
 ros2 bag info /work/bags/ch14_rgbd
 ' 2>&1 | tee "$out/asset-prep.log"
cp "$work/models/export.json" "$out/model-export.json"
cp "$work/bag-receipt.json" "$out/bag-receipt.json"
export MODEL_SHA256="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["onnx_sha256"])' "$out/model-export.json")"
stage=offline
docker run --rm --user "$CH14_UID:$CH14_GID" -e HOME=/tmp --network none --cap-drop ALL --security-opt no-new-privileges -e MODEL_SHA256 -v "$CH14_MODELS:/models:ro" -v "$work/fixture:/fixture:ro" "$CH14_IMAGE" python -c '
import cv2,json,os
from ch14_ai_common.backends import OrtBackend,NAMES
from ch14_ai_common.yolo import preprocess,postprocess
e=OrtBackend("/models/yolov8n.onnx",os.environ["MODEL_SHA256"],2)
x,m=preprocess(cv2.imread("/fixture/000000455085.jpg"))
ds=postprocess(e.forward(x),m,.5,.45)
hits=[dict(label=NAMES[d.class_id],score=d.confidence,xyxy=list(d.xyxy)) for d in ds]
assert any(d["label"]=="bus" for d in hits)
print(json.dumps(dict(status="PASS",provider=e.session.get_providers(),detections=hits)))
' | tee "$out/offline-inference.json"
stage=single
export CH14_EVIDENCE="$out/single"
env_common=(--init --user "$CH14_UID:$CH14_GID" -e HOME=/tmp -e ROS_LOG_DIR=/tmp/ch14-ros-logs --network host --stop-signal SIGINT --stop-timeout 18 --cap-drop ALL --security-opt no-new-privileges -e ROS_DOMAIN_ID -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e MODEL_SHA256)
# Run from unrelated working directory; verify script does not depend on CWD.
(cd /tmp && exec bash "$root/docker/run_docker.sh") > "$out/single/runner.log" 2>&1 &
single_pid=$!
for _ in $(seq 1 100);do [[ -s "$out/single/single-container-id.txt" ]] && break;kill -0 "$single_pid";sleep .1;done
single_cid="$(cat "$out/single/single-container-id.txt")"
monitor_cid="$(docker run -d "${env_common[@]}" -v "$out/single:/evidence:rw" "$CH14_IMAGE" python /opt/ch14/scripts/g06_monitor.py --out /evidence/monitor.json)"
# Actual isolated domain must fail readiness without starting bag.
if docker run --rm "${env_common[@]}" -e ROS_DOMAIN_ID=91 "$CH14_IMAGE" python /opt/ch14/scripts/g06_runtime.py ready --timeout 2 > "$out/single/wrong-domain.log" 2>&1;then echo "wrong domain accepted";exit 1;fi
grep -q 'DDS readiness timeout; bag NOT_STARTED' "$out/single/wrong-domain.log"
sensor_cid="$(docker run -d "${env_common[@]}" -v "$CH14_BAGS:/bags:ro" "$CH14_IMAGE" python /opt/ch14/scripts/g06_runtime.py sensor)"
[[ "$(timeout 60s docker wait "$sensor_cid")" == 0 ]]
sleep .3
docker stop --signal SIGINT --time 18 "$monitor_cid" "$single_cid" >/dev/null
wait "$single_pid";single_pid=""
docker logs "$sensor_cid" > "$out/single/sensor.log" 2>&1
docker logs "$monitor_cid" > "$out/single/monitor.log" 2>&1
docker inspect "$sensor_cid" > "$out/single/sensor-inspect.json"
docker inspect "$monitor_cid" > "$out/single/monitor-inspect.json"
python3 "$root/scripts/g06_verify_deployment.py" --out "$out/single" --image-id "$imageid" --phase single
docker rm "$sensor_cid" "$monitor_cid" >/dev/null
sensor_cid="";monitor_cid="";single_cid=""
stage=compose
export CH14_EVIDENCE="$out/compose" ROS_DOMAIN_ID=90
compose=(docker compose -p "$project" -f "$root/docker/compose.yaml")
"${compose[@]}" config > "$out/compose/resolved.yaml"
"${compose[@]}" up --pull never --abort-on-container-exit --exit-code-from sensor-source 2>&1 | tee "$out/compose/up.log"
mapfile -t cids < <("${compose[@]}" ps -aq)
[[ "${#cids[@]}" == 3 ]]
docker inspect "${cids[@]}" > "$out/compose/compose-inspect.json"
"${compose[@]}" logs --no-color ai-inference > "$out/compose/compose-ai.log"
"${compose[@]}" logs --no-color sensor-source > "$out/compose/sensor.log"
"${compose[@]}" logs --no-color monitor > "$out/compose/monitor.log"
python3 "$root/scripts/g06_verify_deployment.py" --out "$out/compose" --image-id "$imageid" --phase compose
"${compose[@]}" down --timeout 18
[[ -z "$("${compose[@]}" ps -aq)" ]]
echo "CLEANUP_PASS" > "$out/compose/cleanup.txt"
stage=complete
