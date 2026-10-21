# SECTION 6.3 — 모델·Setup Assistant 구성 수정 및 정적 테스트 보고서

- 브랜치: `feat/ch06-section-6-3` (기존 리뷰·실습 가이드 보존).
- 변경 파일: `config/my_robot.urdf.xacro`(중복 world 링크 및 world_to_base_joint 제거), `config/my_robot.srdf`(arm group에서 virtual_joint 항목 제거; 독립된 SRDF virtual_joint는 유지), `launch/demo.launch.py`(설치되는 `config/my_robot.urdf.xacro`를 명시적으로 로드).
- 추가 정적 계약 검사: `Ch06/scripts/audit_model_contract.py`. 표준 라이브러리 ElementTree로 URDF·SRDF XML 루트, world 중복, 하나의 SRDF virtual joint, arm group/말단 링크 확인.
- 신규 회귀 테스트: `Ch06/tests/test_section_6_3.py` 정상·world 이중 정의·arm group virtual joint 포함·가상 조인트 누락 4사례.
- 실제 수행된 검사: 원격 소스의 정확한 대상 패턴 유일성, 수정 후 필수 구문, 리그레션 테스트 4개 정의에 대한 정적 PASS.
- 실행 명령:
  ```bash
  python3 -m py_compile Ch06/scripts/audit_model_contract.py Ch06/tests/test_section_6_3.py
  python3 Ch06/scripts/audit_model_contract.py
  python3 -m unittest discover -s Ch06/tests -p test_section_6_3.py -v
  source /opt/ros/jazzy/setup.bash
  cd Ch06/ros2_ws && colcon build --symlink-install --packages-up-to my_robot_moveit_config
  source install/setup.bash
  ros2 launch my_robot_moveit_config demo.launch.py
  ```
- CPython 구문·unittest·colcon·RViz 실제 실행: **NOT_RUN**. 따라서 본 문서는 ROS 런타임 PASS를 주장하지 않는다.
- 미해결: `ros2_controllers.yaml` gripper action / `moveit_controllers.yaml` 복수 관절 계약 차이 및 gazebo 실제 조인트 제어기; 6.6 연동에서 별도 점검.
- PR 병합 영향: 6.4·6.5절은 각자의 branch에서 description URDF를 직접 참조하므로 개별 적용 가능. 후속 병합 시 두 URDF의 joint/link 정의는 동일하게 유지할 것.
