# SECTION 3.4 — SDF 환경 수정·정적 테스트 보고서 (2026-10-21)

- 브랜치: `feat/ch03-section-3-4`; 대상 `worlds/my_world.sdf`; 선행 리뷰 `SECTION_3_4_REPORT_KO.md`.
- 변경: 기본값에 암묵적으로 의존하지 않도록 world gravity=`0 0 -9.80665` m/s² 명시. 1ms 물리 스텝을 실측 RTF/화면 FPS와 혼동하는 주석 정정.
- 수행한 GitHub HEAD 소스 텍스트 계약 검사: **7/7 PASS** (xml_sdf, world, gravity, timestep, physics, user_commands, ground_static).
- XML 구조·physics·gravity·static ground를 검증하는 `Ch03/tests/test_section_3_4_static.py` 추가; **Python unittest NOT_RUN**, `gz sdf -k` / `gz sim` / GUI / 물리 실측 **NOT_RUN**.
- 재현: `python3 -m unittest discover -s Ch03/tests -p 'test_section_3_4_static.py' -v`; Gazebo 설치 환경은 `gz sdf -k Ch03/ros2_ws/src/my_robot_description/worlds/my_world.sdf` 후 `gz sim -r ...` 확인.
- 물리 목표 값과 실제 실행 주기는 구분하며, `RUNTIME_PASS`는 증거 확보 전 선언하지 않음.
