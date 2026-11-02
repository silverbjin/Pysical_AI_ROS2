# SECTION 3.7 — 로봇 스폰·통합 Launch 코드 리뷰

- 원고: 3.7.1~3.7.4 (URDF 파일/토픽 기반 소환, robot_state_publisher, 통합 런치)
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20 KST
- 대상: `launch/spawn_robot.launch.py`, `urdf/two_dof_arm.urdf.xacro`, `worlds/my_world.sdf`
- **결론**: 정적 설정 개선 완료. Gazebo 실제 실행·로봇 생성·TF 검증은 `NOT RUN`.

## 발견·조치
| ID | 심각도 | 발견 | 처리 |
|---|---|---|---|
| 3.7-01 | Medium | 브리지를 `arguments=['--ros-args', '-p', 'config_file:=...']`에 직접 주입 | `Node(parameters=[{'config_file': bridge_config}])`로 명확히 표현 |
| 3.7-02 | Low | `gz_args`를 리스트/치환 요소로 전달 | `f'-r {world_file}'`로 단일 문자열 전달, 명령어 점검 쉽게 함 |
| 3.7-03 | Medium | 원고에 `gz sim empty.sdf`와 본 저장소 `my_first_world`를 혼용 | 본 통합 런치는 `worlds/my_world.sdf`, 월드 이름은 **my_first_world** |
| 3.7-04 | Medium | 원고는 `-topic` 스폰을 표준 사례라 설명하지만 RSP가 정상적으로 `robot_description`을 제공해야만 성공 | RSP/토픽 존재 및 Gazebo create 응답을 각각 확인 |
| 3.7-05 | High(선행) | 실제 로봇의 제어/JointState는 Xacro 플러그인과 브리지 설정에 의존 | 3.3 + 3.6 + 3.8 수정 병합/검증 후 동작 PASS 판정 |

## 데이터 흐름
`xacro` → `robot_description`(`robot_state_publisher`) → `ros_gz_sim create -topic` → Gazebo entity `my_robot`. Gazebo `/clock` → `ros_gz_bridge` → ROS 노드들(`use_sim_time`). ROS 노드는 기본적으로 시뮬레이션 시간을 따르도록 런치 파라미터 설정됨.

## 검증 상태
- **PASS(소스 정적)**: Xacro 경로, Gazebo 월드 파일 경로, RSP의 `ParameterValue(..., str)`, 스폰 모델명과 YAML 매핑 명칭 대응 확인.
- **NOT RUN**: `ros2 launch`, 실제 spawn 응답, `gz model`, `/robot_description`/TF 토픽 수신, 렌더링/중력 동역학. GUI·ROS 런타임 부재.
- 정적 리뷰로 ROS 2 Jazzy/Harmonic 버전별 실행 성공을 보장할 수 없다.

## 독자 현장 검증
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description spawn_robot.launch.py
# 두 번째 터미널:
ros2 topic echo /robot_description --once | head -30
ros2 topic echo /clock --once
gz topic -l | grep -E '/world/my_first_world|/model/my_robot'
```
로봇을 보지 못하면 **URDF 파서 → RSP → Gazebo world 생성 → create 서비스 응답 → GUI 카메라** 순으로 진단한다. `-z 0.1`은 지면 초기 충돌 회피 목적이지 물리 베이스 고정이 아님. `world`에 고정 조인트가 없는 상태에서 로봇 팔이 반드시 서 있다고 약속해서는 안 된다.

## PR·Acceptance
본 브랜치는 스폰 론치만 수정. ROS 런타임 의존성 정리는 3.2, Clock/TF는 3.6, 관성/EE는 3.3에서 별도 수정되므로 병합 후 통합 테스트 필수. 최종 `PENDING_RUNTIME_VERIFICATION`.
