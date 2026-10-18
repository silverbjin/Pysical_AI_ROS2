# Ch13 13.1 통합 모바일 매니퓰레이터 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ch13만으로 빌드·설치하여 12DoF 4족 베이스, 6DoF 팔, 2지 그리퍼를 Gazebo Harmonic과 MuJoCo 3.3.7에서 실행하고 관절·TF·명령 소유권 및 제한된 물리 파지를 검증한다.

**Architecture:** 순수 Python 패키지 `ch13_sim_core`가 20관절 계약, 명령 중재, MJCF와 엔진 독립 검증 로직을 소유한다. ROS 2 패키지 `ch13_robot_description`은 결합 Xacro·Gazebo 자원을, `ch13_control`은 상태 집계·명령 중재·MuJoCo bridge·Gazebo router·공통 launch를 소유한다. 한 실행에서는 한 backend만 활성화하며 모든 actuator 명령은 단일 중재 출력만 거친다.

**Tech Stack:** Python 3.10+, pytest 8.4.2, NumPy 1.26.4, MuJoCo 3.3.7, ROS 2 Jazzy, Gazebo Harmonic, Xacro, ament_python, ament_cmake

**Spec:** `Ch13/docs/SECTION_13_1_DESIGN_KO.md`

## Global Constraints

- 기준 커밋은 `1451f54a64374f2ff150a39429cc89e9e3b07696`이다.
- Ch05~Ch12 파일은 수정하지 않는다.
- Ch13 실행은 Ch05~Ch12의 build/install/log, overlay 또는 Python source path에 의존하지 않는다.
- 좌표는 REP-103의 +X 전방, +Y 좌측, +Z 상방이며 선형 단위는 m, 각도 단위는 rad이다.
- 관절은 다리 12, 팔 6, 그리퍼 2의 총 20개이며 모든 배열은 이름으로 매핑한다.
- 같은 ROS domain에서 Gazebo와 MuJoCo를 동시에 물리·clock 소유자로 실행하지 않는다.
- 기본 launch는 정책/동작 비활성 또는 안전 hold이며 명시적 인자 없이 로봇을 움직이지 않는다.
- MoveIt 2, 통합 `ros2_control` SystemInterface, whole-body control, 안정 PPO 보행은 구현 완료 범위에 포함하지 않는다.
- 실제 엔진을 실행하지 못한 항목은 자동 테스트 통과로 대체하지 않고 미검증으로 기록한다.

## Review Focus

- JointState 순서가 바뀌거나 추가 관절이 섞여도 20개 계약 관절을 이름으로 정확히 정렬해야 한다. Task 1과 4의 permutation 테스트가 이를 고정한다.
- arm/gripper 명령에 다리 관절 이름이 들어가거나 한 그룹에 중복 이름이 있으면 물리 상태를 바꾸기 전에 거부해야 한다. Task 3의 음성 테스트가 이를 고정한다.
- Xacro와 MJCF의 관절 축·한계·장착 변환이 달라지면 엔진별 검증 결과를 비교할 수 없다. Task 2의 교차 모델 테스트가 이를 고정한다.
- 시뮬레이션 시각 정지·역행 또는 stale 명령에서 새 명령을 적용하지 않고 마지막 안전 목표를 hold해야 한다. Task 3과 5의 시각 테스트가 이를 고정한다.
- 그리퍼 닫힘 명령만으로 성공 처리하지 않고 접촉, 물체 높이 증가, 상대 위치 유지 시간을 모두 확인해야 한다. Task 4와 6의 물리 테스트가 이를 고정한다.

---

### Task 1: Ch13 Python 패키지와 20관절 계약

**Files:**
- Create: `Ch13/.gitattributes`
- Create: `Ch13/.gitignore`
- Create: `Ch13/pyproject.toml`
- Create: `Ch13/src/ch13_sim_core/__init__.py`
- Create: `Ch13/src/ch13_sim_core/contract.py`
- Create: `Ch13/config/joint_contract.yaml`
- Create: `Ch13/tests/test_contract.py`

**Interfaces:**
- Produces: `JointGroup` dataclass, `RobotContract` dataclass, `load_contract(path: Path) -> RobotContract`, `ordered_values(names, values, expected_names) -> np.ndarray`.
- Contract values: ordered leg, arm, gripper names; lower/upper limits; nominal pose; mount xyz/rpy; 20 unique movable joints.

