# 13.6 Go2+Piper 정밀 조작 실습

기능 인수 대상은 v13 교육용 시뮬레이션 profile이다. 입력 손실1개의 원판정 FAIL과 별도 검토 PASS를 함께 공개한다. 실제 인수 판정·대표 UUID·제한은 [최종 보고서](SECTION_13_6_REUSE_REPORT_KO.md)를 함께 확인한다.

설치 후 핵심 재현은 **pick 실행→verify_pick 결과 확인**이다. 한 mission이 접근·정착·계획·파지·들기를 연결하며 앞선 시험의 PASS 파일을 요구하지 않는다. 소절별로 분리해서 배우려면 hold→arm_normal→moveit→pick을 수행한다. 각 명령의 검증 도구가 실제 결과와 종료를 자동 판독한다. 전체 부품 시험과 아래 실패 주입·13.5 회귀는 개발/선택 심화 과정이며 매 실습마다 전부 반복할 필요가 없다. [게이트·검증 비용 점검](SECTION_13_6_REUSE_GATE_REVIEW_KO.md)에 유지/제거 이유를 정리했다.

## 준비

이 실습은 Ubuntu 24.04/WSL2, ROS 2 Jazzy, MuJoCo 3.13.0, 원본 IIT-DLSLab 정책과 94개 고정 자산을 사용한다. 원본 모델·mesh·가중치는 Git 저장소에 재배포하지 않는다. [13.5 준비 가이드](LAB_13_5_REUSE_GUIDE_KO.md)의 준비1(OS/Nav2), 준비3(94자산), 준비4(venv)를 참조하되 **소스는 아래13.6 브랜치**를 받는다.13.5의 준비2 브랜치나114파일 동결을 새13.6 소스에 적용하지 않는다. 다른 로봇의 MoveIt 설정이나 과거 Task8 checkout을 사용하지 않는다.

13.6 소스 branch는 `feat/ch13-section-13-6-manipulation`이다. main에 병합된 것으로 가정하지 않는다. 저장소 루트가 현재 위치인지 확인한다. 아래 Linux 명령의 작업 위치는 모두 그 저장소 루트다. 이미 실행 중인 엔진이 있으면 소유 mission에서 정상 회수한 다음 진행한다.

기존 작업 폴더를 덮지 않는 새 위치에서 다운로드한다. 아래 sparse 범위는6개 패키지·도구·계약·문서와 부품 시험이 읽는 실제 TOTG fixture를 포함한다.

```bash
mkdir -p "$HOME/physicalai_13_6"
cd "$HOME/physicalai_13_6"
git clone --filter=blob:none --sparse --depth 1 --single-branch \
  --branch feat/ch13-section-13-6-manipulation \
  https://github.com/silverbjin/Pysical_AI_ROS2.git Pysical_AI_ROS2
cd Pysical_AI_ROS2
git sparse-checkout set Ch13/docs Ch13/dependencies Ch13/config Ch13/verification/reuse_13_6 \
  Ch13/scripts/reuse_13_5 Ch13/scripts/reuse_13_6 \
  Ch13/ros2_ws/src/ch13_navigation_reuse Ch13/ros2_ws/src/ch13_reuse_wire \
  Ch13/ros2_ws/src/integrated_robot_vision Ch13/ros2_ws/src/ch13_manipulation_reuse \
  Ch13/ros2_ws/src/ch13_piper_moveit_config Ch13/ros2_ws/src/ch13_manipulation_planner \
  Ch13/evidence/section_13_6_reuse/2ece9bb8-1960-44de-b92b-31325ae5dc18
git rev-parse HEAD
```

그다음13.5 준비3의 다운로드 블록을 **이 저장소 루트**에서 실행해 저장소 상위의 `upstream-iit-locomanipulation-d010212`를 준비한다. 기존 폴더가 있으면94개 hash만 검증하며 자동 덮어쓰지 않는다. 준비4의 고정 venv를 만든 뒤 아래 추가 의존성과6개 패키지 build를 진행한다.13.5의3개 패키지용 build만으로는 충분하지 않다.

기존 추론 환경은 `/home/jinho/ch13_reuse_iit_d010212_venv`, 이 실습 전용 build는 `/home/jinho/ch13_reuse_13_6_build`다. 다른 경로를 쓰면 모든 터미널에 `CH13_REUSE_VENV`와 `CH13_REUSE_BUILD`를 동일하게 지정한다. R2/R5 build를 덮지 않는다. ROS CLI는 시스템 Python, 시뮬레이터는 지정 venv를 사용한다. 추론 venv를 터미널 전체에 activate하지 않는다.

