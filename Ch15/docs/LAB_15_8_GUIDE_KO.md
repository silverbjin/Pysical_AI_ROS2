# 15.8 FMEA, 안전 정지 및 bounded recovery
## 환경
WSL2 Ubuntu24.04 ROS2 Jazzy, isolated mock domains only. 4개 이상의 available CPU; 실제 로봇/다른 ROS graph와 절대 연결하지 않는다. G08은 기본 mission_executor와 별개의 recovery_executor를 사용한다. 모든 명령은 Ch15가 포함된 고정 source SHA checkout의 repo root에서 실행. 기존 G04–G07 실습 반복 불필요.
```bash
source /opt/ros/jazzy/setup.bash
# 의존 패키지가 없으면 apt/rosdep으로 설치: rosbag2, rosbag2-storage-mcap, py-trees, rmw-cyclonedds-cpp, nav2-msgs, tf2-ros, nav2-behaviors, colcon, python3-yaml.
REPO="$PWD"
WS="$HOME/ch15-g08-ws"
mkdir -p "$WS"
cd "$WS"
colcon build --base-paths "$REPO/Ch15/ros2_ws/src" --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission
source install/setup.bash
export G03_INSTALL="$WS/install"
export ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER CYCLONEDDS_URI
cd "$REPO"
python3 -m unittest discover -s Ch15/tests -p test_g08_contracts.py -v
OUT="$HOME/ch15-g08-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir "$OUT"
# 사례별 새 domain, 순차 실행, raw bag은 사용자 로컬에만 보존.
for case in F03_transient:90 F03_persistent:91 F04:92 F06:93 F01:94; do
  mode="${case%:*}"; export ROS_DOMAIN_ID="${case#*:}"
  timeout --signal=INT --kill-after=20s 100s python3 Ch15/tests/g08_record_probe.py "$mode" "$OUT/$mode" || break
  python3 Ch15/python/g08_analyze.py "$OUT/$mode" "$mode" || break
done
python3 Ch15/tests/g08_nav2_plugin_audit.py "$OUT/nav2-plugin-audit.json"
python3 Ch15/python/stage_g08_receipts.py "$OUT" "$OUT-public"
```
검수 시 각 case metrics/result 및 종료 로그 확인. 위 순차 실습은 사용자가 처음 체험할 때만 실행; 개발 CI 성공 증거는 재사용. 실패 시 원본을 지우지 말고 첫 실패 경계와 로그를 분석. G09에서 owner entrypoint/전체 archive를 통합하고 실제 WSL2 인수 별도.
## 원리
F03 탐색1 실패 → 정착 및 fresh target → 탐색2 성공 → 원래 업무 leaf 전부 성공. persistent 3번 실패는 ABORTED. F04는 APPROACHING wrong epoch/stale을 거절하고 Pick Goal0. F06은 ABORTED exact UUID terminal 이후 새로운 관측 및 정착을 확인한 뒤 다음 Goal; 3회 실패 ABORTED. recovery 자체 성공이 원 업무 완료가 아니다. 준비 실패도 3회 예산 포함. 안전 latch 상태에서 신규 Goal 금지; reset 우회 없음. C24 예제의 py_trees Retry와 달리 실제 executor는 RetryBudget으로 준비/Goal/terminal을 명시적으로 관리한다. G09에서 본문 코드와 API 대응 검수.
F01은 actual Mock command 차단과 UUID 회수; source stamp 만료 및 paused clock receipt 감시를 분리한다. Zero Twist는 실물 정지 증거가 아니다. Nav2 behavior example YAML은 설치 plugin declaration/library audit만, Spin/BackUp 실제 실행 금지. FMEA/최종 인수 보고서 및 receipt를 함께 읽는다.

## G09 공통 실행 경로
Ch15 루트, `CH15_SOURCE_SHA`를 실제 고정 HEAD로 설정하고 `bash scripts/run_lab.sh 15.8 --profile mock --scenario F01` 실행. 상세 선행 환경과 evidence archive는 [15.9](LAB_15_9_GUIDE_KO.md) 참조. 문서 조회와 실제 실행을 구분한다.
