# 4.6절 코드 수정·정적 테스트 보고서 (2026-10-21 KST)

- 브랜치: `feat/ch04-section-4-6`; 코드 변경 SHA: `9647edad885756978d01ad833f2071316d179912`
- 원본 리뷰: [SECTION_4_6_REPORT_KO.md](SECTION_4_6_REPORT_KO.md)
- 판정: **STATIC_CONTRACT_PASS 9/9; Gazebo/ROS runtime NOT_RUN; FULL_BASE_POSE BLOCKED**

## 수정 범위 및 조치

원고의 존재하지 않는 `my_robot.urdf.xacro` 경로 대신 Ch03의 `two_dof_arm.urdf.xacro`를 명시적으로 로드하는 **Ch04 독립 launch** `launch/sim_sync_ch04.launch.py`를 추가했다. Gazebo world는 `empty.sdf`, model은 `my_robot`, Gazebo joint state 경로는 `/world/empty/model/my_robot/joint_state`이며 `gz.msgs.Model → sensor_msgs/msg/JointState` 브리지와 ROS `/joint_states` remap을 구성한다. `/clock`은 Gazebo→ROS 방향이며 RSP/RViz `use_sim_time`을 적용한다. `joint_state_publisher_gui`는 함께 실행하지 않는다.

`rviz/sim_sync_ch04.rviz`는 `base_link` Fixed Frame·Transient Local robot_description을 갖는다. `test_section_4_6_sync.py`에 3개 정적 계약 테스트를 작성했다.

## Push 후 실소스 정적 검사

| 항목 | 결과 |
|---|---|
| model exists and plugin | PASS |
| empty world name | PASS |
| model joint state type | PASS |
| ROS remap | PASS |
| GZ→ROS sim clock | PASS |
| RSP + RViz sim time | PASS |
| one real publisher | PASS |
| RViz fixed/description QoS | PASS |
| test file | PASS |

원격 저장된 launch·RViz·참조 Xacro 텍스트를 재조회해 계약을 검사했다. Gazebo plugin 로드·joint state 변환 실제 성공은 아직 검증하지 않았다.

## 재현 및 정적 테스트 명령

```bash
cd Ch04/ros2_ws/src/my_robot_tf
PYTHONPATH="$PWD" python3 -m unittest discover -s test -p 'test_section_4_6_sync.py' -v
python3 -m py_compile launch/sim_sync_ch04.launch.py
# Ch03를 먼저 build/source한 뒤 Ch04 build/source
ros2 launch my_robot_tf sim_sync_ch04.launch.py
gz topic -l | grep joint_state
ros2 topic echo --once /clock
ros2 topic echo --once /joint_states
ros2 run tf2_ros tf2_echo base_link link2
```

## 미달·안전 범위

| 확인 단계 | 상태 |
|---|---|
| 원격 정적 구조 | **PASS 9/9** |
| unittest / py_compile / colcon | **NOT_RUN** |
| Gazebo spawn / ros_gz_bridge / RViz | **NOT_RUN** |
| Gazebo 자유 몸체의 월드 포즈 TF | **BLOCKED (미구현)** |

**중요:** `/joint_states`는 URDF 관절의 회전 상태를 담지만, 자유롭게 움직이는 base의 `world→base_link`를 자동으로 제공하지 않는다. 그러므로 로봇 몸체가 넘어지는 전체 자세 동기화를 성공했다고 서술할 수 없다. 해당 기능에는 별도 월드 포즈/odom 또는 TF 브로드캐스터 설계, 단일 소유자 정책, 시뮬레이션 시간 일치 검증이 필요하다.