- [ ] **Step 1: Write failing contract tests**

  Add tests named `test_contract_has_12_leg_6_arm_2_gripper_joints`, `test_contract_rejects_duplicate_joint_names`, `test_ordered_values_is_name_based`, and `test_ordered_values_rejects_missing_duplicate_and_nonfinite_values`. Hand-write the expected 20 names and representative reordered values.

- [ ] **Step 2: Verify RED**

  Run: `python -m pytest Ch13/tests/test_contract.py -q`
  Expected: collection/import failure because `ch13_sim_core.contract` does not exist.

- [ ] **Step 3: Implement the package and contract**

  Implement the exact interfaces above. Use `yaml.safe_load`; validate group disjointness, dimensions, finite values, and lower < upper at load time. Configure package data so `joint_contract.yaml` and future model XML files are installed.

- [ ] **Step 4: Verify GREEN and package install**

  Run: `python -m pytest Ch13/tests/test_contract.py -q`
  Expected: all Task 1 tests pass.

  Run: `python -m pip install -e 'Ch13[test]'`
  Expected: editable install succeeds and `python -c "import ch13_sim_core"` exits 0.

- [ ] **Step 5: Commit**

  ```bash
  git add Ch13/.gitattributes Ch13/.gitignore Ch13/pyproject.toml Ch13/src Ch13/config Ch13/tests/test_contract.py
  git commit -m "feat(ch13): define integrated robot joint contract"
  ```

### Task 2: 동등한 Xacro와 MJCF 결합 모델

**Files:**
- Create: `Ch13/ros2_ws/src/ch13_robot_description/CMakeLists.txt`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/package.xml`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/urdf/common/inertial_macros.xacro`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/urdf/quadruped_base.urdf.xacro`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/urdf/arm_6dof.urdf.xacro`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/urdf/integrated_robot.urdf.xacro`
- Create: `Ch13/src/ch13_sim_core/models/integrated_robot.xml`
- Create: `Ch13/src/ch13_sim_core/model_validation.py`
- Create: `Ch13/tests/test_model_parity.py`

**Interfaces:**
- Consumes: `load_contract()` from Task 1.
- Produces: `load_urdf_joints(xml_text: str) -> dict[str, JointSpec]`, `load_mjcf_joints(path: Path) -> dict[str, JointSpec]`, `validate_model_parity(contract, urdf, mjcf) -> None`.
- Xacro macros: `quadruped_base(parent='')`, `arm_6dof(parent, mount_xyz, mount_rpy)`.

- [ ] **Step 1: Write failing model tests**

  Test unique link/joint names, one URDF root, exact 20 movable joints, finite positive mass/inertia, and literal expected axes/limits for every group. Add a parity test requiring contract, expanded Xacro, and MJCF to agree. Add a regression test that changing `arm_joint_3` axis in an in-memory fixture fails parity.

- [ ] **Step 2: Verify RED**

  Run: `python -m pytest Ch13/tests/test_model_parity.py -q`
  Expected: failure because models and validation functions do not exist.

- [ ] **Step 3: Implement the Xacro model**

  Copy only the required Ch11 dimensions/leg structure and Ch08 Z-Y-Y-X-Y-Z arm concept. Rename all arm/gripper joints, add explicit collision and inertial properties, `arm_mount`, `tool0`, and `grasp_site`. Keep `base_footprint` as the single URDF root below odom.

- [ ] **Step 4: Implement the MJCF model and parity parser**

  Create the same body hierarchy, free base, 20 position actuators, ground, table/fixture and cube. Resolve joint and actuator IDs by name. The parser must compare names, axes, limits and mount transform within `1e-8` for declared values.

- [ ] **Step 5: Verify GREEN**

  Run: `python -m pytest Ch13/tests/test_contract.py Ch13/tests/test_model_parity.py -q`
  Expected: all tests pass.

  Run in ROS Jazzy shell: `xacro Ch13/ros2_ws/src/ch13_robot_description/urdf/integrated_robot.urdf.xacro > /tmp/ch13_integrated.urdf`
  Expected: exit 0; `check_urdf /tmp/ch13_integrated.urdf` reports a valid tree.

- [ ] **Step 6: Commit**

  ```bash
  git add Ch13/ros2_ws/src/ch13_robot_description Ch13/src/ch13_sim_core Ch13/tests/test_model_parity.py
  git commit -m "feat(ch13): add equivalent integrated Xacro and MJCF models"
  ```

### Task 3: 엔진 독립 명령 중재와 단일 소유권

**Files:**
- Create: `Ch13/src/ch13_sim_core/arbiter.py`
- Create: `Ch13/tests/test_arbiter.py`

**Interfaces:**
- Consumes: `RobotContract` from Task 1.
- Produces: `GroupCommand(names: tuple[str, ...], positions: np.ndarray, stamp: float, publisher_id: str)`, `ArbitrationResult(targets: np.ndarray, status: str, stale_groups: tuple[str, ...])`, `CommandArbiter.update(group, command)`, and `CommandArbiter.resolve(now) -> ArbitrationResult`.

- [ ] **Step 1: Write failing arbiter tests**

  Test group name isolation, order permutation, duplicate/missing/nonfinite rejection, limit clipping policy, future/out-of-order timestamps, stale-group hold, full 20-value output, and second publisher conflict. The publisher-conflict test must show that no target changes after conflict detection.

- [ ] **Step 2: Verify RED**

  Run: `python -m pytest Ch13/tests/test_arbiter.py -q`
  Expected: import failure because `arbiter.py` does not exist.

- [ ] **Step 3: Implement minimal arbiter**

  Validate before mutation. Keep one publisher ID per group until explicit `reset_owner(group)`. Resolve missing/stale groups to their last safe target, initialized from contract nominal values. Return targets in the contract's 20-name order.

- [ ] **Step 4: Verify GREEN**

  Run: `python -m pytest Ch13/tests/test_arbiter.py Ch13/tests/test_contract.py -q`
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add Ch13/src/ch13_sim_core/arbiter.py Ch13/tests/test_arbiter.py
  git commit -m "feat(ch13): enforce single-owner actuator commands"
  ```

