# 9.6절 코드 리뷰 — 기립 노드와 P·I·D 위치 제어 튜닝

- 검토일: **2026-10-21 (KST)** · 기준 main `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 원고: 9.6 「9.6 로봇을 바로 세우기: PD 제어기 튜닝」
- 결론: **정적 검토 완료, ROS 2·Gazebo 런타임 NOT_RUN, 코드 실행 가능성 미인증**
- 범위: 요청된 리뷰/실습 문서만 추가하며 기존 소스는 수정하지 않음

## 검토한 실제 소스

- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/stand_up.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`

## 발견 사항

| 심각도 | 실제 코드 관찰 | 문제·개선 권고 |
|---|---|---|
| 높음 | stand_up.py target_pose는 hip=0, thigh=-0.6, calf=+1.2 rad | 원고 9.6 초반 예시의 thigh +0.5/+0.6, calf -1.0/-1.2와 부호가 반대. 실제 코드 기준으로 수정 |
| 확인 | stand_up은 12개 ROS cmd_pos 토픽(명칭에 /0/ 없음)에 10 Hz로 목표를 전송 | 실제 bridge yaml의 12개 ROS 입력 토픽과 이름이 일치 |
| 주의 | leg.xacro의 실제 게인은 hip P20 D1, thigh/calf P70 D2; 각 관절 I0.1 | 원고 9.6의 권장 hip P80, thigh P150~200, calf P150과 다름. 실제 설정은 순수 PD가 아닌 PID |
| 주의 | JointPositionController 설정에는 i_max/i_min가 포함되고 effort는 hip 20, thigh/calf 30 | 게인을 바꿔도 출력 토크/포화와 제어 주기 및 초기 침하가 반응을 좌우함 |
| 높음 | stand_up.py는 단일 다리 실습의 fr_thigh_joint 토픽도 지속 발행 | single_leg_mover, trot_gait_preview와 동시에 실행하면 다중 퍼블리셔 명령 충돌 |

## 리뷰 절차와 실행 검증의 구분

- **정적 리뷰:** 원격 GitHub main의 파일 전문과 첨부 원고를 대조하여 명칭, 값, 토픽·의존성·실행 흐름의 논리 문제를 확인했다.
- **NOT_RUN:** 이 환경에는 실제 ROS 2 Jazzy / Gazebo Harmonic 시뮬레이터가 준비되어 있지 않다. `colcon build`, `colcon test`, GUI, 브리지 통신, 관절 동작·물리 기립, WSL2 화면을 실행하지 않았다.
- **검증 보류:** 원격에서 읽은 파일이 XML·Python 구문상 무오류임을 `xacro`나 ROS 런타임 결과로 확인한 것은 아니다. 아래 기대는 가이드에 있는 사용자의 실행 결과로 검증해야 한다.

## 검증 수용 기준 및 재현 지점

1. 명목 자세와 원고 초기 자세의 관절 부호 차이를 설명할 수 있는가?
2. hip/thigh/calf의 실제 PID 계수를 모두 기록했는가?
3. /joint_states의 각도 추종 및 기립을 일정 시간 실제로 관찰했는가?
4. 명령 퍼블리셔가 관절당 하나인지 확인했는가?

**통과 기준:** 토픽 수신, 관절 명령 추종, 실제 GUI 안정 기립을 분리해 PASS/FAIL 판정한다. 코드상 목표 전송 확인만으로 기립 성공을 주장할 수 없다.

## 원고·교재 수정 및 후속 구현 권고

9.6의 수치 표는 제어기 튜닝의 학습 예시이지 현재 저장소의 실제 튜닝값이 아니다. 0.1의 I게인을 사용 중이므로 'PD만 사용'이라는 본문도 정정이 필요하다.

실제 코드 변경은 별도 승인된 수정 작업에서 담당하도록 남긴다. 수정 후에 같은 명령으로 RED→GREEN, 빌드·runtime·Evidence를 남겨야 한다. [실습 가이드](LAB_9_6_GUIDE_KO.md) · [Ch09 원본](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
