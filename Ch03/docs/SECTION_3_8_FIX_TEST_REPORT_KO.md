# SECTION 3.8 — 관절 제어 안전 설정·정적 테스트 보고서 (2026-10-21)

- 브랜치: `feat/ch03-section-3-8`; 대상 `urdf/two_dof_arm.urdf.xacro`; 선행 `SECTION_3_8_REPORT_KO.md`.
- 수정: 2개 회전 관절에 `damping=0.1`, `friction=0.05`를 선언하여 3.2 정적 URDF의 동역학 명세와 정합성을 높임. `JointPositionController` joint1의 `cmd_min/max`를 ±100으로 제한(이전 ±1000, URDF `effort=100`). 이전 50Hz JointStatePublisher 패치 유지.
- **주의**: `cmd_min/max`는 플러그인 명령 제한 설정이지, 실제 물리 구동 시 절대적 안전보장이나 검증된 PID 튜닝을 뜻하지 않음. 관절별 힘·속도·각도, 베이스 이동/낙하, 시뮬레이션 안정성은 검증 필요.
- 실행된 GitHub 소스 정적 계약 검사: **8/8 PASS** (rate_50, two_controllers, two_dynamics, joint1, joint2, no_1000_cmd_limit, joint1_effort_cap, joint1_negative_cap).
- Python `Ch03/tests/test_section_3_8_static.py` 추가. Python `unittest` **NOT_RUN**; Xacro 전처리, Gazebo 시스템 로딩, 실제 joint command 수렴·모터 하중 **NOT_RUN**.
- 재현: `python3 -m unittest discover -s Ch03/tests -p 'test_section_3_8_static.py' -v` 및 `xacro urdf/two_dof_arm.urdf.xacro > /tmp/ch03_3_8.urdf`. ROS-Gazebo 통합 시에는 3.3 관성 모델 및 3.6 YAML 병합 상태를 먼저 확인.
- RUNTIME/TASK_PASS 미판정; 무단 실기기 적용 불가.
