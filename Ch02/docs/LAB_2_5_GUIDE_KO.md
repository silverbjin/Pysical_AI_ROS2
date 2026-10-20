# LAB 2.5 — 메시지·서비스·액션 인터페이스 생성하기

## 이 절에서 할 일
원고 2.5.1~2.5.6에 따라 `HardwareStatus.msg`와 `ComputeRectangleArea.srv`를 분석하고 `hw_status_publisher`를 실행한다. **GitHub Ch02 소스에는 2.6의 `CountUntil.action`까지 미리 포함**되어 있으므로 action 파일과 의존성도 함께 빌드한다.

## 사전조건
Ubuntu 24.04 + ROS 2 Jazzy; 기존 clone에 있는 `Ch02/ros2_ws`를 사용한다. `ros2 pkg create`와 `mkdir msg srv action`으로 **이미 있는 디렉터리를 중복 생성하지 않는다**.

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon list
colcon build --symlink-install --packages-up-to my_robot_system
source install/setup.bash
```

## 실습 A — 데이터 계약 읽기
```bash
cat src/my_robot_interfaces/msg/HardwareStatus.msg
cat src/my_robot_interfaces/srv/ComputeRectangleArea.srv
cat src/my_robot_interfaces/action/CountUntil.action
ros2 interface show my_robot_interfaces/msg/HardwareStatus
ros2 interface show my_robot_interfaces/srv/ComputeRectangleArea
ros2 interface show my_robot_interfaces/action/CountUntil
```
.msg: 한 벌의 필드, .srv: `요청 --- 응답`, .action: `Goal --- Result --- Feedback`. 실제 정의는 `HardwareStatus`의 ID·온도 경고·메시지 세 필드다. 도입부의 다중 온도/전압/오류코드는 이번 샘플에 구현되어 있지 않다.

## 실습 B — 생성된 Python 타입 확인
```bash
python3 - <<'PY'
from my_robot_interfaces.msg import HardwareStatus
from my_robot_interfaces.srv import ComputeRectangleArea
from my_robot_interfaces.action import CountUntil
m = HardwareStatus(machine_id=101, temperature_warning=False, debug_message="OK")
req = ComputeRectangleArea.Request(length=2.0, width=3.0)
goal = CountUntil.Goal(target_number=5, period=0.5)
print(m, req, goal)
assert m.machine_id == 101 and req.length == 2.0 and goal.target_number == 5
PY
```
이 단계는 **인터페이스 생성/임포트**만 검사한다. 계산 서비스 서버는 현재 코드에 없으므로 `ros2 service call /compute_rectangle_area`는 성공할 수 없다. 이를 실패로 오해하지 않는다.

## 실습 C — Custom msg 발행
터미널 1:
```bash
ros2 run my_robot_system hw_status_publisher
```
터미널 2 (동일 source):
```bash
ros2 topic info -v /hardware_status
ros2 topic echo /hardware_status
```
예상 필드: `machine_id: 101`, `temperature_warning: false`, `debug_message: All Systems Nominal`. 수 초 관찰 후 Ctrl+C.

## 원리·실패 복구
- `rosidl_generate_interfaces`는 인터페이스를 각 언어 타입으로 생성하고 `ament_cmake`와 `rosidl_default_generators`가 필요하다.
- `package.xml`에는 `rosidl_default_runtime`, `rosidl_interface_packages`, 이 저장소에 필요한 **`action_msgs`**가 포함되어야 한다.
- `ModuleNotFoundError: my_robot_interfaces`: 설치 워크스페이스 `source install/setup.bash` 누락, 잘못된 Python 환경, 생성 실패, 다른 장 오버레이 점검.
- 변경 후에는 다시 colcon 빌드 및 source. `ros2 pkg prefix my_robot_interfaces`가 Ch02를 가리키는지 확인.

## PASS 및 산출물
세 타입 `interface show`, Python 객체 3개 생성, 실제 토픽 필드 3개 수신을 기록한다. 실패 케이스를 원인과 함께 제출한다. [리뷰 보고서](SECTION_2_5_REPORT_KO.md).
