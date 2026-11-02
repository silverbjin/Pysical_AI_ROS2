# LAB 1.5 — colcon 빌드 시스템과 패키지 생성

**실습 환경:** Ubuntu 24.04 + ROS 2 Jazzy + Python 3.12 + colcon. 절별 재현용 워크스페이스는 기존 다른 장과 격리한다. **실행 상태: NOT_RUN (가이드 작성 완료)**.

## 1. 준비
권장 Ubuntu 24.04/ROS 2 Jazzy/Python 3.12. **새 워크스페이스**를 사용한다. 원고의 `~/robot_ws` 대신 `~/ch01_lab_15`로 다른 장과 충돌을 피한다.

## 2. 신규 패키지 생성 실습 (원고 1.5.2)
```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ch01_lab_15/src
cd ~/ch01_lab_15/src
ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name simple_controller my_robot_controller --dependencies rclpy std_msgs
test -f my_robot_controller/package.xml
test -f my_robot_controller/setup.py
test -f my_robot_controller/setup.cfg
find my_robot_controller -maxdepth 3 -type f | sort
```
**중요:** 원고의 `--node_name`이 아니라 공식 Jazzy 옵션 `--node-name`이다. 이미 동명의 폴더가 있으면 새 실습 워크스페이스를 사용하며 원본을 덮어쓰지 않는다.

## 3. 초기 생성 패키지 빌드
```bash
cd ~/ch01_lab_15
colcon list --names-only
colcon build --symlink-install --packages-select my_robot_controller
source install/setup.bash
ros2 pkg executables my_robot_controller
ros2 run my_robot_controller simple_controller
```
**기대:** 기본 생성 Hello World 노드가 정상 진입·종료. 실제 생성 결과의 entry point 이름은 `setup.py`에서 재확인한다. 이 단계에서 **1.6절 최종 `test_node`가 나오지 않아도 정상**이다.

## 4. 저장소 완성 패키지와 대조
```bash
grep -n "console_scripts\|test_node\|simple_controller" ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller/setup.py
grep -n "rclpy\|std_msgs" ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller/package.xml
cat ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller/setup.cfg
```
원고 1.5는 생성기 기본값 `simple_controller`, 1.6 완성된 파일의 실제 실행파일은 `test_node`. 생성·완성 상태를 같은 것으로 취급하지 않는다. `setup.py` entry point를 변경하는 경우 **재빌드 및 source**가 필요하다.

## 5. 완성본 별도 재현
```bash
mkdir -p ~/ch01_lab_15_complete/src
cp -a ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller ~/ch01_lab_15_complete/src/
cd ~/ch01_lab_15_complete
source /opt/ros/jazzy/setup.bash
python3 -m compileall -q src/my_robot_controller
colcon build --symlink-install --packages-select my_robot_controller
source install/setup.bash
ros2 pkg executables my_robot_controller
ros2 run my_robot_controller test_node
```
기대 1초 간격 Heartbeat 로그. 해당 장면의 상세 해설은 1.6절. Ctrl+C 종료.

## 6. 패키지 구조·Acceptance
```bash
cd ~/ch01_lab_15_complete
ros2 pkg prefix my_robot_controller
find install -path '*lib/my_robot_controller*' -maxdepth 8
```
`package.xml` 의존성, `setup.py` 별칭, `setup.cfg` 실행 위치, `resource` 등록을 구분하여 설명한다. **ACCEPT:** 생성 명령 성공·패키지 구조 5종·선택 빌드·초기 simple_controller 및 최종 test_node 명령 차이 증명. **NOT_RUN:** 이 리뷰 환경의 실제 Jazzy 실행.

## 실습 Evidence 템플릿

| 확인 내용 | 실제 결과·로그 | 판정 |
|---|---|---|
| `ros2 doctor --report` / `git rev-parse HEAD` | 실습 후 기록 | NOT_RUN |
| 빌드 종료 코드 및 실행파일 경로 | 실습 후 기록 | NOT_RUN |
| stdout/stderr·관찰 결과·문제 해결 | 실습 후 기록 | NOT_RUN |

[SECTION 1.5 코드 리뷰](SECTION_1_5_REPORT_KO.md)
