# 12.7~12.8 독립 코드 리뷰

검토일: 2026-10-17. 구현 담당자와 별도로 소스를 읽고 아래 범위의 테스트를 실행했다. 소스 수정이나 커밋은 수행하지 않았다.

## 결론

검토 범위에서 미해결 수정 필요 결함을 발견하지 못했다. 기존 다섯 지적의 수정과 회귀 검증을 확인했고, 최종 Gazebo·MuJoCo ROS 폐루프 실행의 PASS 결과와 정상 종료 로그도 확인했다. 이 판정은 코드 및 명시된 테스트 범위에 해당하며, 장시간 보행 성능이나 실제 하드웨어 적합성을 입증하지 않는다.

| 기존 지적 | 확인한 수정 및 회귀 |
| --- | --- |
| P1: `mj_setConst`가 실제 초기 상태의 qpos를 덮어씀 | 별도 `MjData`를 임시 계산에 사용한다. locomotion/goal/avoidance의 qpos·qvel·ctrl·mocap·관측 보존 회귀를 확인했다. |
| P2: 동일한 이름의 제어기가 중복 publisher 검사를 통과함 | 명령 토픽의 publisher endpoint 수가 1보다 크면 차단한다. 실제 DDS에서 동일 이름 제어기 두 개를 사용한 회귀가 통과했다. |
| P2: arming 직후 실제로 전송하지 않은 nominal을 이전 행동으로 기록함 | 미전송 nominal 동기화를 제거했다. 전송한 ramp target과 이전 행동 이력이 일치하는 회귀가 통과했다. |
| P2: 같은 센서 토픽의 역순 메시지가 최신 값을 덮어씀 | 토픽별 timestamp 역행을 상태 변경 전에 거부한다. 명시적 시계 초기화를 위한 `reset_timing`과 역순 세 종류 회귀를 확인했다. |
| P2: MuJoCo bridge가 오래되거나 역순인 목표 시각을 무시함 | target timeout, 허용 미래 범위, 마지막 수신 timestamp를 검사한 뒤 목표를 원자적으로 수락한다. 거부 시 기존 목표 보존 회귀가 통과했다. |

## 독립 실행 결과

환경: Ubuntu 24.04 WSL, `/tmp/ch12-ros-venv`, ROS Jazzy, NumPy 1.26.4. `Ch12/scripts/ros_env.sh`를 적용하고 다른 통합 실행과 분리한 `ROS_DOMAIN_ID=193`을 사용했다. Gazebo 시뮬레이터는 리뷰 과정에서 별도로 실행하지 않았다.

```bash
CH12_TEST_RENDER=1 MUJOCO_GL=egl ROS_DOMAIN_ID=193 python -m pytest \
  Ch12/tests/test_ros_core.py Ch12/tests/test_robust_env.py \
  Ch12/ros2_ws/src/quadruped_rl_ros/test -q
```

결과: **37 passed in 15.21s**. 원본 로그: `reviewer_tests.log`.

## 최종 Gazebo 초기 목표 변경

`gazebo_description.py`의 `initial_position`은 각 다리 hip=0, thigh=-0.5, calf=1.0 rad이며 MuJoCo 환경의 `nominal_joint_positions`와 같다. 기존 관절 축·원점·관절 제한에 대한 테스트와 함께 12개 위치 제어기 모두의 초기 목표를 확인했다. Ch11 원본 파일은 변경하지 않고 생성한 모델 설명만 수정한다. 이 변경에서 추가 결함을 발견하지 못했다.

Gazebo Sim 8의 `JointPositionController`가 지원하는 설정임을 [공식 API 문서](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1JointPositionController.html)에서도 확인했다. 초기 목표 설정만으로 전체 시작 과도응답이 검증되는 것은 아니므로 실제 통합 재실행 결과를 별도로 판정해야 한다.

```bash
ROS_DOMAIN_ID=193 python -m pytest \
  Ch12/ros2_ws/src/quadruped_rl_ros/test/test_gazebo_description.py -q
```

변경 후 독립 결과: **1 passed in 4.27s**. 원본 로그: `reviewer_initial_position.log`.

## 통합 증거 확인 범위

리뷰 문서 작성 시 확인한 `mujoco/result.json`은 전체 PASS, 활성 관측 401개, 시뮬레이션 시간 기준 50 Hz, 48차원 관측, 명령 timeout 및 pause watchdog 통과, 강제 정리 없음, 정상 종료였다. 이는 구현 담당자의 실제 실행 증거를 읽어 확인한 것으로 위 독립 테스트 실행과 구분한다.

최종 재실행 완료 후 `gazebo/result.json`, `gazebo/launch.log`, `gazebo/server_stop.log`를 추가 확인했다. 전체 PASS이며 활성 관측 334개, 시뮬레이션 시간 기준 50 Hz, 실제 시간 기준 약 41.747 Hz, 최소 높이 0.3757967 m, 48차원 관측, 명령 timeout 통과였다. Gazebo stop 응답은 `data: true`, launch exit는 0이며 강제 정리 없이 모든 프로세스가 정상 종료했다. pause watchdog은 Gazebo에서 실행하지 않았고 MuJoCo에서 확인했다. Gazebo 로그에 KDL root inertia 경고는 남지만 traceback이나 프로세스 비정상 종료는 없었다.

따라서 두 시뮬레이터 모두 실제 ROS 관측→PPO 추론→위치 목표→물리 상태의 짧은 폐루프 통합과 정상 종료가 확인되었다. 실제 시간 기준 50 Hz 달성을 Gazebo 결과로 주장하지 않는다. 최종 통합 실행은 구현 담당자가 수행했으며 독립 리뷰에서는 저장된 결과 및 로그를 확인했다.

이전 시작 높이 문제와 NumPy ABI/체크포인트 실패 증거는 최종 성공 증거와 구분한다. 상위 `gazebo.log`에는 이전 최소 높이 0.1209343 m 실패의 traceback이 남아 있으므로 최종 실행 로그로 해석하면 안 된다. 최종 판정 근거는 위 `gazebo/` 하위의 결과와 로그다.
