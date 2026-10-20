# LAB 1.6 — ROS 2 노드·타이머·로그 입문 실습

**학습 목표:** `rclpy.init → Node 생성 → create_timer → spin/spin_once → destroy_node → shutdown` 과정을 관찰한다. 이 절은 ROS 2 기본 노드와 가상 배터리 로그 실습이며 실제 모터 제어가 아니다.

## 1. 사전 환경 확인

권장 Ubuntu 24.04 (또는 WSL2 Ubuntu 24.04), ROS 2 Jazzy, Python 3.12, colcon. **새 Ubuntu 터미널**에서 과거 Ch07~Ch13 `install/setup.bash`가 중첩 source되지 않았는지 확인한다.

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git ~/Pysical_AI_ROS2
cd ~/Pysical_AI_ROS2
git fetch origin
git switch --track origin/feat/ch01-section-1-6
source /opt/ros/jazzy/setup.bash
ros2 --help >/dev/null && colcon --help >/dev/null
printenv AMENT_PREFIX_PATH
python3 --version
```

이미 clone한 저장소·로컬 브랜치가 있다면 `git switch feat/ch01-section-1-6` 사용. ROS가 없는 환경에서는 실행 대신 코드 읽기까지만 가능하다.

## 2. 별도의 실습 워크스페이스

`ref/`는 패키지 루트다. `robot_ws/src/examples`의 수많은 ROS 공식 예제를 전체 빌드하지 않도록 필수 세 패키지만 복사한다.

```bash
REPO="$HOME/Pysical_AI_ROS2"
mkdir -p ~/ch01_lab_16/src
cp -a "$REPO/Ch01/ref" ~/ch01_lab_16/src/my_first_package
cp -a "$REPO/Ch01/robot_ws/src/my_robot_controller" ~/ch01_lab_16/src/
cp -a "$REPO/Ch01/robot_ws/src/robot_monitor" ~/ch01_lab_16/src/
cd ~/ch01_lab_16
colcon list --names-only
python3 -m compileall -q src/my_first_package src/my_robot_controller src/robot_monitor
colcon build --symlink-install --packages-select my_first_package my_robot_controller robot_monitor
source install/setup.bash
ros2 pkg executables my_first_package
ros2 pkg executables my_robot_controller
ros2 pkg executables robot_monitor
```

예상 실행파일: `simple_node`, `cmd_publisher`, `test_node`, `battery_node`. 이번 절에서는 `cmd_publisher`를 실행하지 않는다(1.7절).

## 3. 실습 A: 1Hz 기본 Node

터미널 A:

```bash
ros2 run my_first_package simple_node
```

예상 출력은 `Simple Node가 성공적으로 시작되었습니다.` 뒤에 `ROS 2 Jazzy 실행 중... 카운트: 1`, 2, 3 순서다. 스케줄러 영향을 받아 정확한 1.000초는 보장하지 않는다.

터미널 B (새 창에서 **다시 source**):

```bash
source /opt/ros/jazzy/setup.bash
source ~/ch01_lab_16/install/setup.bash
ros2 node list
ros2 node info /simple_node
```

`/simple_node`가 보이는지 확인한다. 터미널 A의 Ctrl+C 후 노드가 사라져야 한다. 타이머 로그는 사용자 토픽을 발행한 것이 아니다.

## 4. 실습 B: Controller Heartbeat

```bash
ros2 run my_robot_controller test_node
```

`로봇 생존 신호 송신 중... (Heartbeat: N)`가 1Hz로 증가한다. 실행파일은 `test_node`이지만 실제 노드 이름은 `/my_robot_node`다. `ros2 node info /my_robot_node`로 확인한다. 이 소스에는 `create_publisher()`가 없으므로 '송신'은 **로그 문구**일 뿐 ROS 토픽 발행은 아니다. Ctrl+C로 종료한다.

## 5. 실습 C: 모의 배터리 분기와 종료

```bash
ros2 run robot_monitor battery_node
echo "exit_code=$?"
```

예상 10번의 출력 잔량: **90, 80, 70, 60, 50, 40, 30, 20, 10, 0%**. 60 초과는 정상, 20 초과는 주의, 나머지는 위험이다. 약 10초 뒤 `모의 배터리 0%` 경고와 함께 **자동 종료 및 exit 0**을 기대한다. 센서 연결·충전·실제 시스템 정지 기능은 전혀 없다.

## 6. 응용과 장애 해결

응용: 기본 타이머 주기를 0.5초로 바꾸어 약 2Hz로 출력되는지 실험한다. `ros2 node list`의 실제 노드명과 실행파일명을 비교한다. 분기 경계 60/20을 바꿔 로깅 횟수를 예측한 뒤 비교한다. 원본 브랜치가 아닌 실습용 복사본에서 수정한다.

| 증상 | 점검 |
|---|---|
| `/opt/ros/jazzy/setup.bash` 없음 | Ubuntu 24.04 Jazzy 설치 여부 확인 |
| `colcon` 없음 | `python3-colcon-common-extensions` 등 설치 |
| `Package not found` | 빌드·`source ~/ch01_lab_16/install/setup.bash`·`ros2 pkg prefix` 확인 |
| `No executable found` | `src/my_first_package/setup.cfg` 및 `setup.py` entry point 확인 후 재빌드 |
| 다른 장의 노드가 실행 | `printenv AMENT_PREFIX_PATH` 및 `ros2 pkg prefix`; 새 셸 사용 |
| 배터리 0% 후 계속 실행 | 최신 `battery_node.py`의 `finished` 루프 확인 및 재빌드 |

**최종 실습 합격:** 세 패키지 선택 빌드, 실행파일 등록, 기본 노드 3회 이상 카운트, Heartbeat 3회 이상, 배터리 10회 후 자체 종료와 exit 0, 전후 노드 목록 확인. 실제 로그와 `git rev-parse HEAD`, `ros2 doctor --report`를 함께 기록하고 [1.6 코드 리뷰](SECTION_1_6_REPORT_KO.md)의 NOT_RUN을 검증 결과로 갱신한다.
