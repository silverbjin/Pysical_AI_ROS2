# 5.4절 코드 리뷰 — JointState 상태 트래킹과 분석

> 기준: 2026-10-20 KST, main @ 1b9e8215e2130c492969bb0da52a82e707c3a16f.
> 범위: 원고 5장 및 Ch05/ros2_ws/src/manipulation_basics. ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic을 목표 환경으로 한다.
> 방법: GitHub 원격 소스 열람 + 경로/문자열 기반 정적 일관성 검사(12건, PASS 7 / FAIL 5). ROS 2·Gazebo 실행, colcon build, pytest, GUI, 실제 운동/오차 측정은 이 실행 환경에서 **수행하지 못함**. 정적 PASS를 동작 PASS로 해석하지 않는다.
> 이 브랜치는 문서만 추가하며 원본 코드를 수정하지 않는다. 5.1~5.6절 브랜치는 모두 동일한 main 기준 독립 PR 대상이다.

## 1. 실제 구현 분석
- joint_state_listener.py는 /joint_states의 sensor_msgs/msg/JointState를 구독하고 joint2의 name 인덱스를 찾아 position(rad/deg)과 velocity(rad/s)를 출력한다.
- setup.py에 joint_listener 엔트리포인트가 존재한다. 이름 기반 인덱싱 자체는 위치 순서 변동에 견고하다.
- 실제 코드에는 try/except ValueError로 타깃 이름 누락만 처리한다.

## 2. 발견사항
| ID | 심각도 | 근거 | 영향 / 권고 |
|---|---|---|---|
| C05-15 | MEDIUM | msg.name에 joint2가 있어도 msg.position 길이가 부족하면 position[index] IndexError | 잘못된 또는 부분 데이터 입력 때 콜백 예외. 배열 길이 검사 추가 |
| C05-16 | MEDIUM | msg.velocity가 비어 있는지만 검사, 길이가 index보다 짧으면 velocity[index] IndexError | velocity가 없거나 짧은 경우를 구분해 안전하게 처리 |
| C05-17 | LOW | 메시지 수신마다 get_logger().info | 100Hz 발행 환경에서 과도한 콘솔 I/O. 주기 조절 또는 throttle |
| C05-18 | MEDIUM | 본문: effort가 언제나 모터 토크라고 설명 | JointState effort는 비어 있거나 구현별 값을 제공할 수 있음. 시뮬레이터/하드웨어 구현별 의미 확인 |
| C05-19 | MEDIUM | 원고의 rqt_plot /joint_states/position[0]과 joint2 고정 비교 | 메시지 배열 순서와 target joint를 일치시키지 않으면 잘못된 관절을 그림 |

## 3. 검사 기록
- TC08 배열 경계 검사 FAIL. 전체 정적 교차 검사는 7 PASS / 5 FAIL(장 전체 기준).
- 코드 구조 검토는 완료했으나, pytest, 실제 /joint_states의 timestamp/Hz, 잘못된 길이 메시지 주입 테스트, rqt_plot GUI는 수행하지 못함.
- 추가 단위 테스트: (A) joint2 누락, (B) name에 존재하고 position 비어 있음, (C) velocity 짧음, (D) name 순서 교환, (E) 정상 rad→deg, (F) 수신 100Hz에서 로그 throttle.

## 4. 승인 기준
1. 필수 position에 없는 인덱스는 안전하게 스킵하고 경고를 throttle해 기록.
2. velocity 누락/짧음은 None 또는 미수신으로 구분해 0.0이라는 물리적 측정치로 오인하지 않게 표현.
3. ros2 topic echo /joint_states --once, ros2 topic hz /joint_states, listener 출력, 제어기 목표를 함께 저장.
4. index=0이 joint1이라고 전제하기 전에 name 배열 확인.

**판정: BASIC SOURCE STRUCTURE PASS / MALFORMED MESSAGE HANDLING FAIL / RUNTIME NOT VERIFIED.**

---
대응 실습: [LAB_5_4_GUIDE_KO.md](LAB_5_4_GUIDE_KO.md)