### Task 4: MuJoCo 실제 물리·파지 코어

**Files:**
- Create: `Ch13/src/ch13_sim_core/mujoco_runtime.py`
- Create: `Ch13/src/ch13_sim_core/grasp_metrics.py`
- Create: `Ch13/scripts/verify_mujoco.py`
- Create: `Ch13/tests/test_mujoco_runtime.py`
- Create: `Ch13/tests/test_grasp_metrics.py`

**Interfaces:**
- Consumes: contract, arbiter and MJCF from Tasks 1-3.
- Produces: `MujocoRuntime.reset(seed)`, `apply_named_targets(names, positions, stamp)`, `step(control_steps)`, `snapshot() -> PhysicsSnapshot`, `close()`; `GraspObservation` and `classify_grasp(sequence, thresholds) -> GraspResult`.

- [ ] **Step 1: Write failing runtime and grasp tests**

  Test 20 actuator name mapping under a permuted actuator fixture, finite state after 2,000 steps at hold, bounded base height/tilt during small arm motion, stale target rejection, and idempotent close. For grasp metrics, require both finger contacts, cube lift >= 0.03 m, tool-cube drift <= 0.025 m, and hold >= 0.5 s; each missing condition gets its own failing fixture.

- [ ] **Step 2: Verify RED**

  Run: `python -m pytest Ch13/tests/test_mujoco_runtime.py Ch13/tests/test_grasp_metrics.py -q`
  Expected: import failure for the new runtime modules.

- [ ] **Step 3: Implement runtime and deterministic fixture sequence**

  Keep MuJoCo arrays private to the runtime and expose copied snapshots. Use `mj_name2id` for every joint, actuator, body, geom and site. Implement a deterministic approach-close-lift sequence with fixed seed; tune only physical mass, friction, damping and trajectory values that are documented in the model.

- [ ] **Step 4: Verify GREEN with actual `mj_step`**

  Run: `MUJOCO_GL=egl python -m pytest Ch13/tests/test_mujoco_runtime.py Ch13/tests/test_grasp_metrics.py -q`
  Expected: all tests pass without skip.

  Run: `MUJOCO_GL=egl python Ch13/scripts/verify_mujoco.py --output Ch13/evidence/mujoco/result.json --image Ch13/evidence/mujoco/frame.png`
  Expected: exit 0 and result `status: PASS` with 20 actuators, finite state, base stability and physical grasp metrics.

