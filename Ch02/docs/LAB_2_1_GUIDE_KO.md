# LAB 2.1 — 첫 클래스 기반 ROS 2 노드 실습

## 학습 목표
`rclpy.node.Node` 상속, 상태 변수, `create_timer(1.0, callback)`, `spin()`, `destroy_node()`를 연결한다. **로그 출력**과 **토픽 발행**은 다르다는 점을 구분한다.

## 환경과 경로
Ubuntu 24.04 + ROS 2 Jazzy(또는 대응되는 배포판). 저장소 clone 후 다음 워크스페이스가 기준이다. 원고의 `~/ros2_ws`는 예시이며 이 저장소에는 **`Ch02/ros2_ws`**가 있다.

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git
cd Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
ros2 --help >/dev/null
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_robot_system
```

기존 저장소가 있다면 clone을 반복하지 말고 해당 경로로 이동한다. Ubuntu 22.04/Humble 사용 시 `jazzy` 대신 `humble`을 사용한다. 다른 장의 `install/setup.bash`와 중복 source하지 않는다.

## 따라 하기

**실습 A — 실행과 로그**
```bash
ros2 run my_robot_system joint_sensor
```
예상: 최초 시작 로그 후 약 1초마다 `Joint Angle: ... rad, Battery: ...%`. 각도는 난수여서 교재 예시 수치와 일치할 필요가 없다. 배터리는 0 아래로 떨어지지 않는다. Ctrl+C 종료.

**실습 B — 노드 그래프 관찰** (실습 A 실행 중 다른 터미널)
```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2/Ch02/ros2_ws/install/setup.bash
ros2 node list
ros2 node info /joint_sensor
```
`/joint_sensor`가 보이며 사용자 정의 토픽 publisher는 없다. 콘솔 로그만 출력하는 노드임을 설명하라.

**실습 C — 상태 변경과 실행 주기**
`joint_sensor_node.py`의 타이머 주기를 1.0→0.2초로 변경하고 `colcon build --symlink-install` 후 다시 실행한다. 약 5Hz라는 **관찰값**과 타이머 설정값을 구분한다. 실습 후 1.0초로 되돌리고 `git diff`를 확인한다.

## 점검 질문·합격 기준
1. `JointSensorNode(Node)`의 상속이 제공하는 기능을 설명한다.
2. `self.joint_angle`와 지역 변수 `noise`의 생존 범위를 구별한다.
3. 타이머와 `rclpy.spin()`이 콜백을 실행하는 관계를 설명한다.
4. 3회 이상 로그 발생, 노드 이름 확인, Ctrl+C 정상 종료를 기록한다.

## 문제 해결
- `Package 'my_robot_system' not found`: 작업 위치와 `source install/setup.bash`, `ros2 pkg prefix` 확인.
- `No module named rclpy`: 시스템 Python/ROS 환경 source 확인; 임의 venv와 ROS Python 혼용 금지.
- 다른 절의 `my_robot_system`이 실행됨: `ros2 pkg prefix my_robot_system`의 실제 설치 경로를 확인.
- WSL에서는 이 절에 그래픽 디스플레이가 필요하지 않다.

## 정리
로그 3줄, `ros2 node info` 출력, 주기 변경 관찰을 Evidence로 남긴다. 본 실습은 가상 센서 상태 변화일 뿐 물리적 센서·관절 제한 검증은 아니다. 리뷰: [SECTION_2_1_REPORT_KO.md](SECTION_2_1_REPORT_KO.md).
