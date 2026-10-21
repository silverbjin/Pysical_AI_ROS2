# Ch09 코드 변경 통합 정적 검사 보고서

- 일시: 2026-10-21 (KST)
- 소스 저장소: https://github.com/silverbjin/Pysical_AI_ROS2
- 통합 코드 브랜치: `fix/ch09-post-review-code-20261021`
- 시작 기준: `main@dbbca36f1b51a8beeb1731c9c3b5e3fa29e64c18` (기존 9.1~9.8 문서 PR #81, #82, #83, #84, #91, #92, #96, #98 병합 후)
- 이 보고서를 작성하기 전의 최종 9.8 커밋: `b55029b2ee294a333c55968eb80916040e637b36`
- 원본 코드 수정 보관소: `hold/ch09-section-9-N-code-fixes-20261021`
- **검증 등급: STATIC_REVIEWED / 정적 계약 검사 37 PASS · 0 FAIL / SCRIPT_SYNTAX_PASS (9.8) / BUILD, RUNTIME, TASK NOT_RUN**

## 1. 기존 문서 PR과 코드 PR의 분리

기존 8개 문서 PR은 사용자에 의해 `main`에 병합되었다. 이후 본 코드 브랜치를 현행 `main`에서 새로 만들었다. 이 브랜치에는 이전에 보관한 절별 실제 코드 변경과 `CHANGE_TEST_REPORT_KO.md` 보고서를 **9.1→9.8 순서의 독립 커밋**으로 적용했다. `main` 및 이미 병합된 문서 PR은 직접 수정하지 않았다.

| 절 | 복원 범위 |
|---|---|
| 9.1 | `leg.xacro` hip visual/collision/inertia 방향 |
| 9.2 | Ch09 RViz 경로, Xacro 설치 파일 필터 |
| 9.3 | thigh/calf 관성 원점 |
| 9.4 | Gazebo foot 마찰·접촉 XML 태그 |
| 9.5 | ROS sim time, Xacro string, `package.xml` 의존성 |
| 9.6 | stand_up 램프, ROS clock과 관절 제어권 |
| 9.7 | 단일 다리·트롯 미리보기의 12관절 단독 제어, 초기 ramp, clock |
| 9.8 | 독립 정적 검사 CLI와 절별 보고서 |

## 2. 통합 실코드 정적 계약 검사: 37/37 PASS

GitHub 연결을 통해 위 브랜치에 저장된 **실제 파일 콘텐츠를 읽어** JavaScript 정적 계약 어설션을 실행했다. XML 태그 균형 검사는 정식 XML/Xacro 파서가 아닌 간이 구조 검사이다.

1. PASS — XML tag balance: urdf/parts/leg.xacro
2. PASS — XML tag balance: urdf/robot.urdf.xacro
3. PASS — XML tag balance: urdf/common/robot_properties.xacro
4. PASS — XML tag balance: package.xml
5. PASS — 9.1 hip visual and collision along lateral Y
6. PASS — 9.1 hip geometry center reflects left/right
7. PASS — 9.1 hip inertia dimensions rotated consistently
8. PASS — 9.1 3 revolute hip/thigh/calf joints
9. PASS — 9.2 RViz uses Chapter 9 share
10. PASS — 9.2 setup filters .draft and intermediate Xacros
11. PASS — 9.2 setup keeps recursive Xacro installation
12. PASS — 9.3 thigh inertia matches length/2
13. PASS — 9.3 calf inertia matches length/2
14. PASS — 9.4 Gazebo friction values are XML element contents
15. PASS — 9.4 contact gains are XML contents
16. PASS — 9.4 controller 3 plugins retained
17. PASS — 9.5 declare use_sim_time true
18. PASS — 9.5 robot_state_publisher consumes launch sim clock
19. PASS — 9.5 alt launch passes typed robot XML string
20. PASS — 9.5 package.xml has ament_python build dependency
21. PASS — 9.5 package.xml declares required runtime dependencies
22. PASS — 9.6 nominal stand targets preserved
23. PASS — 9.6 ramp applied to all target joints
24. PASS — 9.6 time reset and ramp bounds
25. PASS — 9.6 explicit other-controller ownership exclusion
26. PASS — 9.7 exclusive publishers for each of 12 joints
27. PASS — 9.7 clock-derived trajectories in both nodes
28. PASS — 9.7 nominal pose in both control nodes
29. PASS — 9.7 right-front thigh exclusively oscillated in mover
30. PASS — 9.7 trot diagonal pairing and phase inversion
31. PASS — 9.8 all 4 leg Xacro calls
32. PASS — 9.8 nominal total mass 12kg
33. PASS — 9.8 bridge 12 active actuator routes
34. PASS — 9.8 all 12 ROS controller topics are bridge-mapped
35. PASS — 9.8 ROS controller topics avoid /0/ suffix
36. PASS — 9.8 verified Python audit matches local compiled Git SHA
37. PASS — 9.8 strict checks for all predecessor sections

## 3. Python 로컬 실행 테스트 — 독립 정적 감사 스크립트

GitHub 상의 `Ch09/scripts/check_ch09_static.py`를 정확히 복제하고 **Git blob SHA `2eaa1983801fdeebd455648120275441fdc8287c` 일치**를 확인하여 동일 코드임을 입증했다.

- `python3 -m py_compile`: **PASS** (독립 감사 스크립트에 한함).
- `--help`: **PASS**.
- 가상 패키지 **정상 fixture**를 `--strict --output`으로 검사: **32/32 PASS**, JSON evidence 생성됨.
- 필수 `display.launch.py`를 제거한 **부정 fixture**: 종료코드 1, `required:launch/display.launch.py` 실패 검출 **PASS**.
- **한계**: GitHub Ch09 전체 워크스페이스를 컨테이너에 다운로드할 수 없었으므로 실제 통합 브랜치를 대상으로 `check_ch09_static.py --strict`를 로컬에서 직접 실행하지는 못했다. 원격 실제 코드에 대한 통합 정적 계약 검사는 위 37건을 별도로 완료했다.

## 4. 실제 ROS 2/Gazebo 검증 — NOT_RUN

다음 절차는 로컬 Ubuntu 24.04 / ROS 2 Jazzy + Gazebo Harmonic에서 수행할 **예정 검증 명령**이다. 성공을 주장하지 않는다.

```bash
git fetch origin
git switch -c fix/ch09-check origin/fix/ch09-post-review-code-20261021
python3 Ch09/scripts/check_ch09_static.py --strict --output /tmp/ch09_static.json
source /opt/ros/jazzy/setup.bash
cd Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
ros2 launch my_quadruped_bot simulation.launch.py
```

Gazebo 시간과 TF, `/joint_states`, 각 제어 토픽 publisher 수, 기립 응답, 토크·마찰 및 실제 물리 안정성은 이 단계에서 별도 관측한다. **BUILD_PASS, RUNTIME_PASS, TASK_PASS는 부여하지 않는다.**

## 5. 채택 전 검토사항

1. 9.1·9.3·9.4는 공통 `leg.xacro`를 고치지만 본 통합 브랜치에서 세 수정이 누적·보존되었음을 정적 계약으로 확인했다.
2. 9.6·9.7의 제어 노드는 동일 액추에이터에 서로 다른 명령을 발행하지 않도록 한 번에 **하나만 실행**해야 한다. 순차적인 노드 종료·재시작을 권장한다.
3. 정적 코드 검증 결과는 Gazebo 보행 안정성·접촉 물리·제어 성능의 실측 근거가 아니다.
4. 이 통합 브랜치는 새 코드 PR을 만들기 위한 독립 산출물이며, 기존 문서 PR의 내용을 수정하거나 덮어쓰지 않는다.
