# 13.7 Behavior Tree 미션 오케스트레이션 실습

이 실습은 기존 Go2+Piper의 Nav2 접근·RGB-D 관측·MoveIt 파지를 하나의 BT에서 지휘한다. 실제 기본 mission은 같은 engine에서 **이동→정착→새 관측→파지·lift·hold→권한 회수·정상 종료**다. 운반 귀환·기립·충전은 별도 모의 실습이다. 실제 배터리 센서·YOLO 일반 객체 인식·실기 검증으로 해석하지 않는다.

## 다운로드와 준비

아래 명령은 저장소 루트에서 실행한다. 게시 전에는 로컬 `feat/ch13-section-13-7` 작업본을 사용한다. 원격에 아직 없는 branch를 다운로드할 수 있다고 가정하지 않는다. 게시 여부와 실행 인수는 SECTION_13_7_REPORT_KO.md를 확인한다.

공개 저장소는 https://github.com/silverbjin/Pysical_AI_ROS2 이다. 13.7 branch 게시 후에는 새 폴더에서 다음과 같이 받는다.

```bash
git clone --filter=blob:none --sparse --single-branch --branch feat/ch13-section-13-7 \
 https://github.com/silverbjin/Pysical_AI_ROS2.git Pysical_AI_ROS2_13_7
cd Pysical_AI_ROS2_13_7
git sparse-checkout set Ch13/docs Ch13/dependencies Ch13/config \
 Ch13/scripts/reuse_13_5 Ch13/scripts/reuse_13_6 Ch13/scripts/reuse_13_7 \
 Ch13/ros2_ws/src/ch13_reuse_wire Ch13/ros2_ws/src/ch13_navigation_reuse \
 Ch13/ros2_ws/src/integrated_robot_vision Ch13/ros2_ws/src/ch13_manipulation_reuse \
 Ch13/ros2_ws/src/ch13_piper_moveit_config Ch13/ros2_ws/src/ch13_manipulation_planner \
 Ch13/ros2_ws/src/ch13_mission_orchestration
git rev-parse HEAD
```

[13.6 준비 가이드](LAB_13_6_REUSE_GUIDE_KO.md)와 그 가이드가 참조하는13.5 준비에서 Ubuntu24.04/ROS2 Jazzy, Nav2/MoveIt/TRAC-IK, 기존 시뮬레이터 venv, 원본94자산을 준비한다. 소스는13.7 branch를 사용하고 13.6 build 명령 대신 아래를 사용한다. 자산 위치는 저장소 상위 `upstream-iit-locomanipulation-d010212`다. 모델·가중치는 저장소에서 재배포하지 않는다. `Ch13/config`를 빼면 vision 설치가 실패한다.

기존 ROS 환경에 BT 의존성을 더하는 표준 방법은 다음과 같다. 전역 pip3 설치는 하지 않는다.

```bash
sudo apt update
sudo apt install ros-jazzy-py-trees ros-jazzy-py-trees-ros
```

관리자 권한 없이 검증한 공식 deb를13.7 전용 위치에 추출하는 대안도 제공한다. 기존 ROS 의존성은 준비돼 있어야 한다. 검증 버전은 py_trees/py_trees_ros2.6.0, interfaces2.1.2, pydot1.4.2, pyparsing3.1.1이며 정확한 패키지 버전과 hash를 도구가 검사한다. 저장소에서 해당 버전을 더 이상 제공하지 않으면 임의 대체하지 말고 버전/API를 다시 확인한다.

```bash
export CH13_REUSE_BUILD="$HOME/ch13_reuse_13_7_build"
export CH13_REUSE_VENV="$HOME/ch13_reuse_iit_d010212_venv"
bash Ch13/scripts/reuse_13_7/prepare_bt_deps.sh
bash Ch13/scripts/reuse_13_7/build.sh
```

새 빌드는6개 기존 패키지와 새 `ch13_mission_orchestration`을 설치한다. 기존 R2/R5/13.6 개발·검증 경로 및 realpath가 겹치는 경로는 거절한다. 기존 env.sh의13.6 기본값을 사용하지 않는다. 각 터미널에서 두 export를 동일하게 지정하고 실행은13.7 env.sh로 감싼다. ROS CLI는 시스템 Python, 시뮬레이터는 지정 venv를 사용하며 터미널 전체에 venv를 activate하지 않는다. ROS_DOMAIN_ID135·localhost·CPU 제한은 실행 도구 안에서만 설정한다.

13.7 실행은 해당 명령에만 적용되는 Python startup 경로로 ROS apt Python 의존성을 venv 뒤에서 찾는다. venv의 NumPy/torch/MuJoCo 우선순위와 전역 설정은 보존한다. 시스템 Python에서 import 성공했다고 실제 venv 실행도 성공한다고 가정하지 않는다. 현재 기본 동결은 section_13_7_bt_v7.json이며 과거 동결은 해당 준비/실행 이력이다. 실제 인수의 정확한 소스 범위(v3 정상/저전력, v5 파지 취소/기본 경로)는 결과 보고서를 따른다.