MoveIt 2.12.4, moveit_msgs 2.6.0, TRAC-IK 2.0.2가 검증 환경에 이미 설치돼 있었다. 새 환경에서는 ROS 공식 패키지 관리로 MoveIt·TRAC-IK·colcon 의존성을 준비한 뒤 실제 버전을 확인해야 한다. 이번 개발에서 apt/pip 설치·시스템 라이브러리 변경은 하지 않았다. 버전이 다른 경우 원고의 개념 코드를 그대로 실행하지 말고 설치 API와 이 패키지의 계약을 확인한다.

ROS Jazzy 기본 설치·13.5 의존성/venv 준비가 끝난 새 Ubuntu24.04 환경에서는 다음 추가 패키지를 준비한다. 이 명령은 새 환경 설치 안내이며 검증 개발 환경에서 다시 실행하지 않았다. MoveIt 공식 Jazzy binary 설치는 [공식 안내](https://moveit.ai/install-moveit2/binary/)를 따른다. 검증된 기존 RMW를 유지한다.

```bash
sudo apt update
sudo apt install ros-jazzy-moveit ros-jazzy-moveit-py ros-jazzy-moveit-msgs ros-jazzy-trac-ik-kinematics-plugin python3-colcon-common-extensions python3-pytest libssl-dev
```

```bash
export CH13_REUSE_BUILD="$HOME/ch13_reuse_13_6_build"
export CH13_REUSE_VENV="$HOME/ch13_reuse_iit_d010212_venv"
source /opt/ros/jazzy/setup.bash
dpkg-query -W ros-jazzy-moveit ros-jazzy-moveit-py ros-jazzy-trac-ik-kinematics-plugin ros-jazzy-moveit-msgs
bash Ch13/scripts/reuse_13_6/build.sh
```

빌드는 6개 패키지를 선택하고 통합 MuJoCo 모델에서 URDF/SRDF를 로컬 생성한다. 외부 자산 hash가 다르면 중단한다. 시뮬레이션 실행 중 build나 pytest를 병행하지 않는다.

두 export는 이 실습에 쓸 모든 터미널에서 동일하게 적용한다. 실행 도구의 `env.sh`가 각 명령 안에서 ROS·해당 install·추론 환경을 준비하므로 venv를 전역 activate할 필요가 없다. 별도 ROS CLI 터미널에서 관찰하려면 시스템 Python을 유지한 채 다음 환경을 적용한다.

```bash
source /opt/ros/jazzy/setup.bash
source "$CH13_REUSE_BUILD/install/setup.bash"
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=135
ros2 topic echo /ch13/reuse/manipulation/status
```

R2/R5 build 및 그 하위 경로는 거절한다. 기본 실행기는 v13 동결을 요구하며, 동결 파일 누락·해시 불일치 시 설치 감사나 엔진을 시작하지 않는다. 다른 revision을 재현할 때만 `CH13_REUSE_FREEZE`를 명시하며 그 revision과 실제 소스가 일치해야 한다.

현재 인수 입력은 `section_13_6_reuse_acceptance_v13.json`의 소스248개·외부94자산이다. 이전v1~v12는 각 성공·실패·진단 이력으로 보존한다. 기존13.5의114파일 동결과 같다고 주장하지 않는다. 각 실행은 동결·설치 파일/생성 모델/ELF 감사를 거친다. 엔진 보고서에는 실제 compiled model과 정책 hash도 남는다.

```bash
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/freeze_runtime.py verify Ch13/dependencies/section_13_6_reuse_acceptance_v13.json
```

## 13.6.1~2: 같은 엔진의 인계와 계획 장면

13.5 단독 실행을 끝낸 뒤 팔 노드를 새로 붙이는 방식이 아니다. 아래 mission은 Nav2 접근·실제 정착·원본 관측을 확인한 바로 그 엔진을 유지한다. 과거 summary의 READY는 작업 권한이 아니다. 한 번에 한 명령만 실행한다. 각 증거 경로는 존재하지 않는 새 이름이어야 한다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh hold Ch13/evidence/section_13_6_reuse/my_hold_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_handoff.py Ch13/evidence/section_13_6_reuse/my_hold_01
```

기대 결과는 동일 session에서 2wall초 이상 READY 유지, 명시 REVOKED, 엔진·RX·renderer·원본 thread join과 잔여 없음이다. 접근 중 VISION_EXPIRED가 발생하면 실패 증거를 보존한다. 기준을 낮추거나 과거 JSON으로 우회하지 않는다.

계획 장면에는 ground plane, 벽과 받침, 관측 대상 형상을 넣는다. 다리·팔 실제 joint_states와 실제 몸체 TF를 사용한다. planning group은 `manipulator_arm`, TCP는 `reuse/tcp`, base는 `reuse/base`다. MoveIt는 별도 joint_states/TF 발행자가 아니다. TRAC-IK와 OMPL RRTConnect로 계획한다.

## 13.6.3: 좌표와 원본 시각

실제 카메라의 320×240 RGB-D와 촬영 시점 이전 100ms 이내 TF를 사용한다. `last_accepted_observation.json`에는 optical point, map point, T_map_camera, calibration, capture/receipt/GID와 내용 hash가 있다. 최신 TF로 과거 이미지를 변환하거나 header를 now로 바꾸지 않는다. map↔odom은 현재 교육 profile의 ground-truth localization이다. SLAM/AMCL 성공을 뜻하지 않는다.

13.5의 붉은 상자는 보이는 표면점이다. 물리 파지 profile에서는 알려진 upright 원통 반경 2cm·높이 8cm와 RGB-D 표면 fit으로 중심을 추정한다. yaw나 일반 물체 6D pose를 관측한 것이 아니다. 실제 freejoint 위치는 실행 후 평가 파일에만 기록한다.

13.6 물리 파지의 가상 카메라는 base 기준 `[0.4,0.25,0.25]m`, 안쪽 yaw `-20°`다. 팔이 원통 상단을 가리는 문제를 조사한 뒤 선택한 교육 profile이며 실물 설치 검증은 아니다. 13.5 기본 카메라는 유지한다. MuJoCo3.13.0에서 skybox를 끄고 같은 실제 렌더 버퍼의 RGB·원본 depth를 읽는다. 두 정적 장면에서 기존 depth와 전체 오차0을 확인했으며 다른 버전으로 자동 확장하지 않는다.

v4부터 같은 renderer process가 RGB/depth/CameraInfo/원본 metadata의 유일한 DDS 발행자다. 부모의 큰 영상 보존 큐를 실시간 전달 경로에서 분리했다. 촬영 시각·픽셀·native 최초 receipt/GID를 바꾸지 않는다. 모든 원본 촬영 목록은 `renderer_captures.json`과 `sensor_summary.json`의 `captures`에 회수하며 부모가 보존한 큰 스냅샷 건수와 다를 수 있다. 기본13.5는 부모 발행을 유지한다. GC 시간은 관측만 하며 정책이나 시스템 설정은 변경하지 않는다.

저장한 관측의 optical→map→실제 trunk 변환을 확인한다. 이것은 오프라인 좌표 연습이며 저장 JSON은 새 명령 권한이 아니다.

원고의 `Time()` 최신 TF 예시 대신 원본 촬영 시각에 대응하는 과거 변환을 사용한다. 실습의 계획 장면과 pose 요청 기준은 `reuse/odom`, 팔 mount 기준은 실제 `reuse/base`다. 유효한 TF로 표현하면 두 좌표의 같은 점이다. 흔들리는 몸체를 고정 world TF로 대체하지 않는다. 아래 도구는 같은 촬영의 camera→map→trunk 계산과 camera→trunk 직접 계산이 일치하는지 확인하며 TF 시각과 capture 시각을 별도 출력한다.

```bash
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/inspect_target_frames.py Ch13/evidence/section_13_6_reuse/my_pick_01
```

## 13.6.4~5: 계획·실행과 픽킹

먼저 작은 팔 시험과 MoveIt 도달/거절/직선/취소 시험을 수행한다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh arm_normal Ch13/evidence/section_13_6_reuse/my_arm_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_arm.py Ch13/evidence/section_13_6_reuse/my_arm_01
bash Ch13/scripts/reuse_13_6/run_case.sh moveit Ch13/evidence/section_13_6_reuse/my_moveit_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_moveit.py Ch13/evidence/section_13_6_reuse/my_moveit_01
```

원고의 `plan().execute()`/`compute_cartesian_path()`는 개념 코드다. 실제 [Python 래퍼](../ros2_ws/src/ch13_manipulation_reuse/ch13_manipulation_reuse/planning.py)는 단일 MoveIt 장면의 GetMotionPlan/GetCartesianPath와 기존 엔진의 FollowJointTrajectory를 사용한다. 이 버전의 ExecuteTrajectory 취소 문제 때문에 그것과 병렬로 실행하지 않는다. 장면 hash·실제 시작 관절·관측 age를 재확인하고 전체 Cartesian fraction=1만 허용한다. 0.9는 충분하지 않다.

원통의 두 roll 대칭 후보는 raw TOTG 시간만 비교하지 않는다. 실제 실행과 같은C2·관절·속도·가속도·120sim초 검사를 먼저 수행하고, 통과한 후보 중 정규화 시간이 짧은 것을 고른다. 경로점 간격은 물리 주기2ms보다 짧아도 연속 곡선의 한계를 만족하면 유효하다. 후보 검사는 원래 경로를 변경하지 않고 실제 실행 때 현재 장면·상태·관측을 다시 확인한다. 모두 거절되면 실행하지 않는다. 경로점을 삭제하거나120초 제한을 늘려 우회하지 않는다.

| 원고의 개념 동작 | 실행 패키지의 실제 경로 |
|---|---|
| IK·장애물 회피 pose 계획 | `Planner.plan(pose_goal=...)`→MoveIt GetMotionPlan·TRAC-IK·OMPL |
| 직선 접근·lift | `Planner.cartesian(...)`→GetCartesianPath, fraction1·끝점 검사 |
| 계획 실행 | `Planner.execute(...)`→C2/한계/시작 상태 검사→native FollowJointTrajectory→실측 terminal |
| gripper open/close | 표준 GripperCommand→원본 joint7 actuator, joint8은 원래 equality 연동 |
| 대상 부착 표현 | 실제 양 finger 접촉 확인 이후 planning scene geometry만 attach |

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh pick Ch13/evidence/section_13_6_reuse/my_pick_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_pick.py Ch13/evidence/section_13_6_reuse/my_pick_01
```

동일 엔진에서 open→12cm pre-grasp→직선 접근→close→양 finger 실제 접촉→직선 10cm lift→2초 hold→작업 후 정착·회수를 수행한다. 대표 v13 정상 pick의 engine 실행 구간은 약318wall초였다(각1회 측정, 시작/감사는 별도). 120sim초/240wall초 제한은 개별 팔 action에 적용하며 mission 전체의 제한이 아니다. 대상은 20g 동적 원통이며 원본 gripper cap 0.5N을 유지한다. planning scene attach는 충돌 표현이며 물리 부착이 아니다. 판정은 실제 상승≥9cm, 2sim초 이상 유지, TCP에 대한 상대 변화≤2cm, HOLD 중 90% 이상 양 finger 접촉으로 한다. `pick_assessment.json`과 독립 verifier가 PASS여야 한다. 팔 action 성공이나 빈 그리퍼 close만으로 파지 성공이라고 해석하지 않는다.

양 finger normal force가 실제 확인된 뒤 native PD의 내부 reference로 0.5N 이내 닫기 힘을 유지한다. nominal close와 내부 reference를 별도 기록한다. 첫 lift 뒤 새 RGB-D로 상승 부족을 확인하면 한 번만, 최대3cm 추가 직선 보정한다. 보정량에는 실측 팔 끝의 목표 추종 지연을 포함한다. 관측 상승95mm·실제 팔 최대 속도0.003rad/s 이내와 기존 base 정착이0.5sim초 유지되어야 HOLD에 들어간다. 물체 정답 좌표를 제어 입력으로 쓰지 않는다. 물체 질량·마찰·접촉 차원·모터 cap은 보정 때문에 바꾸지 않는다. [계약v6](../dependencies/section_13_6_pick_contract_v6.json)에 수치와 변경 이유가 있다.

## 13.6.6~7: 안정성·실패·종료 판독

속도·가속도 scaling은 0.08, native trajectory 한계는 0.05rad/s·0.1rad/s²다. 다리는 기존 정책으로 계속 지지한다. torso 고정/teleport나 새 WBC·재학습으로 대체하지 않는다. 팔에는 원본 Kp/Kd·힘 cap을 유지한 명시적 모델 bias 보정 v2가 사용된다. [설계 변경 기록](SECTION_13_6_REUSE_ENGINEERING_DECISIONS_KO.md)을 읽는다.

도달 불가·충돌 거절은 팔을 실행하지 않아야 한다. Cartesian fraction<1은 pre-grasp나 목표 자세를 재검토할 이유이며 부분 경로를 실행하지 않는다. 접촉 허용은 지정 finger-target 쌍만 단계에 따라 변경한다. 전체 padding/충돌 검사를 꺼서 성공시키지 않는다.

| 증상 | 판독과 다음 조치 |
|---|---|
| No solution / 계획 거절 | 실제 좌표·팔 작업 영역·자기/환경 충돌을 확인한다. 재접근이 필요하면 기존 작업 권한을 회수하고 새 mission을 시작한다. |
| Cartesian fraction<1 | 경로 전체를 거절한다. pre-grasp·도구 방향·joint jump·충돌을 확인한다. |
| OBSERVATION_EXPIRED / VISION_EXPIRED | 원본 capture·렌더 종료·최초 receipt·추론·engine 처리 시각을 구분한다. 기존 실패를 보존하고 새 UUID로 실행한다. header나300ms 기준을 바꾸지 않는다. |
| camera warmup deadline | `renderer_startup.json`에서 spawn→target 진입→ROS import/init→Node→Renderer→첫 render 시각을 구분한다. 마지막 단계 이름만으로 전체 지연 원인을 단정하지 않는다. 종료한 자식은 별도 exit 오류로 표시한다. |
| pytest에서만 자식 시작이 느림 | 지정한 `run_tests.py`를 사용한다. 기존 여러 시험 파일이 추가한 중복 모듈 검색 경로는 수집 후 정리되며 소스 우선순위는 유지된다. 실제 엔진의15초 시작 기한을 늘려 통과시키지 않는다. |
| gripper stalled | 기계적 막힘이다. 실제 양 finger 접촉·높이·유지 검증 없이는 파지 성공이 아니다. |
| LIFT_HEIGHT / lift settling absent | 실측 상승 또는 작업 정착 부족이다. 물리 판정 FAIL을 보존한다. mass/마찰/force cap을 조용히 바꾸지 않는다. |
| 잔여 PID/lock | 새 engine을 실행하지 않는다. 같은 소유 mission의 정상 회수 결과부터 확인한다. |

다음 실패 주입은 선택 심화 또는 배포 전 개발 인수다. 기본 pick 실습을 마친 학생이 매번 전부 반복할 필요는 없다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh arm_cancel Ch13/evidence/section_13_6_reuse/my_cancel_01
bash Ch13/scripts/reuse_13_6/run_case.sh arm_loss Ch13/evidence/section_13_6_reuse/my_loss_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_arm.py Ch13/evidence/section_13_6_reuse/my_cancel_01 Ch13/evidence/section_13_6_reuse/my_loss_01
bash Ch13/scripts/reuse_13_6/run_case.sh duplicate Ch13/evidence/section_13_6_reuse/my_duplicate_01
bash Ch13/scripts/reuse_13_6/run_case.sh expire Ch13/evidence/section_13_6_reuse/my_expire_01
bash Ch13/scripts/reuse_13_6/run_case.sh old_session Ch13/evidence/section_13_6_reuse/my_old_session_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_handoff.py Ch13/evidence/section_13_6_reuse/my_duplicate_01 Ch13/evidence/section_13_6_reuse/my_expire_01 Ch13/evidence/section_13_6_reuse/my_old_session_01
bash Ch13/scripts/reuse_13_6/run_case.sh observation_loss Ch13/evidence/section_13_6_reuse/my_observation_loss_01
bash Ch13/scripts/reuse_13_6/run_case.sh duplicate_action Ch13/evidence/section_13_6_reuse/my_duplicate_action_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_safety.py Ch13/evidence/section_13_6_reuse/my_observation_loss_01 Ch13/evidence/section_13_6_reuse/my_duplicate_action_01
bash Ch13/scripts/reuse_13_6/run_case.sh held_cancel Ch13/evidence/section_13_6_reuse/my_held_cancel_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_held_cancel.py Ch13/evidence/section_13_6_reuse/my_held_cancel_01
```

취소 ACK와 실제 terminal을 구분한다. fault/cancel은 제한된 감속·hold로 이어지며 torque0/무조건 수납·파지 중 임의 개방하지 않는다. 관측 300ms 초과·시계 역행·중복 소유자는 fault latch다. 입력이 복구돼도 자동 재활성화하지 않는다. 실행 도구는 계획기를 살아 있는 엔진 시계에서 먼저 회수하고 엔진을 정상 종료한 뒤 자식·renderer·lock 잔여를 확인한다. 강제 종료가 발생한 실행은 정상 회수 PASS로 세지 않는다.

위 실패 주입 시험은 의도한 fault·실제 정지·정상 회수가 모두 확인되면 시험 자체는 PASS다. 반대로 주입 전에 우연한 관측 만료가 나면 해당 시나리오 PASS가 아니다. 파지 중 취소는2sim초 유지·낙하5mm 이내·양 finger 접촉을 검사하며9cm 물리 pick 성공과 별도 결과다.

13.5 기본 실행의 회귀는 새13.6 install에서 manipulation 옵션을 끈 아래 경로다. 원래 R5 install을 덮거나 과거 evidence를 갱신하지 않는다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh nav_free Ch13/evidence/section_13_6_reuse/my_nav_free_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_5/verify_navigation.py Ch13/evidence/section_13_6_reuse/my_nav_free_01/run
# 같은 방법으로 nav_cancel, nav_raw_loss, nav_vision을 서로 다른 새 폴더에서 순차 실행한다.
```

새 실행을 만들기 전에 실패 폴더를 지우지 않는다. 다른 기존 engine이 검출되면 실행을 멈추고 그 소유 mission에서 회수한다. 오래된 PID 파일만 보고 프로세스를 죽이거나 lock 파일을 삭제하지 않는다.

## 선택: 개발용 부품 시험

소스 수정이나 설치 문제를 조사할 때 엔진을 모두 종료한 뒤 수행한다. 정상 배포본을 따라 하는 매회 실습의 필수 과정은 아니다.

```bash
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/run_tests.py Ch13/ros2_ws/src/ch13_navigation_reuse/test Ch13/ros2_ws/src/ch13_manipulation_reuse/test
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/audit_saved_timing.py timing_audit_new.json
```

두 번째 명령은 로컬에 원본 궤적이 저장된 사례만 재검사하며 새 엔진이나 명령 권한을 만들지 않는다. 새 출력 이름을 사용한다. 시간 검사 통과는 충돌/실제 파지 성공과 별개다.

## 게시 증거 복원

실행 로그·관측·물리 측정은 사례별 `raw.tar.gz`와 `raw_manifest.json`으로 게시한다. 원본 파일은 개발 환경에 그대로 남긴다. archive와 각 파일 hash를 확인한 뒤 복원하며 기존 파일이 다르면 덮어쓰지 않는다. 모델·가중치·생성 URDF/SRDF와 그것을 포함한 `planner.yaml`은 내용 재배포 대신 hash/로컬 경로만 기록한다. 실제 인수 UUID는 최종 보고서를 참조한다.

```bash
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/restore_evidence.py Ch13/evidence/section_13_6_reuse/보고서의_UUID
# 이후 같은 사례에 해당하는 verify_pick.py / verify_moveit.py / verify_safety.py 등을 실행한다.
```

sparse 다운로드에서 아직 받지 않은 게시 사례는 먼저 `git sparse-checkout add Ch13/evidence/section_13_6_reuse/보고서의_UUID`로 해당 archive·manifest를 받은 뒤 복원한다.

13.6 궤적은 시작 시 검증한 전체 표준 action을2ms 물리 주기에서 평가한다. 기존13.5의 `arm_joint1_offset` 시험 parameter는13.6에서 비활성화하며, 그5Hz 입력 제한을500Hz 새 궤적 샘플링과 혼동하지 않는다. 비전15Hz 상한·원본 capture300ms/과거TF100ms는 별도 계약으로 유지한다.

지원 범위는 원본 보행 정책의 zero 명령 지지와 명시한20g 교육용 시뮬레이션이다. 별도 Crawl/Stand 드라이버 모드, trunk shift 전신 제어, SLAM/AMCL, 실기 하중·드라이버와 일반6D 물체 인식을 검증한 것은 아니다. 원고의 CoM 보상은 설명 대상이며 이번 재사용 패키지에서 새 WBC를 구현하지 않는다.

입력 손실 개발 인수의 원래 판정과 별도 검토를 함께 재현하려면 보고서 UUID의 증거를 복원한 뒤 다음을 실행한다. 기존 FAIL 파일은 수정하지 않는다.

```bash
bash Ch13/scripts/reuse_13_6/env.sh Ch13/verification/reuse_13_6/review_loss.py Ch13/evidence/section_13_6_reuse/a854efd7-67fc-4964-aced-0fd36b59f7bf injected_loss_review_new.json
```

이는 정해진 주입·정지·회수 조건의 오프라인 재검토이며 새 실행 권한이나 일반 timeout 허용이 아니다. 원래 검증기의 FAIL과 두 판정기의 hash를 최종 보고서에서 함께 확인한다.