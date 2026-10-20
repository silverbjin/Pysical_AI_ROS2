# LAB 1.7 — package.xml·setup.py·rosdep 재현성 실습

**원고 범위:** 1.7.1 (manifest·의존성), 1.7.2 (rosdep), 1.7.3 (ament_python 패키징·자산 설치). **주 실습 패키지:** `my_robot_controller`. 원고의 가상 `my_ai_robot_pkg`는 실제 리포지토리에 없다.

## STEP 1. 전용 환경과 소스 준비

```bash
# Ubuntu 24.04 / ROS 2 Jazzy 터미널. 이미 clone된 경우 생략
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git ~/Pysical_AI_ROS2
cd ~/Pysical_AI_ROS2
git fetch origin
git switch --track origin/feat/ch01-section-1-7
source /opt/ros/jazzy/setup.bash

mkdir -p ~/ch01_lab_17/src
cp -a ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller ~/ch01_lab_17/src/
cd ~/ch01_lab_17
colcon list --names-only
```

`colcon list`에 `my_robot_controller`가 한 개 표시되는지 확인한다. 기존 브랜치가 존재하면 `git switch feat/ch01-section-1-7`을 사용한다.

## STEP 2. manifest와 실제 import 비교

```bash
cat src/my_robot_controller/package.xml
grep -R "^import rclpy\|^from rclpy" src/my_robot_controller/my_robot_controller
grep -n "console_scripts\|test_node" src/my_robot_controller/setup.py
cat src/my_robot_controller/setup.cfg
```

`rclpy`는 실제 코드 import와 manifest에 모두 있다. `std_msgs`는 현재 코드에서 미사용이나 원고의 패키지 생성 선행 의존성으로 남았다. `test_node = my_robot_controller.simple_controller:main`은 **실행명**과 **모듈/함수**의 결합을 의미한다. `setup.cfg`는 `lib/my_robot_controller` 스크립트 설치 위치를 담당한다.

## STEP 3. rosdep 초기화/의존성 해결

```bash
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
```

`rosdep update`에서 “not initialized”가 출력되면 **최초 한 번만** `sudo rosdep init` 후 `rosdep update`한다. 원고의 `-r`는 실패한 의존성이 있어도 다른 항목 설치를 계속 시도하는 옵션이므로 **전부 성공했다는 의미가 아님**. `-r` 없이 실패 지점을 먼저 보거나, `-r`을 사용할 때는 실패 항목을 별도 기록한다.

## STEP 4. 선택 빌드와 실제 진입점

```bash
cd ~/ch01_lab_17
python3 -m compileall -q src/my_robot_controller
colcon build --symlink-install --packages-select my_robot_controller
source install/setup.bash
ros2 pkg prefix my_robot_controller
ros2 pkg executables my_robot_controller
ros2 run my_robot_controller test_node
```

`Heartbeat: 1`, 2, 3 로그 후 Ctrl+C. `ros2 run my_robot_controller simple_controller`는 이 **완성본**에 등록되어 있지 않다(1.5절 초기 생성 패키지와 다름).

## STEP 5. package.xml / setup.py / setup.cfg 역할 테스트

```bash
cd ~/ch01_lab_17
test -f install/my_robot_controller/share/my_robot_controller/package.xml && echo "installed manifest found" || find install -path '*share/my_robot_controller/package.xml'
find install -name test_node -o -name my_robot_controller
ros2 pkg executables my_robot_controller
```

`--symlink-install` 환경에서는 설치 경로가 link를 포함할 수 있다. `setup.py` entry point를 수정하면 재빌드 및 새 터미널 source가 필요하다. `package.xml`은 rosdep 의존성의 기준, `setup.py`는 Python 코드·자산 설치 규칙의 기준이다.

## STEP 6. 원고의 가상 data_files 예제를 실제로 구현하려면

원고의 `my_ai_robot_pkg` 예제는 `launch/*.launch.py`, `config/*.yaml`을 `glob`로 설치한다. **Ch01에는 이 디렉터리가 없으므로 설치 검증 PASS가 될 수 없다.** 응용에서는 별도 새 패키지에 파일을 직접 만든 후 다음을 확인한다: (1) `setup.py`의 `data_files`가 경로를 포함하는지, (2) 실제 `install/share/<package>/launch` 및 `config`에 배포되는지, (3) `ros2 launch`가 파일을 찾는지. 패키지 소유자의 라이선스·maintainer 값을 TODO에서 확정해야 공개 배포 가능하다.

## STEP 7. 보조 패키지와 범위 경계

`Ch01/ref/my_first_package`는 `geometry_msgs`와 `sensor_msgs`를 선언하지만 이번 1.7 주교재 패키지와 다르다. `geometry_msgs.msg.Twist` 코드는 별도 `cmd_publisher` 예제이며 **원고 1.7의 의존성 관리 본문에 해당하지 않는다**. 기본 소스의 무한 비영 `cmd_vel` 송신 노드를 **실제 로봇에 연결하지 않는다**.

**ACCEPT:** rosdep 해결 완료, 선택 colcon build 0, `test_node` 확인, manifest 설치 파일 확인, rclpy import, 라이선스 TODO와 예시 launch/config 미구현 사실 설명. 실측되지 않은 항목은 NOT_RUN으로 둔다. [코드 리뷰](SECTION_1_7_REPORT_KO.md) 참조.
