# 9.7절 코드 리뷰 — 단일 다리 사인파 제어·제어권 충돌

- 검토일: **2026-10-21 (KST)** · 기준 main `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 원고: 9.7 「9.7 조인트 제어 기초: 다리 하나 움직여 보기」
- 결론: **정적 검토 완료, ROS 2·Gazebo 런타임 NOT_RUN, 코드 실행 가능성 미인증**
- 범위: 요청된 리뷰/실습 문서만 추가하며 기존 소스는 수정하지 않음

## 검토한 실제 소스

- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/single_leg_mover.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/stand_up.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`
- `Ch09/ros2_ws/src/my_quadruped_bot/setup.py`

## 발견 사항

| 심각도 | 실제 코드 관찰 | 문제·개선 권고 |
|---|---|---|
| 높음 | stand_up 10Hz와 single_leg_mover 100Hz가 같은 fr_thigh ROS 토픽에 명령을 발행 | 동시 실행 시 기립 목표 -0.6과 sine 목표가 경합. 단일 제어권자 또는 다른 관절 제외 기능 필요 |
| 확인 | single_leg_mover offset=-0.6, amplitude=0.3, frequency=1.0Hz, timer_period=0.01 | 관절 목표 범위 -0.9~-0.3 rad. 실제 joint limit(-1,4) 안이지만 부딪힘·낙상은 별도 검증 |
| 확인 | 실제 ROS 토픽 /model/my_quadruped/joint/fr_thigh_joint/cmd_pos, Gazebo 측은 /0/cmd_pos | 원고 9.7.1의 ROS CLI 예시 /0 포함은 현행 bridge와 불일치 |
| 주의 | single_leg_mover는 0.01초 고정 증가 누적을 사용 | 콜백 스케줄 지연 시 실제 시간의 1Hz 파형과 어긋남. monotonic/ROS Clock 기반 경과 시간 권고 |
| 주의 | rqt_plot에서 sensor_msgs/JointState는 이름 배열과 위치 배열로 구성됨 | 문자열 관절 이름을 직접 지표로 선택할 수 없을 수 있음. name 순서를 확인한 index 지정 또는 별도 추출 노드 필요 |
| 주의 | trot_gait_preview는 4개 thigh 토픽을 발행하며 stand_up과 전부 충돌할 수 있음 | 미검증 trot를 안정 보행으로 소개하지 말고 파형 미리보기로 제한 |

## 리뷰 절차와 실행 검증의 구분

- **정적 리뷰:** 원격 GitHub main의 파일 전문과 첨부 원고를 대조하여 명칭, 값, 토픽·의존성·실행 흐름의 논리 문제를 확인했다.
- **NOT_RUN:** 이 환경에는 실제 ROS 2 Jazzy / Gazebo Harmonic 시뮬레이터가 준비되어 있지 않다. `colcon build`, `colcon test`, GUI, 브리지 통신, 관절 동작·물리 기립, WSL2 화면을 실행하지 않았다.
- **검증 보류:** 원격에서 읽은 파일이 XML·Python 구문상 무오류임을 `xacro`나 ROS 런타임 결과로 확인한 것은 아니다. 아래 기대는 가이드에 있는 사용자의 실행 결과로 검증해야 한다.

## 검증 수용 기준 및 재현 지점

1. ROS 토픽과 Gazebo cmd_pos 토픽의 경로 차이를 확인했는가?
2. -0.6 중심·0.3 진폭·1Hz 파형의 예상 상한/하한을 계산했는가?
3. FR thigh joint_states 배열 인덱스를 실제 name으로 확인했는가?
4. stand_up와 명령 토픽이 겹치지 않도록 보장했는가?

**통과 기준:** 명령의 사인파 형태, 관절 실제 위치 추종과 잔여 3다리 안정성을 서로 다른 기준으로 측정. 두 publisher 동시 실행은 회피하거나 변경 실험으로 명시해야 한다.

## 원고·교재 수정 및 후속 구현 권고

원고 9.7의 /0 ROS 명령 예시는 현행 bridge 경로와 다르다. 또한 stand_up과 single_leg_mover를 동시에 실행하는 흐름은 교육 실습의 핵심 차단 요인이다.

실제 코드 변경은 별도 승인된 수정 작업에서 담당하도록 남긴다. 수정 후에 같은 명령으로 RED→GREEN, 빌드·runtime·Evidence를 남겨야 한다. [실습 가이드](LAB_9_7_GUIDE_KO.md) · [Ch09 원본](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
