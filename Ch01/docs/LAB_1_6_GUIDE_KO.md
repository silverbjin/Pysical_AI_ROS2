# LAB 1.6 — SimpleController: 첫 ROS 2 노드 실습

**원고 정합성:** 1.6.1~1.6.4의 `my_robot_controller/simple_controller.py`가 주 실습이다. 환경은 Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12. ROS 2 런타임 검증은 현재 **NOT_RUN**이다.

## STEP 1. 독립 패키지 빌드

```bash
# 이미 clone한 경우 git clone은 건너뜀
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git ~/Pysical_AI_ROS2
cd ~/Pysical_AI_ROS2
git fetch origin
git switch --track origin/feat/ch01-section-1-6
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ch01_lab_16/src
cp -a ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller ~/ch01_lab_16/src/
cd ~/ch01_lab_16
python3 -m compileall -q src/my_robot_controller
colcon list --names-only
colcon build --symlink-install --packages-select my_robot_controller
source install/setup.bash
ros2 pkg prefix my_robot_controller
ros2 pkg executables my_robot_controller
```

이미 로컬 branch가 있으면 `git switch feat/ch01-section-1-6`. 출력에 `my_robot_controller test_node`가 등록되어야 한다. 원고 1.5절의 최초 생성 패키지에서 `simple_controller`를 실행하던 것과 구분한다.

## STEP 2. 타이머/로거 실행

터미널 A:
```bash
ros2 run my_robot_controller test_node
```

예상:
```text
[INFO] [...] [my_robot_node]: Simple Controller 노드가 시작되었습니다!
[INFO] [...] [my_robot_node]: 로봇 생존 신호 송신 중... (Heartbeat: 1)
[INFO] [...] [my_robot_node]: 로봇 생존 신호 송신 중... (Heartbeat: 2)
[INFO] [...] [my_robot_node]: 로봇 생존 신호 송신 중... (Heartbeat: 3)
```

실제 소스는 `Heartbeat` 문구다. 원고 1.6.1에 적힌 `Count`는 정확한 출력 문자열이 아니다.

터미널 B:
```bash
source /opt/ros/jazzy/setup.bash
source ~/ch01_lab_16/install/setup.bash
ros2 node list
ros2 node info /my_robot_node
```

**기대:** `/my_robot_node` 검색. 실행파일 이름 `test_node`와 ROS 그래프 노드 이름 `my_robot_node`는 다르다. `Heartbeat`는 **로그**이며 ROS Topic Publisher가 아니다.

## STEP 3. OOP·이벤트 처리 관찰

`simple_controller.py`를 열고 아래 항목을 줄 단위로 찾는다:
1. `class SimpleController(Node)` — 기본 ROS Node를 상속
2. `super().__init__('my_robot_node')` — 그래프 이름 설정
3. `create_timer(1.0, self.timer_callback)` — 1초 주기 callback 등록
4. `rclpy.spin(node)` — executor 콜백 dispatch
5. `destroy_node()`, `rclpy.shutdown()` — 종료 시 리소스 정리

타이머를 0.5초로 변경하고 **실습용 복사본**에서 노드를 재시작하여 출력이 2Hz에 근접하는지 확인한다(원본 Git 브랜치는 변경하지 않음). Python 코드 변경은 `--symlink-install`로 적용할 수 있지만 실행 중 노드는 다시 시작해야 한다.

## STEP 4. 종료 및 오류 진단

터미널 A에서 Ctrl+C 후 `ros2 node list`에서 `/my_robot_node`가 사라지는지 확인한다. stack trace/exit code 기록. `No executable found`면 `setup.py`의 `test_node`와 `setup.cfg`의 `lib/my_robot_controller`, overlay source를 점검한다. `rclpy` import 오류는 Conda/파이썬 버전 혼용을 의심한다.

## STEP 5. 선택 응용 (본문 외 보조 코드)

`Ch01/ref/my_first_package/simple_node.py`는 파일 주석에 1.6이라고 쓰였지만 **원고의 주교재 노드는 아니다**. `Ch01/robot_ws/src/robot_monitor`는 모의 배터리 상태를 로그로 출력하는 보조 프로그램이다. 필요 시 별도 워크스페이스에 복사하여 실행하되, 실제 배터리 센서로 해석하지 않는다.

**ACCEPT:** 단일 패키지 빌드·`test_node` 등록·`/my_robot_node` 탐색·Heartbeat 3회 이상·종료 후 노드 삭제·OOP 설명. **NOT_RUN:** 리뷰 컨테이너의 실제 Jazzy 실행. 증거: OS/ROS 버전, `git rev-parse HEAD`, colcon 로그, `ros2 node list` 전후, Ctrl+C 종료 로그.

[1.6절 코드 리뷰](SECTION_1_6_REPORT_KO.md)
