# SECTION 3.6 — 브리지 설정 수정·정적 테스트 보고서 (2026-10-21)

- 브랜치: `feat/ch03-section-3-6`, 기존 `SECTION_3_6_REPORT_KO.md` 후속.
- 수정: 소비하는 Gazebo 시스템이 없는 `cmd_vel` 경로를 **실제 YAML 매핑에서 제거**(주석으로 학습용 예시만 유지). 불필요한 토픽 브리지가 작동할 뿐 로봇이 움직일 것처럼 보이는 오해를 방지. 브리지 노드에 `ch03_parameter_bridge` 이름 부여.
- 유지 계약: Gazebo→ROS `/clock`, `/joint_states` 2개; ROS→Gazebo `/joint1/cmd_pos`, `/joint2/cmd_pos` 2개; `/tf` 직접 브리지 없음.
- 수행한 원격 소스 정적 검사 **8/8 PASS** (four_active_bridge_entries, no_unused_cmdvel, gz_clock_only, tf_not_mapped, joint1_ros_to_gz, joint2_ros_to_gz, bridge_param, named_bridge).
- Python `Ch03/tests/test_section_3_6_static.py` 작성. **Python unittest NOT_RUN**; ROS bridge/RMW/QoS 통신 및 Gazebo 동작 **NOT_RUN**.
- 재현: 저장소 루트에서 `python3 -m unittest discover -s Ch03/tests -p 'test_section_3_6_static.py' -v`. 패키지 빌드 후 `ros2 launch my_robot_description bridge.launch.py`, `ros2 topic info /clock -v`와 컨트롤러 플러그인 상태 확인.
- 경고: 파일에 토픽 매핑이 존재하는 것은 브리지와 실제 모델 플러그인이 연결되었다는 증거가 아니다. `RUNTIME_PASS/TASK_PASS` 미판정.
