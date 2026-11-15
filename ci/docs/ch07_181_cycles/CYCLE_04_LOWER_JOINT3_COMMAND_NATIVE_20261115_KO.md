# G04B 개발·디버깅 Cycle 04 — `lower_into_bin` joint3 명령/물리 인과 계측

- 날짜: 2026-11-15 / Issue #181 / Draft PR #202
- 기준 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 직전 Cycle 03 baseline commit `34c4647b73e729090d07cb81da99702ae5a25be7`
- 상태: **L0 사전검증 전 / 실제 Gazebo L2 미실행 / G04B BLOCKED**

## 1. 원본 재사용 및 첫 실패

기존 실제 [CI #43721071561](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43721071561), original Artifact `14163978713`, ZIP SHA256 `b8e2a0bbb99accef578047e714819ff25ad8abce261baeb9e76b824fdbdfbd44`. PR HEAD `98abded...`과 Actions PR merge checkout `52685f...`의 git tree SHA `7fcedef...` 일치.

실제 G04B bilateral finger 2mm / lift 0.11424m / hold 1.3s drift 0.000336m / high XY 0.01243m / high max joint error 0.00855rad까지 부분 성공. 이후 하강 MoveGroup은 성공으로 판정했으나 실제 joint3는 목표 `1.25483988379rad`에 대해 `~1.12347rad`, 오차 `0.13137rad`. 연이은 단 1회 엄격 FJT도 실제 joint3 `1.1286038789rad`, 오차 `0.1262360rad`, ABORTED(status6,error−5).

**핵심 불확실성:** 관절3에 실제 hardware command와 native Gazebo 속도 명령이 전달됐는지, 전달됐음에도 물리 제약으로 정체하는지 기존 원본에는 원자적으로 연결된 시계열이 없음. joint3 실제 ROS joint upper `2.0944rad`이므로 목표 자체가 상한 초과는 아님.

## 2. 한 가지 반증 가능한 계측 가설

- `lower_into_bin` MoveGroup 및 이후 실패한 FJT 구간의 `/arm_group_controller/controller_state` **joint3 reference/feedback/error**와 `/controller_manager/introspection_data/full` 실제 `command_interface.joint3/position`, native Gazebo `JointVelocityCmd`·`JointPosition`·`JointVelocity`를 동일 `sim_time_s`로 연결하면 첫 단절을 식별할 수 있다.
- **반증 기준:** Goal/hardware에서 목표가 빠진 경우 ROS/ros2_control 경계, native velocity cmd 없음은 Gazebo command 경계, **cmd가 존재하지만 실제 native velocity≈0**이면 제약/구동 경계. 관절이 이동했지만 오차가 남는 경우 목표 도달·물리 부하로 분류. 증거 누락은 UNKNOWN.
- 기존 50g 물체 contact stream과 동기화하되 contact 한 쌍으로 DART 원인을 단정하지 않는다.

## 3. 변경 단위 및 안전 기준

1. 기존 read-only Gazebo ECS C++ 플러그인에서 **joint3 하나만 추가**. physics update 함수를 호출하거나 원본 joint를 수정하지 않는다.
2. 기존 ROS typed witness에 joint3 reference/feedback/error와 HW command, lower stage 시작/완료 시간, abort 후 원본을 저장한다. 물리 motion/solver/robot/world, FJT/MoveGroup 목표/허용차 변경 **없음**.
3. read-only 진단기 `ci/ch07_181_lower_joint3_native_audit.py`는 8개 이상 시계열에서만 비영 cmd 대 실제 미이동 결론, 어떤 결과에서도 **G04B BLOCKED**.
4. focused L0 TDD는 `ci/tests/test_ch07_181_lower_joint3_native_audit.py`. 기존 전송 성공·파지 원본 재실행하지 않는다.
5. L0 확인 후 승인형 Gazebo L2 **단 한 번** 실행, 원본 Artifact 감사. 가설이 깨지면 같은 Goal 재시도 금지.

## 4. 사이클 결과

- 개발 커밋: PENDING
- **L0 RED:** [#43725218239](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43725218239)에서 기존 구조 테스트 1건 FAIL. 기존 ECS 객체 이름이 finger1+finger2+joint2로만 한정돼 새 read-only joint3 계측을 허용하지 않는 **오래된 테스트 전제**가 원인.
- **수정:** 기존 `test_ch07_181_arm_joint2_readonly_boundary.py`에서 요청 관측 joint3 추가를 허용. 기존 ECS mutation 금지 및 물리 인수 게이트는 변함없음.
- **L0 GREEN:** PENDING
- L2: NOT_RUN
- raw artifact/ZIP SHA256: NOT_RUN
- 최초 실패/가설 채택 여부: PENDING

## 5. 교육용 회고 항목

- MoveGroup의 성공과 실제 ROS 관절 목표 도달을 구분하는 이유
- 두 번의 실패가 같은 FJT 오차처럼 보여도 controller→hardware→native 차이를 모르면 가설을 세울 수 없는 이유
- 테스트용 PGS 변경을 원복하고 원본 성공 일부를 보존하는 이유
- 독립 실제 동적 물체 release·settled ROI가 없으면 완료 판정이 불가능한 이유

**G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