- [ ] **Step 5: Commit**

  ```bash
  git add Ch13/src/ch13_sim_core Ch13/scripts/verify_mujoco.py Ch13/tests Ch13/evidence/mujoco
  git commit -m "feat(ch13): verify integrated MuJoCo physics and grasp"
  ```

### Task 5: ROS 2 상태 집계·명령 노드와 공통 launch

**Files:**
- Create: `Ch13/ros2_ws/src/ch13_control/package.xml`
- Create: `Ch13/ros2_ws/src/ch13_control/setup.py`
- Create: `Ch13/ros2_ws/src/ch13_control/setup.cfg`
- Create: `Ch13/ros2_ws/src/ch13_control/resource/ch13_control`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/__init__.py`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/state_monitor.py`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/command_arbiter_node.py`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/hold_controller.py`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/mujoco_bridge.py`
- Create: `Ch13/ros2_ws/src/ch13_control/launch/mobile_manipulation.launch.py`
- Create: `Ch13/ros2_ws/src/ch13_control/test/test_state_monitor.py`
- Create: `Ch13/ros2_ws/src/ch13_control/test/test_command_arbiter_node.py`
- Create: `Ch13/ros2_ws/src/ch13_control/test/test_launch_contract.py`

**Interfaces:**
- Consumes: installed `ch13_sim_core` contract, arbiter and MuJoCo runtime.
- Produces: raw state `/ch13/joint_states_raw`; validated complete state `/joint_states`; group inputs `/ch13/command/{legs,arm,gripper}`; sole full output `/ch13/command/actuators`; diagnostics `/ch13/status/{state,command,simulator}`.
- Launch args: `backend`, `enabled`, `headless`, `world`, `seed`; backend must be exactly `mujoco` or `gazebo`.

- [ ] **Step 1: Write failing ROS-independent callback/core tests**

  Extract message-to-core conversions so tests can call them without a running graph. Test 20-name aggregation, timestamp preservation, duplicate/missing/nonfinite rejection, backend exclusivity, safe default disabled, and launch rejection of an unknown backend.

- [ ] **Step 2: Verify RED**

  Run in ROS Jazzy shell: `python -m pytest Ch13/ros2_ws/src/ch13_control/test -q`
  Expected: failure because the ROS package modules do not exist.

- [ ] **Step 3: Implement ament package and nodes**

  The arbiter node is the only publisher of `/ch13/command/actuators`. The MuJoCo bridge is the only raw joint/clock/odom publisher for that backend. State monitor publishes only complete validated JointState. Hold controller uses separate publisher IDs per group and publishes only when `enabled:=true`.

- [ ] **Step 4: Build and verify GREEN**

  Run in a clean ROS shell: `cd Ch13/ros2_ws && colcon build --symlink-install`
  Expected: both Ch13 ROS packages build; package prefixes resolve inside `Ch13/ros2_ws/install`.

  Run: `python -m pytest Ch13/ros2_ws/src/ch13_control/test -q`
  Expected: all Task 5 tests pass.

- [ ] **Step 5: Run actual MuJoCo ROS launch smoke**

  Run: `ros2 launch ch13_control mobile_manipulation.launch.py backend:=mujoco enabled:=true headless:=true`
  Expected: 20 joint states, one actuator command publisher, advancing `/clock`, stable base and clean Ctrl+C shutdown.

- [ ] **Step 6: Commit**

  ```bash
  git add Ch13/ros2_ws/src/ch13_control
  git commit -m "feat(ch13): add ROS command arbitration and MuJoCo launch"
  ```

### Task 6: Gazebo 모델 제어, router와 실제 엔진 검증

**Files:**
- Modify: `Ch13/ros2_ws/src/ch13_robot_description/urdf/integrated_robot.urdf.xacro`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/urdf/gazebo_control.xacro`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/config/ros_gz_bridge.yaml`
- Create: `Ch13/ros2_ws/src/ch13_robot_description/worlds/mobile_manipulation.sdf`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/gazebo_router.py`
- Modify: `Ch13/ros2_ws/src/ch13_control/launch/mobile_manipulation.launch.py`
- Create: `Ch13/scripts/verify_gazebo.sh`
- Create: `Ch13/scripts/gazebo_probe.py`
- Create: `Ch13/ros2_ws/src/ch13_control/test/test_gazebo_description.py`
- Create: `Ch13/ros2_ws/src/ch13_control/test/test_gazebo_router.py`

