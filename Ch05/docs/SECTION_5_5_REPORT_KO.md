# 5.5절 코드 리뷰 — RViz2와 Gazebo 로봇 상태 시각화

> 기준: 2026-10-20 KST, main @ 1b9e8215e2130c492969bb0da52a82e707c3a16f.
> 범위: 원고 5장 및 Ch05/ros2_ws/src/manipulation_basics. ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic을 목표 환경으로 한다.
> 방법: GitHub 원격 소스 열람 + 경로/문자열 기반 정적 일관성 검사(12건, PASS 7 / FAIL 5). ROS 2·Gazebo 실행, colcon build, pytest, GUI, 실제 운동/오차 측정은 이 실행 환경에서 **수행하지 못함**. 정적 PASS를 동작 PASS로 해석하지 않는다.
> 이 브랜치는 문서만 추가하며 원본 코드를 수정하지 않는다. 5.1~5.6절 브랜치는 모두 동일한 main 기준 독립 PR 대상이다.

## 1. 코드 확인
- rviz/manipulation.rviz가 존재하고 setup.py에서 rviz/*.rviz를 설치한다(TC04 PASS).
- 파일은 Fixed Frame=base_link, RobotModel Description Topic=/robot_description, TF display 활성화를 포함한다(TC11 PASS).
- launch는 rviz2를 -d 옵션으로 실행하며 RViz와 robot_state_publisher에 use_sim_time True를 설정했다.
- URDF에는 world_to_base_joint가 fixed로 선언돼 있다. RViz의 TF는 /joint_states와 URDF 구조를 기반으로 계산된다.

## 2. 발견사항
| ID | 심각도 | 근거 | 영향 / 권고 |
|---|---|---|---|
| C05-20 | MEDIUM | setup.py에는 rviz 설치 설정 있으나 패키지 의존성 rviz2 미명시 | clean install에서 rviz2 실행 실패 가능 |
| C05-21 | HIGH(교육 정확성) | 원고가 'Gazebo 로봇이 벽에 부딪혀 튕기면 RViz도 똑같이 튕긴다'고 서술 | 실제 모델은 world->base fixed이며 RViz는 충돌·접촉을 직접 렌더링하지 않음. 실시간 관절 자세 미러링과 물리 반동/베이스 동작을 구분 |
| C05-22 | MEDIUM | RViz Fixed Frame base_link | 관절 상대 자세에는 유효하지만 월드 기준 로봇 위치 확인에는 world/map과 변환 상태가 필요. base_link 프레임 기준 표시의 제한 설명 |
| C05-23 | MEDIUM | 원고의 rviz 폴더 생성 경로는 package 루트가 아닌 Python 모듈 하위 경로 | setup.py glob('rviz/*.rviz')로 해당 파일 설치되지 않음. 저장소의 패키지 루트 rviz 사용 |
| C05-24 | MEDIUM | 원고: source install/setup.ros2 launch ... | 정상 명령 2개로 분리해야 함 |

## 3. 검증 상태 및 재현
- 정적 TC04, TC11 PASS. GUI 화면 로드, TF 지연/드리프트, Gazebo vs RViz 관절 동작 비교는 **미수행**.
- 실행 시 필수: /robot_description이 존재하고, /joint_states가 갱신되며, ros2 run tf2_ros tf2_echo base_link link4가 정상적으로 변화를 출력하는지 확인.
- 체크리스트: RobotModel Status=OK, TF Status=OK, 각 관절 연속 운동 시 RViz/Gazebo의 관절 방향 일치, Fixed Frame 변경 전후 시각 차이.

## 4. 개선·승인 기준
1. 원고의 RViz 생성 위치와 설치 경로를 실제 패키지 구조로 정정한다.
2. '디지털 트윈' 대신 본 절의 측정 가능 범위(URDF 링크와 측정 관절각의 동기화)를 정확히 서술한다.
3. Gazebo 베이스 월드 자세를 RViz에 반영하려면 적절한 odom/world TF 입력이 추가로 필요할 수 있음을 설명한다.
4. 캡처 이미지보다 TF/토픽 정상성과 양방향 자세 비교 기록을 남긴다.

**판정: CONFIGURATION STATIC PASS / GUI·TF RUNTIME NOT VERIFIED / 원고 개선 필요.**

---
대응 실습: [LAB_5_5_GUIDE_KO.md](LAB_5_5_GUIDE_KO.md)
