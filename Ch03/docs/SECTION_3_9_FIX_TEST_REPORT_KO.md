# SECTION 3.9 — 키보드 제어 안전성 수정·정적 테스트 보고서 (2026-10-21)

- 브랜치: `feat/ch03-section-3-9` (기존 브랜치, 강제 푸시 없음). 대상 `my_robot_description/simple_arm_teleop.py`; 선행 `SECTION_3_9_REPORT_KO.md`.
- **High:** 생성자에서 `termios.tcgetattr`를 ROS Node 구성보다 먼저 호출. TTY 속성을 읽을 수 없는 경우 ROS Node 리소스가 부분 생성되어 남는 위험을 줄임.
- **High:** 키보드 제어 시작 시 자동 0 rad 명령을 발행하지 않음. 현재 로봇 상태를 모르는 상황에서 무의도적 리포지셔닝을 방지.
- **Medium:** 키를 누른 관절에만 `std_msgs/msg/Float64` 명령을 발행하고 다른 관절은 그대로 둠. 각도 제한으로 목표가 바뀌지 않으면 명령을 반복 발행하지 않음.
- **Medium:** 터미널 복원 실패에도 `destroy_node` 및 `rclpy.shutdown`이 실행되도록 중첩 `try/finally` 처리.
- 실행된 원격 소스 정적 계약 검사 **10/10 PASS** (tty_guard, tty_before_ros_init, single_joint_publish, no_startup_zero_publish, clamp, no_duplicate_on_limit, nested_cleanup, shutdown, topic1, topic2).
- Python AST 및 ROS import 없는 clamp 테스트 `Ch03/tests/test_section_3_9_static.py` 작성. **Python unittest NOT_RUN**; 실제 키보드/ROS/Gazebo PID/모터 응답 **NOT_RUN**.
- 재현: 저장소 루트에서 `python3 -m unittest discover -s Ch03/tests -p 'test_section_3_9_static.py' -v`; ROS 설치 후 TTY에서 `ros2 run my_robot_description simple_arm_teleop` 실행하고 `w/s/a/d/q`와 `stty -a` 확인.
- 주의: 초기 관절 명령 목표는 0 rad에서 시작하는 **소프트웨어 상태**이며, 실제 관절 피드백을 읽지 않음. 첫 키 입력도 상태 차이에 따라 점프를 일으킬 수 있으므로 안전한 실기기 제어용으로 사용하지 않는다. 향후 `/joint_states`에서 실제 위치 초기화 및 watchdog/E-stop 보강 필요.
- `RUNTIME_PASS/TASK_PASS`: **NOT_RUN**.
