# 9.6절 실습 가이드 — 기립 노드와 P·I·D 위치 제어 튜닝

> 이 문서는 첨부 원고의 학습 단계와 실제 저장소 코드를 맞춘 **재현 가이드**다. 권장: ROS 2 Jazzy, Gazebo Harmonic, Ubuntu 24.04/WSL2. 실행 예시는 현재 세션에서 물리 시뮬레이터로 성공 검증된 명령이 아니다.

## 목표

관절 목표값과 P/I/D 게인, 브리지 토픽의 대응 관계를 이해하고 기립 안정성 테스트를 재현할 수 있게 한다.

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

## 2. 시뮬레이션과 기립 노드

터미널 1:
```bash
ros2 launch my_quadruped_bot simulation.launch.py
```

터미널 2: Ch09 workspace를 source한 뒤:
```bash
ros2 run my_quadruped_bot stand_up
```

터미널 3:
```bash
ros2 topic echo /joint_states --once
ros2 topic info /model/my_quadruped/joint/fr_thigh_joint/cmd_pos -v
ros2 topic echo /model/my_quadruped/joint/fr_thigh_joint/cmd_pos --once
```

**실제 코드의 명목 목표:** hip=0.0 rad, thigh=-0.6 rad, calf=+1.2 rad, 전송 10 Hz. ROS 토픽에 `/0/`가 없음을 유의한다. Gazebo 값이 변하지 않으면 브리지 맵부터 확인한다.

## 3. P-D 튜닝 실험 설계

관절별 현재 `p_gain,d_gain,i_gain`을 표에 적는다. 기존 코드는 `i_gain=0.1`이라 **I가 0이 아니다.** 순수 PD 비교가 필요하면 별도 실험 브랜치에서 `i_gain=0`으로 통제하고 빌드·재시작한다.

| 조건 | P | D | I | 측정 |
|---|---:|---:|---:|---|
| 현재 hip | 20 | 1 | 0.1 | 안정화 시간, 진동 폭 |
| 현재 thigh | 70 | 2 | 0.1 | 처짐, 흔들림 |
| 현재 calf | 70 | 2 | 0.1 | 발 접촉 유지 |
| P 변경 실험 | 기준 ± 일정 비율 | 고정 | 고정 | 같은 초기 높이·동일 시간 |
| D 변경 실험 | 고정 | 기준 ± 일정 비율 | 고정 | overshoot 및 정상상태 |

숫자를 임의로 성공값이라 단정하지 않는다. `/joint_states`의 name/position을 매칭하고 각도 응답을 로그로 추출한다. 20초 같은 동일한 시뮬레이션 시간 구간에서 몸통 높이, 롤/피치, 발의 지면 접촉, 발산 여부를 비교한다.

## 4. 제어 명령 소유권

기립 실습에서는 **stand_up만** 12개 명령 토픽을 소유하게 한다. 다른 컨트롤러의 병렬 실행을 피한다. `ros2 topic info ... -v`의 퍼블리셔 수를 확인해 1을 기대한다(브리지 구성을 포함해 확인). 뒤의 9.7절을 실행하기 전에는 command ownership을 별도로 정리한다.

## 5. 결과 해석

기립하지 못한다고 바로 P만 올리지 않는다. 순서: 컨트롤러 토픽 연결 → 관절 목표/부호 → 초기 스폰 자세 → 지면 접촉·마찰 → 관성·질량중심 → 힘 포화 → 게인 재튜닝. 실물 로봇에 시뮬레이션 게인을 그대로 적용하지 않는다.

## 6. 과제 및 제출 Evidence

| 확인할 질문 | 기록할 결과 |
|---|---|
| 1. 명목 자세와 원고 초기 자세의 관절 부호 차이를 설명할 수 있는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 2. hip/thigh/calf의 실제 PID 계수를 모두 기록했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 3. /joint_states의 각도 추종 및 기립을 일정 시간 실제로 관찰했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 4. 명령 퍼블리셔가 관절당 하나인지 확인했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |

**Acceptance Criteria:** 토픽 수신, 관절 명령 추종, 실제 GUI 안정 기립을 분리해 PASS/FAIL 판정한다. 코드상 목표 전송 확인만으로 기립 성공을 주장할 수 없다.

## 7. 원고 대비 유의점

9.6의 수치 표는 제어기 튜닝의 학습 예시이지 현재 저장소의 실제 튜닝값이 아니다. 0.1의 I게인을 사용 중이므로 'PD만 사용'이라는 본문도 정정이 필요하다.

연습 환경에서 실제 Gazebo 물리·ROS 연결을 실행하지 못했다면 모든 런타임 지표를 **NOT_RUN**으로 남긴다. 섣부른 수치 추정이나 과거 장의 증거 재사용은 금지한다.

[리뷰 보고서](SECTION_9_6_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 문서 기준](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs)
