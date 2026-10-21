# 9.4절 실습 가이드 — Gazebo Harmonic 플러그인과 ROS–Gz 브리지

> 첨부 원고 「9.4 Gazebo Harmonic 환경 설정 및 플러그인 연동」의 학습 목적을 유지하면서 **현행 Ch09 소스의 실제 명칭·경로**를 적용했다. 환경: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / Python 3.12 기준. 아래 명령은 검증 절차이며 이 세션에서 실제 실행되었다는 뜻이 아니다.

## 학습 목표

12개 position controller, 관절 상태, /clock 및 ROS→Gz 토픽 매핑이 연결되는지 확인한다.

## 1. 사전 준비와 워크스페이스

```bash
# 새 터미널: 다른 장의 install/setup.bash는 source하지 않음
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
PKG="$(ros2 pkg prefix --share my_quadruped_bot)"
```

`ros2 pkg prefix`가 **Ch09/ros2_ws**를 가리켜야 한다. 같은 이름의 Ch10/Ch11 패키지가 overlay에 남으면 지금 점검 중인 코드와 다른 버전이 실행된다. WSL2에서는 Gazebo GUI와 ROS 실행을 Ubuntu 터미널에서 수행한다.

## 2. Gazebo·브리지 기동

```bash
ros2 launch my_quadruped_bot simulation.launch.py
```

새 터미널에서 동일 Ch09 overlay를 source한 뒤:
```bash
ros2 topic list | sort
ros2 topic info /joint_states -v
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
ros2 topic list | grep cmd_pos
gz topic -l | grep cmd_pos
```

**기대:** ROS 명령 토픽 12개는 `/model/my_quadruped/joint/fr_hip_joint/cmd_pos`처럼 `/0/`이 없다. 대응하는 Gazebo 토픽은 `.../fr_hip_joint/0/cmd_pos`이다. `/joint_states`은 Gazebo → ROS 방향, `/clock`도 Gazebo → ROS 방향이다.

## 3. 토픽을 안전하게 1회 시험

Gazebo GUI에서 해당 관절과 현재 자세를 확인한 후 작은 명령만 적용한다. **stand_up과 다른 제어 노드는 먼저 중지한다.**

```bash
ros2 topic pub --once /model/my_quadruped/joint/fr_hip_joint/cmd_pos \
  std_msgs/msg/Float64 "{data: 0.05}"
```

한 번의 명령이 실제 관절 변화로 연결되는지 `/joint_states` 또는 Gazebo에서 확인한다. 명령이 안 보이면 브리지 YAML의 `ros_topic_name`과 `gz_topic_name` 및 Gazebo 모델 이름을 각각 확인한다.

## 4. 변환된 SDF 마찰 계수 점검

```bash
xacro "$PKG/urdf/robot.urdf.xacro" > /tmp/ch09_9_4.urdf
gz sdf -p /tmp/ch09_9_4.urdf > /tmp/ch09_9_4.sdf
grep -n -A8 -B3 '<friction>' /tmp/ch09_9_4.sdf | head -80
```

이 도구의 오류나 출력 부재도 증거로 기록한다. Xacro의 `<gazebo reference=...>` 설정이 실제 SDF foot collision의 마찰로 전달되는지 살펴보고, 사용 엔진이 ODE 값들을 어떻게 해석하는지도 확인한다.

## 5. 시간 동기화 확인

```bash
ros2 param get /robot_state_publisher use_sim_time
```

현재 `simulation.launch.py`에는 명시 설정이 없으므로 결과가 false일 수 있다. `/clock` 존재만으로 자동 true가 되지는 않는다. 9.5절의 다른 런치와 비교한다.

## 6. 학습 과제·증거 기록

| 실습 과제 | 제출 Evidence |
|---|---|
| 1. ROS joint cmd_pos 12개와 gz cmd_pos 12개를 실제로 관찰했는가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 2. /joint_states와 /clock의 메시지 타입 및 방향은? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 3. SDF 변환 결과의 발 마찰 계수가 실효 있게 들어갔는가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 4. robot_state_publisher의 use_sim_time 상태는? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |

**수용 기준:** 실제 메시지 수신·매핑·SDF 변환이 확인되어야 한다. GUI 실행, 마찰·접촉 안정성은 이 문서 작성 환경에서 NOT_RUN이다.

## 7. 흔한 오류와 교정 포인트

원고의 `/model/.../0/cmd_pos`는 Gazebo 토픽이다. 현재 ROS 발행 경로는 `/0/`이 없는 경로이므로 명령 예제에서 혼동하지 않는다.

오류를 만나면 재현 명령과 `ros2 pkg prefix my_quadruped_bot` 출력, `ros2 topic list` 결과, 사용 중인 ROS/Gazebo 버전을 함께 남긴다. 다른 장의 동명 패키지 overlay를 먼저 배제한다. 필요한 코드를 검토한 다음 실제 환경에서 다시 검증할 때까지 **실행 완료로 판정하지 않는다.**

관련: [코드 리뷰](SECTION_9_4_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 교육 문서 형식](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs).
