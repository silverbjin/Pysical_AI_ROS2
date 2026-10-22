# 5.6절 코드 리뷰 — Hello Robot 사인파 궤적 프로젝트

> 기준: 2026-10-20 KST, main @ 1b9e8215e2130c492969bb0da52a82e707c3a16f.
> 범위: 원고 5장 및 Ch05/ros2_ws/src/manipulation_basics. ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic을 목표 환경으로 한다.
> 방법: GitHub 원격 소스 열람 + 경로/문자열 기반 정적 일관성 검사(12건, PASS 7 / FAIL 5). ROS 2·Gazebo 실행, colcon build, pytest, GUI, 실제 운동/오차 측정은 이 실행 환경에서 **수행하지 못함**. 정적 PASS를 동작 PASS로 해석하지 않는다.
> 이 브랜치는 문서만 추가하며 원본 코드를 수정하지 않는다. 5.1~5.6절 브랜치는 모두 동일한 main 기준 독립 PR 대상이다.

## 1. 실제 구현과 수학
- wave_hello_node.py는 /arm_controller/joint_trajectory로 50Hz(0.02초)마다 목표를 publish하고 매 점 time_from_start=0.02초를 설정한다.
- joint1 목표=0.3 sin(1.0t) rad, joint4 목표=0.5 sin(4.0t) rad, joint2=-0.5rad, joint3=0.8rad. omega는 **rad/s**이며 주파수 Hz가 아니다.
- 이상적 주기: joint1=2π/1≈6.28초, joint4=2π/4≈1.57초. 목표 각속도 최대값: joint1 0.3rad/s, joint4 2.0rad/s.
- URDF joint4 velocity limit=2.0rad/s로 정점 수준까지 요구하므로 샘플링/추종과 여유를 점검해야 한다.

## 2. 발견사항
| ID | 심각도 | 근거 | 영향 / 권고 |
|---|---|---|---|
| C05-25 | HIGH | 노드 자체에 use_sim_time=True 설정/선언 없음. get_clock() 호출만으로 시뮬레이션 시계가 사용되는 것은 아님(TC06 FAIL) | Gazebo /clock과 ROS 노드 시간 불일치. 최소 실행 옵션 --ros-args -p use_sim_time:=true 필요; 시계 수신 후 시작 |
| C05-26 | HIGH | 첫 메시지부터 joint2=-0.5, joint3=0.8을 0.02초 지점으로 명령 | 갑작스런 목표 변경·큰 요구 속도, 추종 오차/불안정 위험. 먼저 안전한 초기 자세로 충분한 시간 이동 후 wave |
| C05-27 | HIGH | 목표를 20ms마다 20ms 미래 시점으로 새로 발행 | 짧은 horizon에서 trajectory 교체·지연·지터가 생길 수 있음. multi-point 궤적 또는 충분한 look-ahead와 모션 프로파일 비교 |
| C05-28 | MEDIUM | joint4의 요구 각속도 최대 2.0rad/s, 모델 limit도 2.0 | 속도 상한에 여유 없음. 실습 시작 시 amplitude 또는 omega 하향 |
| C05-29 | MEDIUM | 종료 시 모터 정지/안전 자세 전환 동작이 없음 | Ctrl+C 시 제어기는 마지막 setpoint를 유지할 수 있음. 종료 동작/정지 시나리오 검증 |
| C05-30 | MEDIUM | 원고 코드의 time.time() 및 위상차 -0.5는 실제 저장소 코드와 다름 | 실제 구현은 ROS clock 및 위상차 미적용. 그래프 설명과 원고를 수정해야 함 |

## 3. 검증 상태
- 정적: wave_hello entry point 존재(TC01 유사 검사), TC06 FAIL. 수학 식·수치·URDF limit를 수동 교차 검토.
- 미수행: 컨트롤러 실수신, 주기/지터, joint_states 추종, 속도 포화, Gazebo 물리 안정성, RViz 연동.
- 테스트 프로토콜: 우선 /clock 수신 확인 → arm_controller active → simple_controller 중지 → wave_hello를 use_sim_time:=true로 실행 → 조인트 이름 매핑 확인 후 그래프 저장.

## 4. 권장 개선·승인 기준
1. clock을 포함한 시작/재시작(시뮬레이션 pause/시간 reset) 테스트 작성.
2. 인사 전 2~3초 안전한 시작 자세 이행; 그 뒤 진폭/속도/jerk 한도를 가진 파형 적용.
3. 파형의 목표값과 /joint_states 실측을 동일 시각축으로 기록, 오차·주기·타이밍을 계량적으로 판정.
4. 실제 하드웨어에서 본 예제 실행 금지(별도의 속도·토크·충돌 제한 검증 전까지).

**판정: SINE GENERATION STATIC REVIEWED / CLOCK CONFIG FAIL / MOTION NOT VERIFIED.**

---
대응 실습: [LAB_5_6_GUIDE_KO.md](LAB_5_6_GUIDE_KO.md)
