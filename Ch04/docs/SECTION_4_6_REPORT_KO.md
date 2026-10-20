# 4.6절 코드 리뷰: Gazebo–RViz 상태 동기화

- 기준: `main@7b7c10f` / 2026-10-20 KST / `feat/ch04-section-4-6`
- 검토 파일: 원고 4.6; Ch03의 `launch/sim_sync.launch.py`, `urdf/two_dof_arm.urdf.xacro`, `config/ros_gz_bridge.yaml`, `rviz/display.rviz`; Ch04 전체
- 결론: **PARTIAL / CH04 STANDALONE BLOCKED**. 구현은 Ch03에 존재하지만 4.6 원고 경로·공통 토픽과 상충하며 '넘어짐까지 RViz 동기화' 검증 계약은 현재 코드만으로 만족 불가.
- 검증 제한: GitHub 실제 소스 정적 점검과 Gazebo 공식 계약 문서 대조. Gazebo·Rviz 물리 실행 **NOT RUN**.

## 1. 실제 구현과 데이터 경로

Ch03의 `sim_sync.launch.py`는 `two_dof_arm.urdf.xacro`를 xacro 확장한 뒤 RSP에 전달하고, Gazebo `empty.sdf`를 실행해 `my_robot`을 spawn한다. `ros_gz_bridge`를 통해 `/clock`, `/world/empty/model/my_robot/joint_state`(Gazebo `gz.msgs.Model` → ROS `sensor_msgs/msg/JointState`)를 브리지하고 ROS 쪽 `/joint_states`로 remap한다. RSP는 관절 TF를 계산하고 RViz는 이를 표시한다.

Ch03의 별도 `ros_gz_bridge.yaml`은 `/world/my_first_world/model/my_robot/joint_state`를 사용한다. **서로 다른 world의 별도 launch 예제**이므로 동일 실행에서 yaml을 그대로 혼합하면 토픽 연결이 없을 수 있다.

## 2. 심각한 이슈

| ID | 등급 | 근거 | 해결 방향 |
|---|---|---|---|
| 4.6-R1 | High | 원고의 `my_robot.urdf.xacro`은 Ch03 실제 파일 목록에 없음 | 원고·경로를 `two_dof_arm.urdf.xacro`와 일치시키고 Ch04 독립 패키지 구성 여부 결정. |
| 4.6-R2 | High | 원고의 `/joint_states` Gazebo 토픽 vs Ch03 launch의 `/world/empty/model/my_robot/joint_state` | **실제 `gz topic -l` 결과 기준**으로 정확한 Gazebo 토픽·메시지 타입 확인; YAML의 별도 world와 혼동 금지. |
| 4.6-R3 | **Critical(교육 목표)** | `JointState`에는 관절값은 있어도 자유 부유 base의 world pose가 없음 | Gazebo에서 Apply Force로 로봇 몸체 전체가 넘어져도 `world→base_link`가 따라간다는 보장 없음. 월드 포즈 소스(`odom`/Pose/TF)를 추가하고 TF 트리 연결해야 '전체 자세 디지털 트윈' 충족. |
| 4.6-R4 | Medium | `sim_sync.launch.py`의 gazebo/RSP/spawn/bridge 순서가 선언 순서만으로 동기 준비 완료를 의미하지 않음 | spawn 성공 이벤트·노드 준비·토픽 활성화·부하 시 race를 실제 검사. |
| 4.6-R5 | Medium | `use_sim_time`은 RSP와 RViz에 true지만 나머지 사용자 노드의 시계 정책은 불명확 | 모든 관련 state consumer의 시간원 및 `/clock` 수신 여부 점검. |
| 4.6-R6 | Medium | 원고 코드만 사용하면 RobotModel만 보고 '전부 동기화'로 오인 가능 | **관절 상태 동기화**와 **월드 base pose 동기화**를 별도 Acceptance로 구분. |

`gz.msgs.Model → sensor_msgs/msg/JointState` 변환 자체는 Gazebo 공식 예제에 존재하므로 메시지 타입만 보고 오류라고 단정하지 않는다. 실제 연결 실패는 토픽명·world명·모델명과 프로세스 로그를 함께 확인한다.

## 3. 검증 계약

### A. 현재 코드로 목표할 수 있는 부분
- `/clock` ROS topic 수신·RSP `use_sim_time=true`.
- Gazebo joint state 발행, ros_gz_bridge /joint_states 전달, RSP의 관절 TF 생성.
- RViz의 관절 링크 움직임(관절에 실제 변화가 생겼을 때).

### B. 현재 코드만으로 보장할 수 없는 부분
- 로봇 몸체의 world position/orientation을 RViz가 그대로 따라감.
- Apply Force/Torque로 넘어뜨린 로봇의 기울기·전역 위치가 재현됨.
- 실시간 지연 상한과 Gazebo 물리 안정성.

## 4. 점검 및 변경 결과

- **확인:** Ch04에 sim launch가 없고, Ch03의 실제 bridge·plugin 연결 경로가 존재함.
- **미실시:** colcon, Gazebo Harmonic 실기동, `gz topic`, `ros2 topic echo`, RViz, 외력 테스트. **NOT RUN**.
- **소스 변경:** 없음. 결함·수정 우선순위만 기술한다.

참고: [Gazebo Harmonic ROS 2 Interoperability](https://gazebosim.org/docs/harmonic/ros2_interop/) · [Gazebo ROS 2 Integration](https://gazebosim.org/docs/harmonic/ros2_integration/) · [실습](LAB_4_6_GUIDE_KO.md).
