# 5.1절 코드 리뷰 — 매니퓰레이션 제어 개요와 패키지 준비

> 기준: 2026-10-20 KST, main @ 1b9e8215e2130c492969bb0da52a82e707c3a16f.
> 범위: 원고 5장 및 Ch05/ros2_ws/src/manipulation_basics. ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic을 목표 환경으로 한다.
> 방법: GitHub 원격 소스 열람 + 경로/문자열 기반 정적 일관성 검사(12건, PASS 7 / FAIL 5). ROS 2·Gazebo 실행, colcon build, pytest, GUI, 실제 운동/오차 측정은 이 실행 환경에서 **수행하지 못함**. 정적 PASS를 동작 PASS로 해석하지 않는다.
> 이 브랜치는 문서만 추가하며 원본 코드를 수정하지 않는다. 5.1~5.6절 브랜치는 모두 동일한 main 기준 독립 PR 대상이다.

## 1. 원고와 실제 소스 대조
- 실제 제어 패키지는 Ch05/ros2_ws/src/manipulation_basics이다. package.xml, setup.py, config/ros2_controllers.yaml, launch, urdf, rviz, 3개 Python 노드가 존재한다.
- 원고 5.1.4의 최초 폴더 예시는 simple_joint_controller.py가 맞으며, 뒤 절의 simple_trajectory_publisher.py는 실제 저장소에 **없다**.
- YAML의 arm_controller는 joint1~joint4, position 명령 인터페이스를 사용한다. URDF의 ros2_control joint1~joint4 선언과 텍스트상 일치한다(정적 TC02 PASS).
- YAML에 gripper_controller가 선언됐지만 실제 URDF에는 gripper_joint가 없고 launch에서 해당 제어기를 spawn하지 않는다(TC10 FAIL). 교육상 미사용 예제인지 제거할지 명시해야 한다.

## 2. 발견사항
| ID | 심각도 | 근거 | 영향 / 권고 |
|---|---|---|---|
| C05-01 | HIGH | package.xml에 ros_gz_bridge, xacro, robot_state_publisher, gz_ros2_control, rviz2, builtin_interfaces 등의 직접 런타임 의존성 명시 없음 | 개발 PC에는 우연히 설치돼 동작해도 깨끗한 환경에서는 실행 실패 가능. 실제 사용하는 패키지별 exec_depend 추가 |
| C05-02 | MEDIUM | package.xml version 0.0.1 / setup.py version 0.0.0 | 빌드 산출물 버전 불일치. 버전 동기화 |
| C05-03 | MEDIUM | gripper_controller 설정에 gripper_joint만 등장, 실제 URDF에 관절 없음 | 스포너를 활성화할 경우 실패 가능. 현재 실습에서 사용하지 않는다는 점 명시/설정 분리 |
| C05-04 | MEDIUM | test/에는 기본 lint 테스트만 있고 launch/YAML/조인트 대응 테스트 없음 | 수정 후 회귀 검출 불가. 교차 검증 테스트 추가 |

## 3. 정적 검사와 미검증
- TC01(PASS): setup.py의 simple_controller 엔트리포인트가 실제 simple_joint_controller.py의 main을 가리킴.
- TC02(PASS): YAML arm_controller와 ros2_control xacro 간 joint1~joint4 선언 일치.
- TC03(PASS): setup.py가 urdf/*.xacro를 설치함. TC04(PASS): rviz/*.rviz를 설치함.
- TC07(FAIL): package.xml에 ros_gz_bridge 명시 없음. TC10(FAIL): gripper_controller와 모델 관절 불일치.
- **미수행**: 의존성 설치 검증, colcon build, Gazebo 플러그인 로드, 노드 입출력 검증.

## 4. 개선 및 승인 기준
1. 실행에 필요한 의존성 목록을 정확히 명세하고 새 쉘에서 ros2 pkg prefix / ros2 pkg executables로 확인한다.
2. YAML에 선언한 제어기와 URDF 관절을 일치시키거나 그리퍼 항목을 미사용 예제로 분리한다.
3. 패키지 메타데이터와 원고의 파일명 불일치를 정리한다.
4. 5.2절에서 컨트롤러 2개 active 및 /joint_states 확인 전에는 **런타임 ACCEPT 판정 불가**.

**판정: STATIC REVIEW COMPLETE / RUNTIME NOT VERIFIED / 개선 필요.**

---
대응 실습: [LAB_5_1_GUIDE_KO.md](LAB_5_1_GUIDE_KO.md)
