# 6.3절 코드 리뷰 — Setup Assistant·설정 패키지

> 기준: 2026-10-20 KST · GitHub main 1b9e8215e213 · 원고 6.3절 · ROS 2 Jazzy / Ubuntu 24.04 기준
> 범위: 저장소 소스 및 원고 정적 검토. 현재 세션에 ROS 2/Gazebo 실행 환경이 없으므로 실제 빌드·GUI·물리 시뮬레이션 결과는 **미검증**이다. 성공·PASS를 추정하지 않는다.
> 검토 대상: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 대상
`Ch06/ros2_ws/src/my_robot_description/urdf/my_robot.urdf.xacro`, `my_robot_moveit_config/{config,launch,CMakeLists.txt,package.xml}`. 원고의 `wrist_3_link`, `finger_joint1`, `joint6` 등은 예시이지만 실제 모델 이름처럼 지시하는 구간이 있다.

## 주요 문제
| ID | 수준 | 증거와 조치 |
|---|---|---|
| IK63-01 | HIGH | 실제 말단 링크는 `link_wrist`, gripper 관절은 `joint_finger1/2`. 원고의 `wrist_3_link`, `finger_joint1/2`는 실제 SRDF·URDF에 없다. 실습 단계의 명칭을 현 저장소 기준으로 수정한다. |
| IK63-02 | HIGH | MoveIt config `config/my_robot.urdf.xacro`는 world 링크 및 fixed `world_to_base_joint`를 포함하지만 SRDF에도 `world -> base_link` virtual joint가 있다. 동일 기준좌표 모델을 하나로 정하고 루트/TF 중복을 조사한다. |
| IK63-03 | HIGH | `CMakeLists.txt`는 `config`와 `launch`만 설치. `hello_moveit.py` 등은 config package의 `urdf/my_robot.urdf(.xacro)`를 요청하므로 설치본에는 해당 경로가 존재하지 않아 로딩 실패 위험. **6.4에서 먼저 수정 필요.** |
| IK63-04 | HIGH | `my_robot_moveit_config/config/ros2_controllers.yaml`의 그리퍼는 단일 `joint`를 갖는 그리퍼 액션 타입인 반면 `moveit_controllers.yaml`은 GripperCommand에 두 관절을 기재. 실제 액션 인터페이스와 조인트 계약 불일치 가능. |
| IK63-05 | MEDIUM | `arm_group`가 virtual_joint와 5축 chain을 함께 나열. group 정의의 불필요한 중복/플러그인 호환성을 검토하고 실제 사용되는 active joints를 확인. |
| IK63-06 | MEDIUM | Setup Assistant에서 self-collision 자동 제외는 충돌 안전 보증이 아님. `reason=Never` 쌍은 샘플링 빈도 및 모델로 재검토 필요. |

## 검증/승인 조건
- `xacro` 생성→`check_urdf` 통과; `urdf_to_graphiz` 또는 TF tree로 루트 하나 확인.
- 설치본 `ros2 pkg prefix my_robot_moveit_config` 아래의 설정·모델 경로 존재 확인.
- `arm_group`, `gripper_group`, SRDF named `home/ready` 유효성 확인.
- `ros2 control list_controllers` / `ros2 action list`로 그리퍼 액션·조인트 매핑 교차검증.

**판정: GUI 설정 따라하기는 가능하나 이름/루트/설치 경로/그리퍼 계약 문제로 완성 패키지 정상 구동을 보장할 수 없음. 실 구동 미검증.**
