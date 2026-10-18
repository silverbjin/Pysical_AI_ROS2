# 13.2 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task and `superpowers:test-driven-development` before implementation.

**Goal:** Ch13 독립 패키지에서 12축 4족, 6축 팔, 2축 그리퍼를 모듈형 Xacro로 결합하고 Gazebo/MuJoCo backend의 ros2_control 구성을 검증한다.

**Spec:** `Ch13/docs/SECTION_13_2_DESIGN_KO.md`

## Global Constraints

- Ch05~Ch12 파일을 수정하지 않는다.
- 실행 배열과 controller 목록은 관절 이름을 기준으로 검증한다.
- 한 backend와 한 controller만 각 command interface를 소유한다.
- 실제 엔진 미실행을 정적 테스트 통과로 대체하지 않는다.

## Review Focus

- 18축이라는 원고 표현과 그리퍼 포함 20축 구현의 불일치가 문서·코드에서 명확한가.
- prefix가 링크·관절·controller 설정 전체에 일관되게 적용되는가.
- URDF의 축·한계·관성이 유효하고 TF가 단일 트리인가.
- backend 선택이 정확히 하나의 hardware plugin만 생성하는가.
- controllers가 20개 command interface를 중복 없이 완전히 나누는가.
- Gazebo와 MuJoCo 검증의 수준을 과장하지 않는가.

### Task 1: 패키지 골격과 실패하는 모델 계약 테스트

**Files:** `Ch13/tests/test_section_13_2_model.py`, `Ch13/ros2_ws/src/integrated_robot_description/{package.xml,CMakeLists.txt}`

- [ ] 20개 관절, prefix, 단일 루트, 관성, backend plugin, controller 소유권 테스트를 먼저 작성한다.
- [ ] 테스트를 실행해 모델 부재로 실패하는 것을 확인한다.
- [ ] 최소 패키지 골격을 만들고 설치 규칙을 추가한다.
- [ ] 커밋한다.

### Task 2: 모듈형 Xacro와 controller 구성

**Files:** `urdf/*.xacro`, `config/controllers.yaml`, `launch/view_robot.launch.py`, `rviz/robot_system.rviz`

- [ ] 재사용한 4족 구조와 축소 6DoF 팔·그리퍼를 각 매크로로 구현한다.
- [ ] 단일 ros2_control macro와 mock/gazebo/mujoco backend 선택을 구현한다.
- [ ] 테스트와 `xacro`, `check_urdf`를 통과시킨다.
- [ ] RViz launch의 안전한 기본값을 확인하고 커밋한다.

### Task 3: Gazebo 실제 통합

**Files:** `launch/gazebo.launch.py`, `worlds/empty.sdf`, `scripts/verify_gazebo_13_2.py`, tests/evidence

- [ ] Gazebo 검증 테스트를 먼저 작성한다.
- [ ] `gz_ros2_control` 한 인스턴스, controller spawner와 실제 서버 launch를 구현한다.
- [ ] 실제 Gazebo에서 controller 목록, joint state, 작은 arm 명령, base 유한성을 기록한다.
- [ ] 결과와 로그를 evidence에 남기고 커밋한다.

### Task 4: MuJoCo 모델과 ros2_control 통합 시도

**Files:** `mujoco/robot_system.xml`, `launch/mujoco.launch.py`, `scripts/verify_mujoco_13_2.py`, tests/evidence

- [ ] MJCF 20관절/actuator 및 이름 대응 테스트를 먼저 작성한다.
- [ ] native MuJoCo 실제 load/step 검증을 구현한다.
- [ ] 공식 `mujoco_ros2_control` 의존성을 소스 빌드하고 launch를 실행한다.
- [ ] 성공·실패와 원인을 구분해 증거로 남기고 커밋한다.

### Task 5: 문서, 재사용 명세와 최종 회귀

**Files:** `Ch13/docs/LAB_13_2_GUIDE_KO.md`, `REUSE_MANIFEST.md`, `SECTION_13_2_REPORT_KO.md`, evidence

- [ ] 설치·빌드·RViz·Gazebo·MuJoCo 단계별 가이드를 작성한다.
- [ ] 원본 경로, 기준 SHA, 새 경로, 변경 이유와 해시를 기록한다.
- [ ] 전체 테스트, clean colcon build, 엔진 검증, Ch05~Ch12 무변경을 새로 확인한다.
- [ ] 미검증 항목과 원고 교정을 보고서에 기록하고 커밋한다.

### Task 6: 전체 브랜치 리뷰와 원격 전달

- [ ] 전체 diff를 별도 리뷰 관점으로 검사하고 중요 결함을 RED→GREEN으로 수정한다.
- [ ] 최종 검증 후 `feat/ch13-section-13-2`를 push한다.
- [ ] `git ls-remote`로 원격 SHA가 로컬 HEAD와 같은지 검증한다.

