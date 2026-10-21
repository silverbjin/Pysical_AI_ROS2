# 6.4절 코드 리뷰 — MoveItPy 목표 자세 제어

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.4절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 실제 코드
`Ch06/ros2_ws/src/my_robot_control/my_robot_control/hello_moveit.py`, `setup.py`, `package.xml`, `my_robot_moveit_config/CMakeLists.txt`, SRDF/YAML. 원고 6.4절 예제의 `home`/좌표 (0.3,0,0.4)는 저장소 실행본과 다르다.

## 차단/결함
| ID | 심각도 | 사실 및 영향 | 최소 조치 |
|---|---|---|---|
| IK64-01 | BLOCKER | `hello_moveit.py`의 `.robot_description(file_path="urdf/my_robot.urdf")` 요청. `my_robot_moveit_config/CMakeLists.txt`는 `config`와 `launch`만 install하며 `urdf`는 미설치. 로봇 모델 로드 실패 위험. | 존재하는 `config/my_robot.urdf.xacro`를 신중하게 선택하거나 description 패키지의 실제 설치된 모델을 절대 경로로 참조. 루트 중복도 함께 점검. |
| IK64-02 | HIGH | `setup.py`가 등록한 CLI는 `hello_node`이지만 원고는 `ros2 run my_robot_control hello_moveit.py` 또는 `hello_moveit`이라고 지시. | 실행 명령을 `ros2 run my_robot_control hello_node`로 통일하거나 새 entry point 명시. |
| IK64-03 | HIGH | 실제 Task 1 named state는 `ready`, 원고는 `home`; Task 2 목표는 `(0,0,2.1)`과 identity orientation. 원고의 `(0.3,0,0.4)`와 다르며, 5축 팔의 전체 6D 포즈·특이자세·충돌 등으로 계획 실패 가능. | 실제 reachable 목표를 FK/충돌로 검증하고 시작/목표 state를 구분. |
| IK64-04 | HIGH | `my_robot.execute(...)` 뒤에 실행 반환 상태를 확인하지 않고 `Execution Success`를 출력. 마지막에 `os._exit(0)`로 프로세스 강제 종료. | 실행 상태 검증, `try/finally` 정리 및 정상 종료·종료코드 전파. |
| IK64-05 | MEDIUM | `time.sleep(2)`로 노드·컨트롤러 준비를 추정. MoveItPy의 시간/현재 상태/액션 서버 readiness를 검사하지 않음. | `/joint_states`, `/clock`, action readiness 및 timeout 기반 게이트 도입. |
| IK64-06 | MEDIUM | `moveit_client.py`는 `planning_pipelines` 매핑을 중간에 리스트로 덮어씀. `moveit_direct_node.py`는 `rclpy.init` 후 `sys.argv`에 파라미터를 덧붙여 초기화 해결을 시도. | 실습의 기준 예제를 하나로 정하고 실험성 대안은 별도 파일·주석으로 구분. |

## 원고와 코드 정합
원고의 `wrist_3_link`는 실제 SRDF의 `link_wrist`가 아니다. 실습상 '목표 포즈 → IK → plan → action 실행'을 별개 성공 기준으로 기록한다. `Plan Success`는 컨트롤러의 실행 성공을 뜻하지 않는다.

## 검증 게이트
1. Xacro 및 설치 경로, SRDF/URDF root, 5축 IK 목표 검증.
2. `ros2 pkg executables my_robot_control` 결과가 `hello_node`를 포함.
3. Named pose는 planning & execution 각 결과/시간 확인; 6D pose는 실제 FK 오차·충돌상태 포함.
4. 정상·의도적 실패에서 exit code 0과 경고만 나오지 않는지 테스트.

**판정: BLOCKED (현재 그대로 성공 실습을 보장할 수 없음). 코드 수정·실행 재검증 후 완료 처리.**
