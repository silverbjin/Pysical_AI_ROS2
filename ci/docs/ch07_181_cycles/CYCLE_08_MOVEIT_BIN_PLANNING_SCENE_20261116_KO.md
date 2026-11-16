# G04B Cycle 08 — MoveIt PlanningScene / Gazebo 실제 bin 충돌 정합

- 날짜: 2026-11-16 / Issue #181 / Draft PR #202
- 기준 원격 main: `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 이전 실제 증거: [Cycle07 L2 #43770622882](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43770622882), Artifact **14184565359**, ZIP SHA256 `b529217444359f86e4de17304824c30cc13e7cabac73bb6b9c9d54358ce1e423`.
- **상태: 개발/단위 검증, G04B BLOCKED, G05 NOT_RUN, Ch10 HOLD**.

## RED — 문제의 구조

Cycle07 원본은 `bin_support::bin_collision`과 `my_robot::link4::link4_collision` 실제 Gazebo 접촉 **5,371개**를 기록했다. High MoveGroup(64.798~67.828s) 도중 **66.427s**에 첫 native 접촉, 이후 joint2 명령 vs 실제 속도 분리. 최종 joint1 error **0.219196rad**. 실제 물체 lift **0.11083m**와 1.3초 hold는 통과했지만, 하강·release/settled ROI 미실행.

MoveGroup이 성공이라고 보고해도 Gazebo의 정적 장애물은 별도 계획장면에 등록하지 않으면 예측 경로에서 제외될 수 있다. 기존 witness에는 static bin의 `CollisionObject` 등록이 없었다.

## 인과 가설 한 개와 예상 반증

**MoveIt이 Gazebo의 동일 bin 충돌 형상을 받아 계획하면, link4가 bin에 닿는 고위치 경로를 피하거나 안전한 경로가 없을 때 계획을 거절한다.**

반증:
- 등록 서비스 성공 후에도 동일 collision pair 발생·joint 추종 실패: PlanningScene 동기화만으로 해결되지 않은 것(장면/보간/부착 물체/물리 정확성 후속 분석).
- 원본 객체 등록은 성공하지만 MoveGroup이 경로를 찾지 못함: 기존 경로의 충돌 회피 가능성을 별도 검토, 로봇을 강제 이동시키지 않음.
- 서비스·좌표계·SDF 불일치: Goal 전 STOP, L2 물리 결과 UNKNOWN.

## GREEN — 변경 사항

1. `ci/ch07_181_bin_moveit_scene_contract.py`: 테스트 SDF의 static `g04_bin_support`, world pose [0.55,0.25,1.63]m, 원래 collision BOX [0.30,0.30,0.20]m 정확 일치 및 로컬 pose 미존재 검증, **world-mutating code 없음**.
2. `ci/tests/test_ch07_181_bin_moveit_scene_contract.py`: 정상 형상 및 변형된 pose/size/static/충돌 offset 모두 거절하는 fail-closed 단위시험.
3. `ci/ch07_77_g04b_actual_physics_witness.py`: 실제 물체 파지·1.3초 hold 이후, high Goal 이전에 `/apply_planning_scene` ROS 2 서비스로 `CollisionObject.ADD`를 동기 적용. 프레임은 world-fixed `base_link`, 장애물 형상은 원본 SDF와 동일. Apply 응답 `success=True` 아니면 Goal 전 중지.
4. `ci/ch07_77_g04b_physical_once.sh`: **동일 원본 Gazebo world 파일 경로만** 전달. 기존 world collision/geometry/robot/rod 그대로.
5. `.github/workflows/book-ch07-77-g04b-real-grasp.yml`: 원본 소스의 SHA·Python L0 테스트, 실제 Gazebo L2는 명시적 신규 라벨 승인형.

**절대 변경하지 않은 기준:** 50g 동적 원통, ROS 7관절, DART solver, 마찰/게인, FJT/MoveGroup tolerance, lift≥0.05m·hold 1.3s·실제 양측 접촉·world custody·release·settled bin XY/height. No teleport, no fake grasp/attached object.

## 테스트/증거 기록 (후속 커밋에서 확정)

- 소스 SHA: 이 문서 포함 커밋으로 확정
- L0: PENDING
- 실제 Gazebo L2: NOT_RUN
- Original raw Artifact/ZIP SHA256: NOT_RUN
- 첫 실패 및 PASS 범위: PENDING, **G04B BLOCKED**

## 교육용 회고

**로봇 제어기 실패처럼 보이는 문제가 실제로는 경로 계획기의 환경 모델 누락 때문일 수 있다.** 실제 충돌 센서와 Action 피드백의 타임스탬프를 결합해 하드웨어 명령 재전송이 아닌 환경 모델 정합 문제를 식별하고, 물리 세계를 손대지 않은 채 계획장면 한 개만 변경하는 실험을 설계한다.

검증 계층: L0 geometry/frame/schema ≠ L2 실제 피드백·접촉/안착, 문서·계획기 성공만으로 G04B 완료 선언 불가.
