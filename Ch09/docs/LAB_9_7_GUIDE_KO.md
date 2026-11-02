# 9.7절 실습 가이드 — 단일 다리 사인파 제어·제어권 충돌

> 이 문서는 첨부 원고의 학습 단계와 실제 저장소 코드를 맞춘 **재현 가이드**다. 권장: ROS 2 Jazzy, Gazebo Harmonic, Ubuntu 24.04/WSL2. 실행 예시는 현재 세션에서 물리 시뮬레이터로 성공 검증된 명령이 아니다.

## 목표

직접 CLI 발행 및 sine 궤적 명령을 실습하면서 다중 퍼블리셔 제어권과 실제 관절 응답의 차이를 이해한다.

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

## 2. 실제 ROS 토픽 찾기

```bash
ros2 launch my_quadruped_bot simulation.launch.py
# 두 번째, Ch09 overlay를 source한 터미널에서
ros2 topic list | grep fr_thigh
ros2 topic info /model/my_quadruped/joint/fr_thigh_joint/cmd_pos -v
ros2 topic pub --once /model/my_quadruped/joint/fr_thigh_joint/cmd_pos \
  std_msgs/msg/Float64 "{data: -0.5}"
```

원고의 `.../fr_thigh_joint/0/cmd_pos`는 **Gazebo 내부 토픽**이고, ROS 2 명령 토픽에는 `/0/`이 없다. 컨트롤러 중복 실행을 피한 상황에서 CLI 단발 명령을 확인한다.

## 3. 사인파 생성 노드

```bash
ros2 run my_quadruped_bot single_leg_mover
```

이 명령은 `θ(t)=-0.6+0.3sin(2π×1.0×t)`를 목표로 보낸다. 100Hz 요청이 곧 실제 100Hz 실행 보장을 뜻하지는 않는다. GUI에서 FR thigh가 움직이는지 확인하고 `/joint_states` 이름 배열을 같이 기록한다.

**중요: 동시에 `ros2 run ... stand_up`을 실행하지 않는다.** 이미 기립시킨 경우 `stand_up`을 종료한 후 다음 관찰을 진행한다. 이 상태에서 다른 11관절에 대한 명령 유지/기립 안정성은 설치된 Gazebo 컨트롤러와 실제 제어 소유권에 좌우되므로 성공을 보증할 수 없다. 교육용 안정적인 재현에는 단일 노드가 12개 명령을 통합 발행하고 FR thigh만 sine을 적용하도록 **별도 코드 수정**하는 편이 적합하다.

## 4. RQT와 측정

```bash
ros2 topic echo /model/my_quadruped/joint/fr_thigh_joint/cmd_pos
ros2 topic echo /joint_states --once
ros2 run rqt_plot rqt_plot
```

명령용 Float64는 `/model/my_quadruped/joint/fr_thigh_joint/cmd_pos/data` 항목으로 확인한다. `/joint_states/position[N]`의 `N`은 매 실행의 `name` 배열에서 `fr_thigh_joint`가 있는 위치를 확인하고 선택한다. name 순서가 고정이라고 단정하면 다른 관절 값을 잘못 비교한다.

## 5. 후속 확장

`trot_gait_preview`는 대각 쌍 FL+RR과 FR+RL thigh에 180° 위상차를 적용하지만 안정 보행/지면 접촉을 입증하지 않은 파형 실습이다. 9.7 기본 과제와 별도 실행하고, 다른 관절 제어권을 분리한 후 실제 기립·낙상 여부를 관찰한다.

## 6. 과제 및 제출 Evidence

| 확인할 질문 | 기록할 결과 |
|---|---|
| 1. ROS 토픽과 Gazebo cmd_pos 토픽의 경로 차이를 확인했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 2. -0.6 중심·0.3 진폭·1Hz 파형의 예상 상한/하한을 계산했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 3. FR thigh joint_states 배열 인덱스를 실제 name으로 확인했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 4. stand_up와 명령 토픽이 겹치지 않도록 보장했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |

**Acceptance Criteria:** 명령의 사인파 형태, 관절 실제 위치 추종과 잔여 3다리 안정성을 서로 다른 기준으로 측정. 두 publisher 동시 실행은 회피하거나 변경 실험으로 명시해야 한다.

## 7. 원고 대비 유의점

원고 9.7의 /0 ROS 명령 예시는 현행 bridge 경로와 다르다. 또한 stand_up과 single_leg_mover를 동시에 실행하는 흐름은 교육 실습의 핵심 차단 요인이다.

연습 환경에서 실제 Gazebo 물리·ROS 연결을 실행하지 못했다면 모든 런타임 지표를 **NOT_RUN**으로 남긴다. 섣부른 수치 추정이나 과거 장의 증거 재사용은 금지한다.

[리뷰 보고서](SECTION_9_7_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 문서 기준](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs)
