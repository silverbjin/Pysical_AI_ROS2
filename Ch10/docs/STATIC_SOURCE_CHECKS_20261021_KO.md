# Ch10 원격 소스 정적 패턴 확인 기록 (2026-10-21 KST)

## 목적·범위

GitHub main 기준 (`bab76f6ca7df0bda6efd8882c1a698561707e51d`) Ch10의 Python, URDF/Xacro, 브리지 YAML, launch/setup 원문을 **읽기 전용으로 조회하여**, 리뷰에서 지적한 표현의 존재·부재가 사실인지 확인했다.

- 검사 방법: 12개 소스 파일의 텍스트에 대해 정확한 문자열 또는 정규식 기반의 **15개 구조적 패턴 비교**.
- 검사 결과: **15/15개 예상 소스 패턴 일치**. 이는 정상 동작 15개 PASS가 아니라, 리뷰에서 기술한 코드 상태가 소스와 일치했다는 뜻이다.
- 수행하지 않은 항목: `python -m compileall`, `colcon build`, `pytest`, ROS 메시지 교환, Gazebo Harmonic 시뮬레이션, 실제 보행·접지·회복 측정.
- 한계: 소스 패턴은 의미론적 동작을 전부 증명하지 않으며, 누락 문자열만으로 완전한 기능 부재를 단정하지 않는다. 이 기록은 실험 Evidence의 대체물이 아니다.

## 점검 결과 (MATCH=찾으려던 코드 표현이 실제 존재/부재 조건과 일치함)

| ID | 패턴 비교 결과 | 관련 절 | 의미 |
|---|---|---|---|
| C01 | MATCH — setup.py에 gait_planner:main 등록, gait_planner.py의 main() 없음 | 10.2 | 실행 entry point 실패 가능 |
| C02 | MATCH — GaitPlanner trot 위상배열 [0,0.5,0.5,0] 확인 | 10.2 | 대각선 리듬 구현의 부분 증거 |
| C03 | MATCH — TrajectoryGenerator.generate()에 0.5s, duty 0.5 고정 | 10.3 | 다른 gait와 주기 불일치 |
| C04 | MATCH — Xacro thigh_length=0.25m vs IK l2=0.20m | 10.4 | 기구학 위치 오차 위험 |
| C05 | MATCH — Xacro calf_length=0.25m vs IK l3=0.20m | 10.4 | 기구학 위치 오차 위험 |
| C06 | MATCH — Xacro thigh/calf joint rpy=+1.2/-2.4 | 10.4 | IK 영점/정운동학 대응 필요 |
| C07 | MATCH — FSM stance_time=1/(2*frequency) | 10.5~10.6 | crawl duty=0.75 미반영 |
| C08 | MATCH — 실행 FSM/ROS 통합 노드의 create_service 호출 없음 | 10.6 | SetGait.srv 선언만으로 호출 불가 |
| C09 | MATCH — 통합 노드가 /joint_states에 목표 JointState를 publish | 10.7 | 상태 측정/제어값 혼재 위험 |
| C10 | MATCH — 통합 노드에 ik_angles=self.default_stance 고정값 존재 | 10.7 | 명령이 IK 산출값 아님 |
| C11 | MATCH — step_freq 변경에서 planner 적용 코드 주석 처리 | 10.7 | 파라미터 성공과 실제 동작 불일치 |
| C12 | MATCH — ros_gz_bridge.yaml에 Float64 위치 명령 ROS_TO_GZ 12개 | 10.1·10.8 | 현행 실사용 명령 계약 |
| C13 | MATCH — test_gait_fsm.py에 4.0 > sim_time >= 4.2 조건 존재 | 10.5 | 실행 불가능한 분기 |
| C14 | MATCH — simulation.launch.py에 use_sim_time 명시 설정 없음 | 10.8 | 시각 기준 혼재 확인 필요 |
| C15 | MATCH — 통합 노드에 명시적인 cmd_vel_timeout/last_cmd_time 관리 없음 | 10.7 | 오래된 명령 지속 위험 |

## 후속 재현 요구

1. Git SHA와 설치 환경을 기록하고 ROS 2 Jazzy에서 Ch10만 `colcon build`.
2. 코드 가정과 URDF/FK/브리지 실제 모델을 통일한 다음 테스트를 추가한다.
3. 각 절의 단위 테스트에서 입력-출력 수치, 시간경계, 비정상 입력 사례를 검증한다.
4. Gazebo의 실측 각도·몸체 pose·접지·외란 결과로 10.8 시나리오를 평가한다.

**최종 범주:** STATIC SOURCE CHECK — 소스 정합 확인. RUNTIME / PHYSICS: NOT RUN.
