# SECTION 8.8 코드 리뷰 — Sim-to-Real 및 ROS 2 브리지

**기준:** 2026-10-20 / main `38fb4647aeff2d3ab951404d78e1812e598f2308`; 원고 8.8.1~8.8.3; `Ch08/ros2_ws/rl_env.py`, `my_robot_env.py`, `src/my_robot_description/launch/sim_sync.launch.py`, `my_robot_description/simple_arm_teleop.py`, `setup.py`, `package.xml`.

**판정: 연구 개념 설명에 적합하나 실물 안전 배포 불가 / 정책↔ROS 2 연결 미구현.** 실제 하드웨어·Gazebo·ROS 통합 동적 테스트 미수행.

## 구현 범위 대비 원고
- **구현됨:** `ReachEnv`의 reset 시 목표 랜덤 생성, actor action clip, 보상의 연속 action 변화량 벌점.
- **미구현:** 링크 질량·마찰·감쇠의 모델 도메인 랜덤화, 관측 노이즈·통신 지연 큐, inference 정책의 ROS 2 joint 명령 변환, 하드웨어 토크/속도/위치 한계 및 watchdog·E-stop.
- **별도 기능:** `sim_sync.launch.py`는 Gazebo+robot_state_publisher+ROS-Gazebo bridge+RViz 데모다. `simple_arm_teleop.py`는 키보드 기반 위치 명령 발행기. **PPO `ReachEnv`가 Gazebo/ROS와 연동된다는 근거가 아니다.**

## 확인한 이슈
| ID | 심각도 | 문제 | 조치 |
|---|---|---|---|
| 8.8-R1 | BLOCKER | PPO action 정규화(-1~1)와 ROS 2 `Float64` 위치 cmd 사이의 제어 의미·관절 순서·단위/주기가 정의되지 않음 | 별도 계약·안전 필터·상태 검증 후 시뮬레이터 우선 통합 |
| 8.8-R2 | HIGH | 원고의 도메인 랜덤화 예시가 `reset`에서 `original_mass=self.model.body_mass.copy()`를 호출함: 매 episode 현재 랜덤 값을 baseline으로 삼으면 배율이 누적됨 | `__init__`에서 원본 질량/마찰/감쇠 스냅샷 고정, 매 reset 독립 샘플링; 필요한 물리 상수 재계산/API 확인 |
| 8.8-R3 | HIGH | 원고 관측 노이즈 예시는 전역 `np.random` 사용, target/physical 관측 모두 같은 노이즈 적용 | seeded `self.np_random`, 단위별 noise 표준편차, 노이즈 없는 ground-truth 보존 |
| 8.8-R4 | HIGH | 실제 정지/전원 차단은 `clip`/EMA로 보장되지 않으며 하드웨어 안전 회로가 필요 | 드라이버 독립 E-stop, watchdog, 한계 스위치/토크·속도 제한, 위험평가 |
| 8.8-R5 | HIGH | `sim_sync.launch.py` bridge 명령은 `joint2/cmd_pos`만 정의; `simple_arm_teleop.py`는 `joint1`과 `joint2` 모두 발행 | joint1 bridge와 컨트롤러 endpoint 존재 여부 검증 |
| 8.8-R6 | MEDIUM | ROS 패키지 `setup.py`가 MJCF XML을 설치하지 않고, launch는 `two_dof_arm.urdf.xacro`를 사용 | 2DOF Gazebo 데모와 6DOF MuJoCo PPO의 모델 차이 문서화 |
| 8.8-R7 | MEDIUM | 도서 예시에서 `mjModel`을 '절대 불변'이라 해석하면 런타임 파라미터 랜덤화와 충돌 | 런타임 변경 가능 항목·수반 계산/주의사항을 정확히 설명 |
| 8.8-R8 | MEDIUM | ROS overlay에서 동일 `my_robot_description` 패키지 이름 재사용 가능 | 새 터미널에서 환경 분리, `ros2 pkg prefix`로 실제 설치 경로 확인 |

## 안전 인수 조건(향후 구현용)
**ROS에서 실기 사용 금지.** 먼저 분리된 Gazebo/MuJoCo 모의 연결에서 관측 단위·관절 순서·엔드포인트·주기·타임스탬프·명령 만료·E-stop까지 명세/테스트한다. 안전 등급이 요구되는 현장은 독립된 하드웨어 안전 체계와 전문 검토가 선행돼야 한다.

**검증 상태:** GitHub 코드 대조만 완료, 물리 파라미터/randomization, ROS 연결, 실기 안전 검증 모두 미수행. 문서-only branch.

[실습 가이드](LAB_8_8_GUIDE_KO.md)