**Interfaces:**
- Consumes: `/ch13/command/actuators` and the 20-name contract.
- Produces: exactly one Gazebo Float64 `cmd_pos` publisher per joint; bridged raw joint state, clock, IMU, odometry and world pose needed by the probe.
- Verification result: JSON fields for 20-joint presence, TF uniqueness, publisher counts, command response, base stability, cube lift/contact/hold, shutdown acknowledgement and forced cleanup.

- [ ] **Step 1: Write failing Gazebo description/router tests**

  Test exactly 20 position-controller plugins, exact joint names, finite gains/force limits/initial positions, router name mapping under permutation, no publisher for unknown joints, and unique simulator command topic ownership.

- [ ] **Step 2: Verify RED**

  Run in ROS Jazzy shell: `python -m pytest Ch13/ros2_ws/src/ch13_control/test/test_gazebo_description.py Ch13/ros2_ws/src/ch13_control/test/test_gazebo_router.py -q`
  Expected: failures because Gazebo control and router are absent.

- [ ] **Step 3: Implement Gazebo resources and router**

  Add one position controller per movable joint and only the sensor/odometry systems required by 13.1. Bridge observation topics GZ_TO_ROS; never bridge command topics bidirectionally. Spawn the robot once as `ch13_mobile_manipulator` and the fixture cube once in the world.

- [ ] **Step 4: Verify unit GREEN and clean build**

  Run: `cd Ch13/ros2_ws && rm -rf build install log && colcon build --symlink-install`
  Expected: clean build succeeds using only the ROS installation and Ch13 workspace.

  Run: `python -m pytest Ch13/ros2_ws/src/ch13_control/test -q`
  Expected: all ROS package tests pass.

- [ ] **Step 5: Run actual Gazebo verification**

  Run: `bash Ch13/scripts/verify_gazebo.sh`
  Expected: actual Gazebo server starts, all state/TF/command checks pass, and `Ch13/evidence/gazebo/result.json` records `status: PASS`. Physical grasp must be separately reported as PASS/FAIL/UNVERIFIED; the wrapper exits nonzero if a required 13.1 check fails.

- [ ] **Step 6: Commit**

  ```bash
  git add Ch13/ros2_ws Ch13/scripts/verify_gazebo.sh Ch13/scripts/gazebo_probe.py Ch13/evidence/gazebo
  git commit -m "feat(ch13): integrate and verify Gazebo mobile manipulator"
  ```

### Task 7: 선택적 Ch12.8 다리 정책 어댑터와 회귀

**Files:**
- Create: `Ch13/src/ch13_sim_core/locomotion_contract.py`
- Create: `Ch13/ros2_ws/src/ch13_control/ch13_control/rl_leg_controller.py`
- Modify: `Ch13/ros2_ws/src/ch13_control/launch/mobile_manipulation.launch.py`
- Create: `Ch13/tests/test_locomotion_contract.py`
- Create: `Ch13/ros2_ws/src/ch13_control/test/test_rl_leg_controller.py`

**Interfaces:**
- Consumes: Ch13 full JointState and a Ch12-compatible locomotion bundle supplied by path.
- Produces: only the 12 names on `/ch13/command/legs`; never publishes arm, gripper or full actuator commands.
- Contract: 48-D locomotion observation, `[0, -0.5, 1] × 4` nominal pose, `0.35 rad` action scale, 50 Hz simulation time, 20 ms inference budget.

- [ ] **Step 1: Write failing isolation tests**

  Test that extra arm/gripper JointState entries are ignored by name, missing leg names fail, goal/avoidance bundle manifests fail, controller output has exactly 12 leg names, and disabled mode publishes no motion command.

- [ ] **Step 2: Verify RED**

  Run: `python -m pytest Ch13/tests/test_locomotion_contract.py Ch13/ros2_ws/src/ch13_control/test/test_rl_leg_controller.py -q`
  Expected: new modules missing.

- [ ] **Step 3: Implement the minimum adapter**

  Copy the required logic from Ch12 `ros_core.py` and `rl_controller.py` into Ch13 namespaces with recorded provenance. Remove all Ch11/Ch12 package/path assumptions. Keep model loading optional so the default package remains usable without PyTorch.

