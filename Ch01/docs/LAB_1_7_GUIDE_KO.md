# LAB 1.7 — ROS 2 Twist 발행·의존성 관리 실습

**목표:** `geometry_msgs/msg/Twist` 메시지·ROS 2 Publisher·타이머·`package.xml` 의존성·`setup.py` 실행파일 등록·ROS 토픽 remapping을 관찰한다. 실제 이동 실습이 아니라 **토픽 메시지 확인 실습**이다.

## 1. 권장 환경과 브랜치

Ubuntu 24.04 / WSL2 Ubuntu 24.04, ROS 2 Jazzy, Python 3.12 및 colcon. 새 터미널에서 과거 장의 환경 overlay를 제거한다.

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git ~/Pysical_AI_ROS2
cd ~/Pysical_AI_ROS2
git fetch origin
git switch --track origin/feat/ch01-section-1-7
source /opt/ros/jazzy/setup.bash
python3 --version
ros2 --help >/dev/null
colcon --help >/dev/null
```

로컬 브랜치가 이미 있으면 `git switch feat/ch01-section-1-7`. 작업 브랜치의 `ref/setup.cfg`는 1.6 브랜치에서의 수정과 동일하며 두 브랜치 모두 독립적으로 빌드할 수 있다.

## 2. 패키지 복사·컴파일·빌드

```bash
mkdir -p ~/ch01_lab_17/src
cp -a ~/Pysical_AI_ROS2/Ch01/ref ~/ch01_lab_17/src/my_first_package
cd ~/ch01_lab_17
python3 -m compileall -q src/my_first_package
colcon list --names-only
colcon build --symlink-install --packages-select my_first_package
source install/setup.bash
ros2 pkg prefix my_first_package
ros2 pkg executables my_first_package
ros2 interface show geometry_msgs/msg/Twist
```

실행파일 `simple_node` 및 `cmd_publisher`가 보여야 한다. ROS Python 패키지의 메시지 의존성은 `package.xml`의 `<depend>geometry_msgs</depend>`, 실행파일은 `setup.py`의 `console_scripts`에서 연결된다. `setup.cfg`는 ROS 2의 실행파일 디렉터리를 지정한다.

## 3. 실제 로봇 토픽과 격리된 발행/구독 확인

실물 로봇·Gazebo와 연결된 `/cmd_vel`에는 보내지 말고, **실습용 `/ch01_demo/cmd_vel`로 remap**한다. 터미널 A:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ch01_lab_17/install/setup.bash
ros2 topic echo /ch01_demo/cmd_vel
```

터미널 B:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ch01_lab_17/install/setup.bash
ros2 run my_first_package cmd_publisher --ros-args \
  -r cmd_vel:=/ch01_demo/cmd_vel \
  -p linear_x:=0.2 \
  -p angular_z:=0.5 \
  -p publish_count:=10
echo "exit_code=$?"
```

예상: 약 0.5초 간격으로 10개 `Twist` 메시지에서 `linear.x=0.2`, `angular.z=0.5`, 나머지 성분 0을 관찰한다. 마지막에 `Twist()` (전체 속도 0) 송신을 시도하고 자체 종료한다. `exit_code=0`이 기대되지만 실제 확인 전에는 PASS가 아니다.

**단위:** `linear.x`는 m/s, `angular.z`는 rad/s. 메시지 발행 성공은 실제 로봇이 해당 속도로 이동한다는 증거가 아니다. 종료 시 0 명령은 best-effort이며 실제 로봇의 안전 정지 신뢰성을 보장하지 않는다.

## 4. 기본 안전값 및 진단

기본값은 `linear_x=0.0`, `angular_z=0.0`, `publish_count=10`이다. 별도 수신자 없이 실행한다:

```bash
ros2 run my_first_package cmd_publisher --ros-args -r cmd_vel:=/ch01_demo/cmd_vel
```

모든 Twist 선속도/각속도 성분이 0이어야 한다. 토픽을 먼저 구독한 뒤 publish 노드를 실행한다. 노드가 종료되면 `ros2 topic list`에서 토픽이 사라질 수 있으며 이는 정상이다.

진단용 추가 터미널 (발행 노드가 활동 중일 때만):

```bash
ros2 node list
ros2 node info /cmd_publisher_node
ros2 topic info -v /ch01_demo/cmd_vel
ros2 topic hz /ch01_demo/cmd_vel
```

`ros2 topic hz`의 2Hz 근사값은 네트워크/스케줄러 영향을 받는다. 발행 횟수가 10회여서 측정 시간이 짧을 수 있다.

## 5. 개념 확인과 확장 실습

1. `geometry_msgs/msg/Twist`는 `Vector3 linear`와 `Vector3 angular`를 가지며, 이 코드는 각각 x·z 성분만 설정한다.
2. `create_publisher(Twist, 'cmd_vel', 10)`의 마지막 값 10은 속도가 아니라 QoS History depth다.
3. `setup.py`의 `cmd_publisher`와 `rclpy.Node`의 이름 `cmd_publisher_node`는 서로 다른 개념이다.
4. `--ros-args -r cmd_vel:=/ch01_demo/cmd_vel`는 코드 수정 없이 실습 토픽만 격리한다.
5. `-p publish_count:=4`로 발행 횟수를 바꿔 종료 시점과 메시지 수를 비교한다. `-p publish_count:=0`은 초기화 오류가 예상되며 입력 검증 사례다.

## 6. 오류 및 합격 기준

| 현상 | 진단 |
|---|---|
| `Package not found` | `source ~/ch01_lab_17/install/setup.bash`, `ros2 pkg prefix my_first_package` |
| `No executable found` | `src/my_first_package/setup.cfg`가 있는지 확인 후 재빌드 |
| `geometry_msgs` import 실패 | ROS Jazzy source 및 메시지 패키지 설치 확인 |
| 토픽 수신 없음 | subscriber를 먼저 실행, 토픽 remap 문자열과 ROS_DOMAIN_ID 일치 여부 검사 |
| 다른 로봇이 반응 | 즉시 중지하고 `/ch01_demo/cmd_vel` 격리 및 로봇 제어권 확인 (실물 구동 테스트 금지) |
| 종료 후에도 로봇 움직임 | Twist zero 송신에 의존하지 말고 실제 로봇의 watchdog/비상정지로 대응 |

**Acceptance:** 패키지 빌드, `cmd_publisher` 조회, 올바른 메시지 타입, remap 토픽에서 설정값 10회 및 zero 메시지 확인, 실행 완료 코드 0, 기본 실행은 정지 명령만 발행. 실제 ROS 환경·로그가 없다면 상태는 **NOT_RUN**이다. 검증 환경·커밋·로그를 [리뷰 보고서](SECTION_1_7_REPORT_KO.md)에 남긴다. PR은 사용자 검토 후 별도 진행한다.
