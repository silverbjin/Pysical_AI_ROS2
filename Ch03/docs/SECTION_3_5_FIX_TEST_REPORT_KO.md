# SECTION 3.5 — 충돌체·관성 정합성 수정 및 테스트 (2026-10-21)

- 대상: `urdf/two_dof_arm.urdf`; 브랜치 `feat/ch03-section-3-5`; 기존 `SECTION_3_5_REPORT_KO.md` 보완.
- 오류: link1 visual은 폭 0.05m box지만 collision은 **반지름 0.05m의 원통**이라 충돌 직경이 폭의 2배. 링크1 collision을 동일 크기 **box 0.05×0.05×0.5m**로 변경.
- 두 링크의 균질 box 관성 근사를 `Ixx=Iyy=0.0210416667`, `Izz=0.0004166667` kg·m²로 통일(질량 1kg). **실측 관성값 아님**.
- 실행된 소스 정적 계약 검사: **5/5 PASS** (collision_box, no_oversized_collision, link_inertia, link_izz, two_revolute).
- XML 형상 크기·관성 근사를 확인하는 `Ch03/tests/test_section_3_5_static.py` 추가. Python unittest **NOT_RUN**, Gazebo 충돌/접촉 **NOT_RUN**.
- 주의: 3.5 브랜치는 3.2 패치를 포함하지 않아서 link1 **visual rpy 불일치가 여전히 남아 있음**. 3.2 PR 병합 후 visual/collision *위치·방향*까지 일치하는지 통합 검증해야 한다. 3.3 Xacro는 별도 모델이므로 3.3의 관성 보정도 함께 필요.
- 재현: `python3 -m unittest discover -s Ch03/tests -p 'test_section_3_5_static.py' -v`; `check_urdf Ch03/ros2_ws/src/my_robot_description/urdf/two_dof_arm.urdf`.
- RUNTIME/TASK_PASS: **NOT_RUN**.
