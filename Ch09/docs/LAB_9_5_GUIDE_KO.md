# 9.5절 실습 가이드 — 시뮬레이션 론치·스폰·TF 검증

> 이 문서는 첨부 원고의 학습 단계와 실제 저장소 코드를 맞춘 **재현 가이드**다. 권장: ROS 2 Jazzy, Gazebo Harmonic, Ubuntu 24.04/WSL2. 실행 예시는 현재 세션에서 물리 시뮬레이터로 성공 검증된 명령이 아니다.

## 목표

Gazebo → Xacro/robot_state_publisher → create 스폰 → ros_gz_bridge의 기동 순서와 설치 경로·시간 동기화·TF 루트를 확인한다.

## 1. Ch09 단독 환경 설치·검사

```bash
# 기존 Ch07/Ch08/Ch10/Ch11 설치물을 source하지 않은 새로운 터미널
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
PKG="$(ros2 pkg prefix --share my_quadruped_bot)"
```

패키지 prefix는 **Ch09**의 `install`이어야 한다. 다른 장의 `my_quadruped_bot`이 조회되면 새 터미널에서 source를 다시 수행한다. `package.xml`의 실행 의존성 선언은 불충분하므로 `rosdep`만으로 모든 프로그램이 설치된다고 가정하지 말고 `ros2 pkg executables ros_gz_sim`, `ros2 pkg executables ros_gz_bridge` 등을 점검한다.

## 2. 두 시뮬레이션 런치 비교

**한 번에 하나만 실행한다.** 동일한 `my_quadruped` 모델을 두 번 스폰하면 이름 충돌이 발생한다.

```bash
ros2 launch my_quadruped_bot simulation.launch.py
```

새 터미널에서 Ch09를 source하여 검사:

```bash
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
ros2 param get /robot_state_publisher use_sim_time
ros2 node list
```

**기대:** `/clock`과 `/joint_states`가 실제 출력될 것. 현재 기본 simulation 런치는 `use_sim_time`을 설정하지 않았으므로 false 결과는 문서화해야 할 결함이다. 이 런치를 종료한 뒤 대안 런치를 별도로 실행한다.

```bash
ros2 launch my_quadruped_bot 9-5_simulation.launch.py use_sim_time:=true
```

이후 `ros2 param get /robot_state_publisher use_sim_time`가 `Boolean value is: True`인지 확인한다. 만약 명령 치환 XML 관련 파라미터 에러가 발생하면 런치의 `Command` 사용 위치를 먼저 점검한다.

## 3. 로봇 스폰과 TF 트리

```bash
ros2 run tf2_tools view_frames
ros2 topic info /robot_description -v
ros2 topic info /joint_states -v
ros2 topic echo /tf --once
```

`view_frames`는 현재 작업 디렉터리에 `frames_*.pdf` 또는 해당 버전의 결과 파일을 만들 수 있다. 저장 위치·파일 이름을 실제 출력으로 확인한다. 루트는 **`base_footprint`**이고 그 아래 고정 `base_link`가 연결된다. 이는 지면에 투영된 발자국 프레임이 아니라 현재 URDF의 고정 원점이다.

## 4. 설치 의존성과 launch 자산 점검

```bash
find "$PKG/launch" -maxdepth 1 -type f -print
test -f "$PKG/worlds/empty_world.sdf"
test -f "$PKG/config/ros_gz_bridge.yaml"
test -f "$PKG/rviz/display.rviz"
ros2 pkg executables my_quadruped_bot
```

`display.launch.py`가 Ch08의 `my_robot_description`에 잘못 의존한다는 점을 기록한다. 원고의 `source install/setup.`는 오타이므로 `source install/setup.bash`를 사용한다.

## 6. 과제 및 제출 Evidence

| 확인할 질문 | 기록할 결과 |
|---|---|
| 1. 동일 워크스페이스에서 simulation vs 9-5_simulation의 use_sim_time 값 차이는? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 2. create가 실제 로봇을 스폰했는가? 이름과 월드를 확인했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 3. base_footprint에서 모든 4개 발까지 TF가 연결되는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 4. Ch09 단독 source에서 RViz 설정 파일을 찾을 수 있는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |

**Acceptance Criteria:** Gazebo 스폰 로그, /joint_states, /clock, TF 및 시간 설정을 각각 별개로 확인해야 한다. GUI에 로봇이 보인다는 사실 하나로 PASS로 처리하지 않는다.

## 7. 원고 대비 유의점

원고의 경로·launch 명칭·ROS 파라미터를 현재 두 런치의 차이와 비교해야 한다. ROS 시간 true 설정이 기본 simulation 런치에 자동 적용된다고 가정하지 않는다.

연습 환경에서 실제 Gazebo 물리·ROS 연결을 실행하지 못했다면 모든 런타임 지표를 **NOT_RUN**으로 남긴다. 섣부른 수치 추정이나 과거 장의 증거 재사용은 금지한다.

[리뷰 보고서](SECTION_9_5_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 문서 기준](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs)