- [ ] **Step 4: Verify GREEN and run smoke bundle if available**

  Run: `python -m pytest Ch13/tests/test_locomotion_contract.py Ch13/ros2_ws/src/ch13_control/test/test_rl_leg_controller.py -q`
  Expected: tests pass.

  Run with an explicitly supplied compatible smoke bundle: `ros2 launch ch13_control mobile_manipulation.launch.py backend:=mujoco leg_controller:=ppo bundle_path:=... enabled:=true`
  Expected: connection and safety checks pass. Report this as integration smoke only, never as learned walking success.

- [ ] **Step 5: Commit**

  ```bash
  git add Ch13/src/ch13_sim_core Ch13/ros2_ws/src/ch13_control Ch13/tests
  git commit -m "feat(ch13): isolate optional locomotion policy adapter"
  ```

### Task 8: 실습 문서, 재사용 명세, 최종 증거와 보고서

**Files:**
- Create: `Ch13/README.md`
- Create: `Ch13/docs/LAB_13_1_GUIDE_KO.md`
- Create: `Ch13/docs/REUSE_MANIFEST.md`
- Create: `Ch13/docs/CHANGE_REPORT_KO.md`
- Create: `Ch13/scripts/verify_all.py`
- Create/Update: `Ch13/evidence/**`

**Interfaces:**
- Consumes: all prior tasks and their commands/results.
- Produces: one student-facing start path, exact dependency/build/run steps, source provenance, review findings, limitations, and `verification_summary.json` whose status is derived from fresh result files.

- [ ] **Step 1: Implement the verification orchestrator**

  `verify_all.py` runs pure Python/engine tests and validates evidence schemas without marking unavailable external engines PASS. It records commit SHA, dirty paths, versions, commands and timestamps.

- [ ] **Step 2: Write the Korean lab guide**

  Cover clean setup, Python install, isolated colcon build, MuJoCo run, Gazebo run, expected topics/TF/joints, command ownership inspection, fixture grasp, shutdown and common failures. Separate verified current behavior from MoveIt/ros2_control/PPO proposals.

- [ ] **Step 3: Write the reuse manifest**

  For every copied or adapted file/idea record source commit, original path, new path, license, SHA-256 and modification summary. Confirm no draft/error/latest/ok/gem backup file entered an execution path.

- [ ] **Step 4: Run fresh full verification**

  Run on Windows or the Python environment: `python -m pytest Ch13/tests -q`
  Expected: zero failures and zero unexpected skips.

  Run in a clean ROS Jazzy shell: `cd Ch13/ros2_ws && rm -rf build install log && colcon build --symlink-install && colcon test --event-handlers console_direct+ && colcon test-result --verbose`
  Expected: build/test exit 0; package prefixes point inside Ch13.

  Run: `MUJOCO_GL=egl python Ch13/scripts/verify_mujoco.py ...`
  Expected: fresh MuJoCo PASS result.

  Run: `bash Ch13/scripts/verify_gazebo.sh`
  Expected: fresh Gazebo result, with any unverified physical-grasp subcheck explicitly represented.

- [ ] **Step 5: Confirm scope and repository cleanliness**

  Run: `git diff 1451f54 -- Ch05 Ch06 Ch07 Ch08 Ch09 Ch10 Ch11 Ch12`
  Expected: no output.

  Run: `git diff --check && git status --short`
  Expected: no whitespace errors; only intended Ch13 evidence/report changes before final commit.

- [ ] **Step 6: Write the change/review report from evidence**

  Record exact versions, test counts, engine run metrics, failures fixed, final SHA, unverified items and short-policy limitations. Do not copy expected results from this plan into the report without matching fresh evidence.

- [ ] **Step 7: Final commit**

  ```bash
  git add Ch13
  git commit -m "docs(ch13): add section 13.1 lab and verification report"
  ```

- [ ] **Step 8: Verify commit and optional push**

  Run all relevant verification commands again after the final commit, then record `git rev-parse HEAD` and `git status --short`. Push `feat/ch13-section-13-1` only after confirming the remote has not advanced unexpectedly; verify the remote SHA with `git ls-remote origin refs/heads/feat/ch13-section-13-1`.