## 13.7.1~3: 미션을 트리로 표현하기

`tree.py`의 실제 트리는 memory=False Selector 아래에 안전 중단 가지와 memory=True Fetch Sequence를 둔다. Fetch의 잎은 Battery→Navigate→Find→Pick→Finish다. Navigate 성공은 goal accepted가 아니라 실제 terminal SUCCEEDED와 실측 정착이다. Finish는 planner/engine/자식 회수까지 완료돼야 성공한다.

정상·저전력·기립·물체 없음 모의 실습은 실제 로봇 프로세스를 실행하지 않는다. 출력 profile은 항상 mock이다. 출력 파일은 새 이름을 사용한다.

```bash
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_7/run_mock.py normal mock_fetch_01.json
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_7/run_mock.py low_battery mock_battery_01.json
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_7/run_mock.py fallen mock_recovery_01.json
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_7/run_mock.py not_found mock_missing_01.json
```

기대 결과는 normal/fallen SUCCESS, low_battery ABORTED, not_found FAILURE다. normal의 요청 순서는 navigate/find/pick/return/finish, low_battery는 navigate/charge이며 pick이 없어야 한다. fallen은 recover가 navigate보다 먼저다. 이는 모의 행동의 BT 순서 검증이며 실제 운반·충전·기립 성능이 아니다.

## 13.7.4: Blackboard와 데이터 수명

각 mission은 고유 Blackboard namespace를 사용한다. target_pose에는 좌표뿐 아니라 원본 관측 payload와 session을 보관한다. capture_ns/capture_wall/TF 시각·first receipt/GID/hash를 유지하며 now로 갱신하지 않는다. Find는 도착 후 새 capture를 기다린다. Pick은 현재 engine의 원본 관측과 live lease를 다시 검사하므로 오래된 JSON을 넣어 권한을 만들 수 없다.

모의/실제 출력의 ticks[].target_pose 또는 bt_ticks.jsonl에서 Find 이전 None→Find 성공 후 원본 관측 payload 변화를 확인한다. 원통은 알려진 반경2cm·높이8cm·20g이며 RGB-D 표면 fit이다. 콜라/부엌은 원고의 설명 이름이고, 실제 profile은 upright 원통/접근 지점이다.

## 13.7.5~6: 비동기 잎과 실제 통합

잎의 initialise는 단계 요청을 한 번 보내고 update는 snapshot만 읽는다. 실제 ROS 작업은 한 소유 worker에서 순차 진행한다. BT node와 robot node는 별도 executor/context를 사용한다. update/terminate에서 sleep·결과 대기·nested spin을 하지 않는다.

Nav2의 goal response와 결과 future를 분리하고, INVALID 뒤 늦게 수락된 goal도 소유자가 취소한다. 취소 ACK와 실제 terminal·정착은 다르다. 기존 팔/gripper actuator 경계·정책·힘 cap·속도·수명은 유지한다.

한 번에 하나의 engine만 실행한다. 새 사례 경로는 존재하지 않아야 한다. 다음은 학생 기본 실제 실습이다. 별도 전체 unit/matrix나 과거 PASS 파일을 요구하지 않는다.

```bash
bash Ch13/scripts/reuse_13_7/run_case.sh normal Ch13/evidence/section_13_7_bt/my_fetch_01
cat Ch13/evidence/section_13_7_bt/my_fetch_01/mission_verification.json
```

기대 결과는 result=PASS와 모든 checks=true다. BT SUCCESS만으로 물리 파지를 통과시키지 않는다. 실제 상승≥9cm, hold≥2sim초, TCP 상대 변화≤2cm, HOLD 양 finger 접촉≥90%와 기존 원본 RGB-D 재계산·정상 종료를 확인한다. 각 팔 action 제한120sim초/240wall초와 전체 mission 시간을 구분한다. 정상 파지는 수분이 걸릴 수 있으며 실제 측정 시간은 결과 보고서를 따른다.

## 13.7.7: 상태 시각화

사례의 `run/tree.dot`와 `run/tree.txt`는 최종 구조/상태 자료다. `run/bt_ticks.jsonl`은10Hz visited/status와 Blackboard 기록이며 `run/bt_summary.json`은 단계 요청·시작·완료·session·종료 결과다. py_trees_ros native snapshot 발행도 연결돼 있다. 정적 PNG가 자동으로 애니메이션되는 것은 아니다.

Graphviz가 설치돼 있으면 DOT를 그림으로 변환할 수 있다.

