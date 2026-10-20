# LAB 1.4 — 워크스페이스의 구조와 이해

**실습 환경:** Ubuntu 24.04 + ROS 2 Jazzy + Python 3.12 + colcon. 절별 재현용 워크스페이스는 기존 다른 장과 격리한다. **실행 상태: NOT_RUN (가이드 작성 완료)**.

## 1. 수업 전 환경
Ubuntu 24.04 / Jazzy. 1.2절을 먼저 완료. 별도 새 셸에서 `source /opt/ros/jazzy/setup.bash`를 실행한다. 저장소는 `~/Pysical_AI_ROS2`에 clone되어 있다고 가정한다(미복제 시 `git clone https://github.com/silverbjin/Pysical_AI_ROS2.git ~/Pysical_AI_ROS2`).

## 2. 워크스페이스 구조 이해
```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ch01_lab_14/src
cd ~/ch01_lab_14
pwd
find . -maxdepth 1 -type d
```
최초에는 `src`만 있다. 빌드하면 `build`(중간 산출물), `install`(실행파일), `log`(기록)가 추가된다. 이 셋은 git에 commit하지 않는다.

## 3. 저장소의 공식 예제 한 개만 복사
```bash
cp -a ~/Pysical_AI_ROS2/Ch01/robot_ws/src/examples/rclpy/topics/minimal_publisher ~/ch01_lab_14/src/
cd ~/ch01_lab_14
colcon list --names-only
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install --packages-select examples_rclpy_minimal_publisher
source install/setup.bash
ros2 pkg executables examples_rclpy_minimal_publisher
ros2 pkg prefix examples_rclpy_minimal_publisher
```
`rosdep update`가 초기 설정 미완료 오류이면 시스템에서 최초 한 번 `sudo rosdep init` 후 `rosdep update` 실행. `colcon list`에 패키지 1개, `ros2 pkg executables`에 `publisher_member_function`이 나와야 한다.

## 4. 실행 및 토픽 검증
터미널 A:
```bash
source /opt/ros/jazzy/setup.bash
source ~/ch01_lab_14/install/setup.bash
ros2 run examples_rclpy_minimal_publisher publisher_member_function
```
터미널 B:
```bash
source /opt/ros/jazzy/setup.bash
source ~/ch01_lab_14/install/setup.bash
ros2 topic echo /topic
ros2 topic info -v /topic
```
발행 로그 Hello World 카운트 및 수신 메시지 3개 이상 확인. 예제 트리는 ROS 2 공식 소스의 저장소 스냅샷이므로 최신 upstream 버전과 완전히 일치한다고 가정하지 않는다.

## 5. Overlay 개념·복구 훈련
```bash
echo "$AMENT_PREFIX_PATH" | tr ':' '\n' | head -20
ros2 pkg prefix examples_rclpy_minimal_publisher
ls -d build install log
```
새 셸에서 `source /opt/ros/jazzy/setup.bash`만 했을 때와 개인 overlay source 후의 설치 경로를 비교한다. 충돌 시 오래된 Ch07~Ch13 install이 섞였는지 확인한다. 클린 빌드는 반드시 `cd ~/ch01_lab_14 && pwd`로 확인한 다음에만 `rm -rf build install log`를 실행한다.

**ACCEPT:** 1패키지 선택 빌드 성공, 4개 디렉터리 설명, `publisher_member_function` 실행, /topic 3회 수신, overlay 경로 확인. **NOT_RUN:** 검토 환경에서 실제 Jazzy 실행·DDS 네트워크/GUI.

## 실습 Evidence 템플릿

| 확인 내용 | 실제 결과·로그 | 판정 |
|---|---|---|
| `ros2 doctor --report` / `git rev-parse HEAD` | 실습 후 기록 | NOT_RUN |
| 빌드 종료 코드 및 실행파일 경로 | 실습 후 기록 | NOT_RUN |
| stdout/stderr·관찰 결과·문제 해결 | 실습 후 기록 | NOT_RUN |

[SECTION 1.4 코드 리뷰](SECTION_1_4_REPORT_KO.md)
