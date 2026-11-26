#!/usr/bin/env bash
set -Eeuo pipefail
: "${CH14_IMAGE:?set tested CPU image tag or ID}"
: "${CH14_MODELS:?set model directory}"
: "${MODEL_SHA256:?set verified export SHA}"
: "${CH14_EVIDENCE:?set evidence directory}"
domain="${ROS_DOMAIN_ID:-89}"
[[ "$domain" =~ ^[0-9]+$ ]] && ((10#$domain<=232)) || { echo "invalid ROS_DOMAIN_ID"; exit 2; }
[[ "$MODEL_SHA256" =~ ^[0-9a-f]{64}$ ]]
models="$(realpath "$CH14_MODELS")";out="$(realpath "$CH14_EVIDENCE")"
[[ -d "$out" && -f "$models/yolov8n.onnx" && ! -L "$models/yolov8n.onnx" ]]
echo "$MODEL_SHA256  $models/yolov8n.onnx" | sha256sum -c -
docker info >/dev/null
docker image inspect "$CH14_IMAGE" >/dev/null
name="ch14-run-${CH14_RUN_ID:-$$}"
cid=""
cleanup(){
  rc=$?
  trap - EXIT INT TERM
  if [[ -n "$cid" ]]; then
    if [[ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" == true ]];then docker stop --signal SIGINT --time 18 "$cid" >/dev/null || rc=1;fi
    docker logs "$cid" > "$out/single-detector.log" 2>&1 || rc=1
    docker inspect "$cid" > "$out/single-inspect.json" || rc=1
    code="$(docker inspect -f '{{.State.ExitCode}}' "$cid")"
    [[ "$code" == 0 ]] || rc=1
    docker rm "$cid" >/dev/null || rc=1
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 0' INT TERM
cid="$(docker run -d --name "$name" --init --network host --stop-signal SIGINT --stop-timeout 18 --cap-drop ALL --security-opt no-new-privileges \
 -e ROS_DOMAIN_ID="$domain" -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e MODEL_SHA256 \
 -v "$models:/models:ro" "$CH14_IMAGE")"
echo "$cid" > "$out/single-container-id.txt"
docker wait "$cid" > "$out/single-exit.txt" &
wait "$!"