```bash
dot -Tpng Ch13/evidence/section_13_7_bt/my_fetch_01/run/tree.dot -o tree_fetch_01.png
```

## 13.7.8: 반응성과 실제 중단

Selector 첫 자식에 배터리 Condition만 놓고 FAILURE를 반환하면 다음 이동 가지가 선택된다. 이 실습은 StopRequired→CancelAndSettle의 우선순위 가지를 사용하며 abort latch로 자동 재시작을 방지한다. 배터리 시작 조건은 Main Sequence에도 있다. BT의10Hz 틱은 기존300ms 안전 watchdog을 대체하지 않는다.

실제 저전력 주입은 소프트웨어 교육값이며 실제 배터리 센서가 아니다. 실제 운동이 관찰된 뒤 실행 중 Nav goal을 취소하고 정착·회수한다. 자동 충전 이동은 mock에서만 한다.

```bash
bash Ch13/scripts/reuse_13_7/run_case.sh low_battery Ch13/evidence/section_13_7_bt/my_stop_01
cat Ch13/evidence/section_13_7_bt/my_stop_01/mission_verification.json
```

기대 BT terminal은 ABORTED지만, 의도한 주입→실제 canceled terminal→정착→회수·잔여 없음이 모두 확인되면 시험 판정은 PASS다. pick/finish 명령이 뒤늦게 시작되면 FAIL이다. 입력 복구나 배터리 값 복구 후 자동 재시작하지 않는다. 파지 중 중단 시 임의 개방/수납/torque0을 하지 않는다.

안전 가지가 성공적으로 종료되면 트리 root 상태는 SUCCESS여도 mission terminal은 ABORTED다. 실제 임무 완료 여부는 bt_summary.json의 terminal과 최종 판정에서 확인한다.

파지 후 중단은 개발자용 추가 사례다. 실제 LIFT action이 EXECUTING인 상태에서1sim초를 관찰한 뒤 취소한다. 실제 취소 terminal 이후2sim초 이상의 힘 유지·낙하≤5mm·접촉을 검사하며9cm lift 성공과 구분한다.

```bash
bash Ch13/scripts/reuse_13_7/run_case.sh held_cancel Ch13/evidence/section_13_7_bt/my_held_stop_01
```

## 실패와 개발 검증

freeze/source/install 불일치면 build 및 사용한 branch/환경부터 확인한다. 임의로13.6 freeze를 수정하지 않는다. 관측 만료는 원본 capture·TF·최초 receipt를 조사하며300ms 기준을 늘리거나 header를 now로 바꾸지 않는다. worker 오류는 navigation_summary.json의 error와 launch.log를 확인한다. 종료 불능·잔여 PID/lock은 실패이며 다음 engine을 실행하지 않는다. 기존 소유 mission의 정상 회수 경로를 사용하고 lock을 임의 삭제하지 않는다.

개발자 부품·회귀는 engine이 모두 종료된 뒤 실행한다.

```bash
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_6/run_tests.py \
 Ch13/ros2_ws/src/ch13_navigation_reuse/test \
 Ch13/ros2_ws/src/ch13_manipulation_reuse/test \
 Ch13/ros2_ws/src/ch13_mission_orchestration/test
```

과거13.6 v13/v14 성공·실패와 동결은 그대로 보존한다.13.7 결과를 v14 전체16개 PASS나 반복 강건성 검증으로 표현하지 않는다. 이 개발은 단일 작업자 자체 검토다.

## 게시 증거 복원·재판정

각 사례는 모델을 제외한 raw.tar.gz와 raw_manifest.json으로 보관한다.13.6의 안전 복원 도구는 폴더 이름에 종속되지 않으며 archive·각 파일 hash를 확인하고 기존 파일이 다르면 덮어쓰지 않는다. 기본 sparse 다운로드에 없는 사례는 해당 UUID 폴더를 추가로 받는다.

```bash
git sparse-checkout add Ch13/evidence/section_13_7_bt/보고서의_UUID
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_6/restore_evidence.py Ch13/evidence/section_13_7_bt/보고서의_UUID
bash Ch13/scripts/reuse_13_7/env.sh Ch13/scripts/reuse_13_7/verify_mission.py \
 Ch13/evidence/section_13_7_bt/보고서의_UUID \
 Ch13/evidence/section_13_7_bt/보고서의_UUID/my_new_verdict.json
```

위 재판정 명령은 BT 사례용이다. legacy_free는 기존13.6 verify_navigation.py와 새 --output 경로를 사용한다. 기존 verdict 파일은 재사용하지 않는다. 과거 소스 동결과 현재 소스가 다르면 새 engine 실행 전에 현재 기본 동결을 사용한다. 과거 사례의 오프라인 재판정은 새 실행 권한을 만들지 않는다.
