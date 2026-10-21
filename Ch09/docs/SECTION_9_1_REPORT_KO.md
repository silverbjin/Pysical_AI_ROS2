# 9.1절 코드 리뷰 — 12자유도 기구 구조와 링크 설계

- 검토일: 2026-10-21 (KST)
- 원고: 9.1 「4족 보행 로봇의 해부학: 자유도와 링크 구조」
- 기준: `main` @ `bab76f6ca7df`
- 파일: `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro`, `urdf/parts/leg.xacro`, `urdf/common/robot_properties.xacro`
- 판정: **정적 코드 리뷰 완료 / ROS·Gazebo 실제 실행 NOT_RUN / 운동학·물리 정확성 미인증**

## 검토 결과

| 심각도 | 관찰(실제 소스) | 의미 / 권고 |
|---|---|---|
| 확인 | `<xacro:leg>` 4회, 각 매크로에 hip/thigh/calf 회전 관절 3개 | 전개 시 12개 revolute 관절이 기대됨. 실제 전개·검증은 학습자 환경에서 수행 |
| 확인 | FR=(+1,-1), FL=(+1,+1), RR=(-1,-1), RL=(-1,+1) | REP-103의 X 전방 / Y 좌측과 위치 부호 부합. 링크 축과 자세의 좌우 대칭성은 별도 확인 필요 |
| 주의 | 코드의 thigh joint `origin rpy="0 1.2 0"`, calf joint `rpy="0 -2.4 0"` | 원고의 중립 관절 좌표가 아닌, 고정 관절 프레임 회전으로 외형을 굽힘. 관절 `position=0`이 다리를 수직으로 뻗은 형상이라는 설명과 충돌. Ch10·Ch12의 관절 영점 및 IK 계약과 비교 필수 |
| 주의 | 모든 hip joint 회전축 `1 0 0` | `(+)` 명령이 양쪽 다리에서 모두 외전한다는 서술은 바로 보장되지 않음. 좌/우 링크 방향과 각도 정의를 시각적으로 검증 |
| 주의 | `base_footprint`가 루트이고 `base_link`와 원점이 같은 고정 조인트 | 원고의 `base_link` 루트 가정과 다름. 현재 `base_footprint`는 지면 투영 프레임이 아님 |
| 확인 | 질량: base=6.0 kg, 다리당 hip=0.2, thigh=0.7, calf=0.5, foot=0.1 kg | 기대 합계 `6.0 + 4*(0.2+0.7+0.5+0.1)=12.0 kg`. 원고 표의 hip=0.5, thigh=1.0과 불일치 |

## 확인 방법 및 판정 기준

**원격 소스 정적 검사:** 파일 구조, 4개 매크로 호출, 관절명·축·원점, 질량 상수를 대조했다. Xacro 확장 성공, URDF 파서, TF 발행, Gazebo 중력·접촉은 이 실행 환경에서 테스트하지 않았다.

학습자 실행 환경에서:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
PKG="$(ros2 pkg prefix --share my_quadruped_bot)"
xacro "$PKG/urdf/robot.urdf.xacro" > /tmp/ch09_robot.urdf
check_urdf /tmp/ch09_robot.urdf
ros2 launch my_quadruped_bot display.launch.py
```

**알려진 별도 차단 요인:** 위 `display.launch.py`는 Ch09 대신 `my_robot_description` 패키지의 RViz 설정을 참조하므로, 해당 패키지가 없다면 실패할 수 있다. 이때 소스 경로의 실제 파일 `rviz/display.rviz`를 확인해야 한다.

기대: revolute 12개, fixed 5개(foot 4 + base_footprint 1), 유일한 링크/조인트 명칭, 합계 12.0 kg, 모든 다리 TF 연결. 힙 각도 좌우 부호는 실측 화면으로 판정한다.

## 수정 제안(이번 PR에서 코드 변경하지 않음)

1. 원고의 관절 영점과 코드의 관절 프레임 회전(`rpy`)을 표로 명시하고 Ch10·Ch12 연결 계약을 검토한다.
2. hip 회전 부호를 좌우 독립 검증해 외전/내전 의미를 고정한다.
3. `base_footprint`와 `base_link`의 실제 TF 의미를 문서에 기록한다.
4. 원고의 부품별 질량 표를 실제 코드와 일치시키거나 차이를 설계 변경으로 명시한다.

## 범위·참고

코드 수정, 실물 로봇 검증, ROS2 colcon 빌드, Gazebo GUI 테스트는 수행하지 않았다. `PASS` 기록을 생성하지 않는다. [실습 가이드](LAB_9_1_GUIDE_KO.md), [원본 Ch09 코드](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09), [REP-103](https://www.ros.org/reps/rep-0103.html).
