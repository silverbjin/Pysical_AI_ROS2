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
- **L2 FAIL** [#43725514319](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43725514319) — 하강 단계에 도달하지 못함.
- **raw Artifact #14166535736, ZIP SHA256** `19cc19c1dff5a2fc42837b9ffe53ac6d059a12326912dbfb768b9dd8ac53a628`. GitHub PR merge checkout `2dbc6c916e62eb1ffd19084a5b86b06d5af51bde` (parents `1aadc...`, source `637e2dac...`), tree 동일함을 기록.
- 최초 실패/가설: `G04B_181_HIGH_MOVEGROUP_ACTUAL_JOINT_TRACKING_FAILED` at `transfer_high_above_bin`, high 실제 joint2 오차 `0.010442392497322692rad` > `0.010rad`. **lower_into_bin NOT_RUN**, joint3 인과 가설 미검증.

## 5. 교육용 회고 항목

- MoveGroup의 성공과 실제 ROS 관절 목표 도달을 구분하는 이유
- 두 번의 실패가 같은 FJT 오차처럼 보여도 controller→hardware→native 차이를 모르면 가설을 세울 수 없는 이유
- 테스트용 PGS 변경을 원복하고 원본 성공 일부를 보존하는 이유
- 독립 실제 동적 물체 release·settled ROI가 없으면 완료 판정이 불가능한 이유

**G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**

## 6. Cycle 04 종료 — L2 실행 경로 미도달의 의미

동일 물리 기준선(DART default solver)에서 lift **0.130040m**, 1.3초 hold drift **0.001026679m**까지는 실제 Gazebo로 확인했다. 그러나 고위치 MoveGroup은 `joint2` actual 목표 오차 **0.0104423925rad**, 즉 엄격한 `0.010rad` 기준보다 **0.0004423925rad** 초과. 목적지 하강, 직접 FJT, release, settled ROI 미실행이며 `lower_joint3_native_first_boundary.json`의 결론은 **`UNKNOWN_NO_LOWER_GOAL`**이다. 해당 값을 물리 관절3 고착/해결 증거로 바꿔 쓰면 안 된다.

기존 PGS 시험 [#43721071561](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43721071561)은 high 실제 오차 `0.0085488rad`로 high 인수는 통과, 이후 lower joint3 실제 0.126236rad 미도달. **서로 다른 실제 원본의 PASS를 혼합해 가상의 전체 G04B 성공을 만들 수 없다**.

### 종료 판단

- **계측기 개발 및 L0** 완료, 실제 관절3의 native causal info는 아직 얻지 못했으므로 구체적 physics 원인은 **UNKNOWN**.
- Dantzig 조건에서 고위치 관절2 오차 0.01rad 부근에 있는 실행 간 변동이 하강 단계 재현을 가로막는다. 근거 없는 재실행 금지.
- 다음 Cycle 05는 **이전에 실제 고위치를 통과한 PGS world의 동일 단일 조건**에 Cycle 04의 read-only joint3 관측기만 적용하여 하강의 첫 실패를 계측하는 것으로 제한한다. PGS가 정식 물리 해결책이라는 주장이나 신규 motion 목표 변경은 없다. 이 실행 역시 실패 시 G04B BLOCKED.

**Cycle 04 CLOSED** / G00–G04A NOT_RERUN / **G04B BLOCKED** / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.
