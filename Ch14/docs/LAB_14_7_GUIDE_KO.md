# 14.7 CPU Docker 배포 실습 — T14~T16
## 0. 범위와 사전 준비
Ubuntu24.04 ROS Jazzy 기반 Linux Docker Engine 검수. Windows는 WSL2 Docker Desktop 또는 WSL 내부 Engine 중 하나만 사용합니다. Docker Desktop의 host network 지원/설정은 별도 검증해야 합니다. GPU나 실제 장치 전달 불필요. CPU image는 Gazebo 실행용 이미지가 아니며, 설치된 replay 패키지 4개와 rosbag2/ORT/CycloneDDS를 사용합니다. 모델/fixture는 외부 권리 확인 후 로컬에서 확보하며 배포 이미지나 저장소에 넣지 않습니다. 모든 명령은 검증된 source의 Ch14에서 실행합니다. G06 CI 결과는 인수 원장 참조; WSL2 owner NOT_RUN.
## 1. T14 — CPU 이미지 빌드
\`\`\`bash
docker version
docker compose version
docker info
export CH14_IMAGE=ch14-ai:cpu
bash docker/build_cpu.sh
docker image inspect "$CH14_IMAGE" --format '{{.Id}} {{.Size}}'
docker run --rm --network none "$CH14_IMAGE" bash -ec \
 'test ! -e /opt/robot_ws/src; python -m pip check; ros2 pkg prefix ch14_ai_perception; ros2 pkg prefix ch14_performance_monitor'
\`\`\`
Dockerfile의 pinned ROS base와 lock 복제본 일치 확인. 빌드 컨텍스트는 Ch14, build_cpu.sh는 자신의 경로를 기준으로 찾습니다. 선택 CH14_WHEELHOUSE는 hash-verified wheels의 디렉토리; 없으면 다운로드. Builder의 일반 colcon install을 runner의 동일 경로에 복사합니다. rosdep의 ament_python은 가상 build type이라 해당 키만 제외하고 setuptools/colcon_ros 실제 설치 및 import/빌드로 확인합니다. 전체 rosdep 무시 금지. apt/rosdep live resolution은 장래 변경될 수 있으므로 빌드 결과 image ID와 dpkg 목록을 보존합니다.
## 2. 고정 실습 자산 준비
아래는 pinned COCO RGB 원본 (455085), synthetic aligned 2m depth 및 TF X=1m의 로컬 bag을 생성하는 실습입니다. 실제 Gazebo 센서 기록은 아닙니다. 해당 파일의 원래 사용 조건과 AGPL 조건을 확인하고 동의하는 경우에만 fetch/export를 실행합니다. 원본/변환 모델/영상/bag 재배포 금지.
\`\`\`bash
RUN="$(mktemp -d "$HOME/ch14-g06.XXXXXX")"
mkdir -p "$RUN/fixture" "$RUN/bags" "$RUN/evidence"
curl -fsSL --proto '=https' --proto-redir '=https' \
 -o "$RUN/fixture/000000455085.jpg" \
 https://huggingface.co/datasets/merve/coco/resolve/9e50abcdc1361852f34841af4939cbcd2d37c92f/val2017/000000455085.jpg
echo "022d2068d525b03a753287c333c09026fe22b9ae6d8071d4e8c757cbed32bdc4  $RUN/fixture/000000455085.jpg" | sha256sum -c -
docker run --rm -v "$RUN:/work:rw" "$CH14_IMAGE" bash -ec '
 python /opt/ch14/scripts/fetch_models.py yolov8n --cache /work/cache --fetch --acknowledge-agpl
 python /opt/ch14/python/export_yolo.py --manifest /opt/ch14/models/model_manifest.json --cache /work/cache --model yolov8n --output /work/models --threads 1
 python /opt/ch14/scripts/g06_make_bag.py --image /work/fixture/000000455085.jpg --bag /work/bags/ch14_rgbd --receipt /work/bag-receipt.json
 ros2 bag info /work/bags/ch14_rgbd
'
export CH14_MODELS="$RUN/models" CH14_BAGS="$RUN/bags" CH14_EVIDENCE="$RUN/evidence"
export MODEL_SHA256="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["onnx_sha256"])' "$RUN/models/export.json")"
export ROS_DOMAIN_ID=89
echo "$MODEL_SHA256  $CH14_MODELS/yolov8n.onnx" | sha256sum -c -
\`\`\`
Bag에는 RGB, depth, CameraInfo, static TF가 포함되고 /clock은 저장하지 않습니다. player가 단 하나의 /clock을 생성합니다. 동일 domain의 기존 simulator/player를 종료하거나 별도 미사용 domain을 선택하십시오.
## 3. T15 — 단일 컨테이너
\`\`\`bash
bash docker/run_docker.sh
\`\`\`
이 스크립트는 독립 detector만 실행합니다. 유효 결과에는 별도 sensor/monitor가 필요합니다. T15 자동 검수는 g06_deploy_ci.sh의 single phase: 같은 image로 monitor와 sensor를 각각 별도 container에서 실행하고, 잘못된 domain readiness 거부와 정상 실제 DDS/point 결과를 확인합니다. Ctrl+C/TERM은 소유한 container만 정리하고 inspect/log를 evidence에 남깁니다. 실행 자체는 결과 수신 성공을 의미하지 않습니다. Compose와 동시에 같은 domain에서 실행하지 않습니다.
## 4. T16 — Compose 3서비스
\`\`\`bash
docker compose -p ch14-lab -f docker/compose.yaml config
docker compose -p ch14-lab -f docker/compose.yaml \
 up --pull never --abort-on-container-exit --exit-code-from sensor-source
docker compose -p ch14-lab -f docker/compose.yaml ps -a
docker compose -p ch14-lab -f docker/compose.yaml logs --no-color > "$RUN/evidence/compose.log"
docker compose -p ch14-lab -f docker/compose.yaml down --timeout 18
\`\`\`
sensor-source는 depends_on만 신뢰하지 않습니다. 실제 detector heartbeat SHA와 monitor discovery, RGB/depth subscription, /clock publisher 부재를 확인한 뒤 bag을 단일 재생합니다. ai-inference는 ORT CPU async, monitor는 실제 bus+동일 stamp odom point, debug topics 및 /clock 수를 기록합니다. monitor.json과 컨테이너 각각 exit code를 확인하십시오. Compose parent exit0만으로 성공 판정하지 않습니다. CI는 scripts/g06_verify_deployment.py로 동일 image ID, mounts/privilege, source trace Age, worker join, DDS stamp overlap, 3개 이상의 실제 의미/3D 매칭까지 검증합니다. independent receive Age는 수신기 최신 /clock 기준이며 원본 발행 순간의 독립 Age와 동일하지 않습니다.
## 5. 실패 디버깅과 종료
잘못된 model SHA/경로는 detector 시작 전 거부. DDS domain mismatch는 gate timeout 후 bag NOT_STARTED. 다른 /clock 발행자가 있으면 replay 금지. 진단: docker compose ps/logs, actual topic graph, model hash, clock ownership 순서. 종료는 소유한 project만 down. 모든 기존 로봇/컨테이너를 일괄 삭제하지 않습니다. G04 Gazebo shutdown은 reports/G04_SHUTDOWN_BOUNDARY_DEBUG_KO.md 별도. CPU Docker replay에는 네이티브 Gazebo가 없습니다. WSL2 GUI/GPU는 미검증.
