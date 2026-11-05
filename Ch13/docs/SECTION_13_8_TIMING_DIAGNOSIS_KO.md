# 사전 파지 궤적의 시간 보정 분석

2026-11-05 KST. 단일 작업자. 제한값을 높이지 않고 불필요한 시간 보정을 줄이는 작업이다. 새 물리 실행 성공은 아직 확인하지 않았다.

## 실제 실패 원인

v19/UUID853f2592-ea9e-4567-ac7f-4d4aeabb4475는 비전3908회 수락/거부0회였지만 사전 파지 팔 action이240wall초를 넘겨 실패했다. native 기록은 시작wall86.007541→취소 ACK326.117113→ABORTED329.169920, 원인은wall_deadline이다. 이후 종료 과정의MISSION_EXPIRED를 최초 heartbeat 장애로 해석하지 않는다.

선택된 궤적은93.728sim초였다. 이번 실행 속도에서는 개별action의240wall초 안에 끝나지 못했다. 전체trial은114.82sim초/304.833wall초, 실제engine은116.854sim초/306.24wall초였다. 원본 FAIL과 정상 회수/공유lock 해제를 보존했다. 이 결과를 관측 조각 수정이나 내려놓기 정착 gate의 실제 실패로 쓰지 않는다. 해당 단계에는 도달하지 않았다.

## 원본 궤적을 이용한 최소 분석

기존 시간 보정기는 배율1.00,1.25,1.50,2.00,3.00 중 기존 연속 검증을 처음 통과하는 값을 골랐다. 원본 위치 waypoint는 보존하고 시간·속도·가속도를 함께 환산한다.

저장된 두 궤적에서1.00배가 실패한 원인은 quintic의 연속 가속도였다. 실제 제한0.1rad/s²에 대해0.104398과0.109915rad/s²가 검출됐다. 따라서 보정 자체는 필요하지만25%의 시간 증가 전체가 필요한 것은 아니다.

| 후보 | 원본 시간(sim초) | 기존1.25배(sim초) | 같은 연속 검증+1% 여유(sim초) |
|---|---:|---:|---:|
| 790점 후보 | 78.813 | 98.516 | 85.334 |
| 선택된751점 후보 | 74.982 | 93.728 | 79.413 |

이는 종료 후 같은 검증기로 계산한 결과이며 실제wall시간 보장은 아니다. 다른 부하에서는 실제 실행이 여전히 실패할 수 있다.

## 공식 자료와 적용 차이

[MoveIt2.12.4 TOTG 구현](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/trajectory_processing/src/time_optimal_trajectory_generation.cpp)은 위치 경로에 속도·가속도 한도를 적용해 시간을 정한다. [ros2_control Jazzy 궤적 설명](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/trajectory.html)은 위치·속도·가속도 입력의 quintic 보간과 연속성, 입력에 따른 overshoot를 설명한다. 따라서 waypoint 값만 확인하고 연속 구간의 제한을 생략하지 않는다.

이 프로젝트는 custom native 제어기와 기존 Trajectory.from_points 검증기를 유지한다. 새ros2_control controller나 다른TOTG API로 교체하지 않는다. 12회 구간 탐색과1% 여유는 이 프로젝트의 선택이며 공식 문서가 지정한 표준 수치라고 주장하지 않는다.

## 수정 범위와 검증

13.8의floor profile만 기존에 통과한 coarse 배율 구간 안에서12회 탐색한다. 통과한 상한에1% 여유를 더하되 원래 coarse 배율을 넘지 않고, 마지막에 같은 연속 검증을 다시 통과해야 한다. 시간 배율이 작아져도 위치 경로와 모든 waypoint는 같고, 속도는 시간 배율의 역수, 가속도는 역수의 제곱으로 환산된다.

원래0.05rad/s·0.1rad/s², 관절 범위, zero boundary derivatives,120sim/240wall 개별action,600sim mission, 원본 관측 수명, PD와 보행 정책은 유지한다. legacy/development는 기존 coarse 정책을 사용한다. 검증기가 거부한 위치 오류를 clamp하거나 경로점을 삭제하지 않는다. feasible coarse 구간이 없으면 새 방식도 거부한다.

실제751점 궤적을 고정 fixture로 보존했다. 새API 부재의2 FAIL을 확인한 뒤, 전체 waypoint 보존·31개 구간의 경로/미분 환산·동일 연속 제한·정상hold·잘못된 위치 거부와 기존TOTG 회귀를 함께 확인했다:5 PASS/4.34초,345 deselected. 전체 회귀·설치·동결·실제 재검증은 다음 결과로 별도 기록한다.

최종 전체350 PASS/53.98초. 시험 fixture가 생성자를 건너뛰며 새 초기값을 누락한 최초348 PASS/2 FAIL도 보존했다. 분리build16.6초·설치63모듈/94자산/actual child PASS, 실행 동결source359개가350시험 snapshot의source359개와전수hash동일PASS. 새 실제 미션은 별도UUID로 검증한다.
