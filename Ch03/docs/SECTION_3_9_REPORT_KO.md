# SECTION 3.9 — 키보드 텔레오퍼레이션 리뷰·수정 보고서

- 원고: 3.9.1~3.9.3 (토픽 흐름, Linux raw-mode, `setup.py` entry point, 실행)
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20 KST
- 대상: `my_robot_description/simple_arm_teleop.py`
- 결론: **정적 제어 경계 및 터미널 처리 보완 완료 / 실제 키 입력·Gazebo 관절 응답 미검증**

## 발견·수정
| ID | 심각도 | 발견 | 개선 |
|---|---|---|---|
| 3.9-01 | High | 비대화형 stdin에서 `termios.tcgetattr` 예외가 객체 생성 중 발생하고 `rclpy.shutdown` 전에 빠질 수 있음 | `isatty` 검사, `node=None` 초기화, 전체 생성/루프 `try/finally` |
| 3.9-02 | Medium | `get_key`의 raw-mode 복구는 select/read 예외 시 건너뛰어 터미널 깨짐 위험 | `get_key` 내부 `try/finally`에서 항상 복원 |
| 3.9-03 | Medium | 원래 코드의 `except Exception: print(e)`는 오류를 숨기고 정상처럼 종료할 수 있음 | 예외는 숨기지 않되 `finally`가 TTY/RCLPY 자원을 정리 |
| 3.9-04 | Medium | 0.1초 polling마다 불필요한 동일 위치를 재전송(최대 약 10Hz) | 유효 키 처리 시만 명령 publish, 시작 시 0 rad 한 번 발행 |
| 3.9-05 | Low | 도움말 W/S/A/D 대문자, 실제 코드는 소문자만 처리 | `.lower()`로 대소문자 동시 지원 |
| 3.9-06 | Medium | 원고 일부 경로는 `/model/my_robot/joint/joint1/cmd_pos`를 사용하나 **실제 YAML과 소스는** ROS `/joint1/cmd_pos` | 실행 명령/데이터 흐름은 현재 코드와 bridge 설정을 SSOT로 사용 |
| 3.9-07 | Info | `JOINT1_LIMIT=±1.57`은 URDF joint1의 ±3.14보다 좁음 | 보수적 소프트웨어 한계로 유지, joint2와 단위 rad 설명 |

## 실제 소스 계약
`setup.py`에는 `simple_arm_teleop = my_robot_description.simple_arm_teleop:main` 진입점이 이미 등록되어 있어 **중복 등록 불필요**. ROS 토픽 타입은 양 관절 모두 `std_msgs/msg/Float64`. 주요 입력 w/s→joint1, a/d→joint2, q 및 Ctrl+C 종료이다. 모터의 물리 피드백은 발행 노드가 아닌 Gazebo 및 `/joint_states`로 확인해야 한다.

## 검증
- **PASS(정적)**: 명령 두 토픽·Float64 대응, clamp, 단위 rad, TTY 초기화 가드, `try/finally` 복구, 이미 존재하는 entry point 확인.
- **NOT RUN**: `python3 -m compileall`, ROS 2 프로세스·키보드 TTY·Gazebo PID 응답. 현재 환경에서는 TTY/ROS2/Gazebo를 실행할 수 없다.

## 재현
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
python3 -m compileall -q src/my_robot_description/my_robot_description/simple_arm_teleop.py
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
# A: ros2 launch my_robot_description spawn_robot.launch.py
# B: 반드시 상호작용 가능한 일반 터미널에서
ros2 run my_robot_description simple_arm_teleop
```
B에서 w,w,a,d,s,q를 누르고 ROS 관절 상태 및 TTY 복구(`stty -a`)를 기록한다. 비TTY로 리디렉션할 경우 명확한 예외와 깨끗한 ROS 종료가 기대되지만 실제 검증은 필요하다.

## PR 의존성·Acceptance
3.9 제어 토픽이 실제로 연결되려면 3.6 브리지와 3.8 controller, 3.7 spawn, 3.3 Xacro 수정이 필요. 해당 PR을 병합한 통합 브랜치에서 키 입력→브리지→모터→`/joint_states` 전체를 확인 후 PASS. 현재 `PENDING_RUNTIME_VERIFICATION`.
