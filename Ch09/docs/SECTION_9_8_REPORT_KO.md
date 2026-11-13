# Ch09 §9.8 — 최신 실행 증거와 미완료 물리 접촉 경계 (2026-11-14)

> 이 구간은 **공개 CI에서 직접 검수된 최신 상태**다. 아래 2026-10-21 정적 보고서는 이력으로 보존한다. ROS 2 Jazzy / Gazebo Harmonic 고정 환경, Ch10 #123 **HOLD**.

## 1. 실제 성공 증거를 구분해서 보존

- **Ch09 §9.6 실제 Gazebo 기립 자세 SCOPED PASS:** [원본 stand_up 수정 PR #132](https://github.com/silverbjin/Pysical_AI_ROS2/pull/132), [CI #43244795784](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43244795784), [원본 Artifact #13955504103](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43244795784/artifacts/13955504103). 직접 내려받아 감사한 22개 파일 ZIP SHA256 `3c08ba5b6bae22eb55849df77461556bbf3a2476f175a4ca92c7c20b2f3ff08a`; 원본 테스트 checkout SHA `d8c4c03998cfce2dc14af5a3952ba86ea77ca408`. `stance_verdict.json`: model odom 492건, 8개 다리 관절 표본 16,161건, 마지막 4초 118표본. min base z=0.423203798m, late-window height spread=0.0000677506m, roll/pitch 최대 절대각=**0.463056°** (20° 상한), base XY displacement=**0.000181034m**. 원본 6초 보간 `STAND_UP_MEASURED_START_RAMP_6S` → `STAND_UP_RAMP_COMPLETE_ORIGINAL_GOALS` 확인.
- **Ch09 §9.7 단일 다리 명령·실제 관절 응답 SCOPED PASS:** 기존 [CI #43187047823](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43187047823)의 1,376 명령·13,080 관절 상태·약 0.723rad 변화 기존 증거를 **재실행 없이** 보존.
- **Ch09 §9.8 실제 ROS clock/TF SCOPED PASS:** [PR #147](https://github.com/silverbjin/Pysical_AI_ROS2/pull/147) 병합 SHA `21a96d6c273bbece2776edc5e5be29c538a53474`; [공개 CI #43363095114](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43363095114) SUCCESS, [Artifact #14008269297](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43363095114/artifacts/14008269297) ZIP 직접 감사 (16개 파일; SHA256 `5a50237c3b23e301ac22206648caae820a350486b8ebb69b1ad65391bbeceb59`). `model_contract.json`의 12개 revolute joint, 12개 고유 ROS→GZ cmd 쌍, 양수 질량 17개, 총 12.0000kg. 실제 RSP 및 **합성** `/clock`·`/joint_states`에 따른 **12개 동적 TF와 5개 정적 TF**, sim stamp≥100s, `result.json status=SCOPED_PASS rc0 shutdown=SIGTERM_CLEAN`. 이 TF-only CI는 **Gazebo 물리를 실행하지 않았다**.

## 2. 기존 합격을 전체 챕터 PASS로 확대하지 않는 이유

- 실제 기립 pose PASS는 **발 접촉력 직접 측정이 아니다**. `stance_verdict.json`은 `measured foot-ground contact forces`, 3회 독립 기립, 안정 관절 토크/한계, GUI 및 실기 검증을 명시적으로 `NOT_RUN`으로 기록했다.
- 다운받은 원본 실행 당시 생성 URDF에는 `fr_foot`, `fl_foot`, `rr_foot`, `rl_foot` 네 collision 링크가 있으나 명시적 `<mu1>`·`<mu2>` friction 태그는 없다. **Gazebo 기본 마찰을 포함한 실효 마찰이 0이라는 결론은 불가능**하다. 실제 gz-SDF 변환과 접촉 센서/힘 관측을 해야 한다.
- `TF-only` 성공은 실제 시뮬레이터 내부 clock·발 접촉·발 미끄러짐이 검증됐다는 의미가 아니다. GUI와 하드웨어도 `NOT_RUN`.
- Ch10 [Issue #123](https://github.com/silverbjin/Pysical_AI_ROS2/issues/123)은 별도 **HOLD**. 이번 범위에서는 Ch10 코드·CI·모델에 접근하지 않는다.

## 3. 다음 최소 신규 검수 (기존 성공 Gazebo 시험을 반복하지 않음)

신규 [Issue #165](https://github.com/silverbjin/Pysical_AI_ROS2/issues/165)로 실제 네 발의 지면 접촉력/접촉 여부 및 슬립 증거를 분리한다. 같은 불변 GHCR digest를 사용하되 **시험용 생성 URDF/SDF에만** 명시적 contact 계측 추가, 원본 stand_up·PID·월드는 불변. 한 번의 분리된 실제 Gazebo 물리 시험에서 최종 4초 각 발의 비어 있지 않은 contact 관측·시간·상대 충돌 대상·owned-process 종료를 검사해 새 raw Artifact로만 PASS 판정한다. 계측이 없다면 `NOT_RUN`; 원본 기립 CI와 ROS TF CI를 재실행해 합격 횟수를 늘리지 않는다.

---

## 2026-10-21 과거 정적 검토 보고서 — 변경하지 않고 보존

# 9.8절 코드 리뷰 — 통합 QA·트러블슈팅·다음 장 인계

- 검토일: **2026-10-21 (KST)** · 기준 main `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 원고: 9.8 「9.8 프로젝트 마무리 및 트러블 슈팅」
- 결론: **정적 검토 완료, ROS 2·Gazebo 런타임 NOT_RUN, 코드 실행 가능성 미인증**
- 범위: 요청된 리뷰/실습 문서만 추가하며 기존 소스는 수정하지 않음

## 검토한 실제 소스

- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/worlds/empty_world.sdf`
- `Ch09/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/display.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/stand_up.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/single_leg_mover.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/package.xml`
- `Ch09/ros2_ws/src/my_quadruped_bot/setup.py`

## 발견 사항

| 심각도 | 실제 코드 관찰 | 문제·개선 권고 |
|---|---|---|
| 높음 | 9.1~9.7에 드러난 launch 경로·시간·동시제어 문제는 전체 통합 실습에 직접 영향 | 정적 리뷰 문제 목록을 단계적 회귀 체크리스트로 전환 |
| 확인 | 전개 기대 총질량은 base6 + 4*(hip0.2+thigh0.7+calf0.5+foot0.1)=12kg | 원고 10~15kg 기준에는 포함되나 원고 부품별 수치와 다름 |
| 주의 | leg.xacro의 inertia vs collision center 및 foot friction 값 적용 불명확 | SDF 변환과 실제 물리 장면에서 기록 필요 |
| 높음 | package.xml의 실제 의존성 선언 부족, RViz launch가 Ch08 패키지 이름 참조 | 새 머신에서 Ch09 독립 재현 실패 가능성. clean overlay 검증 필요 |
| 높음 | source install/setup. 는 원고 오타, 설치 패키지 중복 overlay 가능 | setup.bash로 정정하고 Ch09 pkg prefix를 확인 |
| 주의 | 프로젝트에 trot_gait_preview.py가 추가로 있으나 원고 9.8 QA에는 별도 기대/위험 항목 없음 | 보행 안정성과 제자리 다리 파형 미리보기를 구분 |

## 리뷰 절차와 실행 검증의 구분

- **정적 리뷰:** 원격 GitHub main의 파일 전문과 첨부 원고를 대조하여 명칭, 값, 토픽·의존성·실행 흐름의 논리 문제를 확인했다.
- **NOT_RUN:** 이 환경에는 실제 ROS 2 Jazzy / Gazebo Harmonic 시뮬레이터가 준비되어 있지 않다. `colcon build`, `colcon test`, GUI, 브리지 통신, 관절 동작·물리 기립, WSL2 화면을 실행하지 않았다.
- **검증 보류:** 원격에서 읽은 파일이 XML·Python 구문상 무오류임을 `xacro`나 ROS 런타임 결과로 확인한 것은 아니다. 아래 기대는 가이드에 있는 사용자의 실행 결과로 검증해야 한다.

## 검증 수용 기준 및 재현 지점

1. XML/YAML·Python 구문 검사 결과와 colcon test 결과를 각각 보존했는가?
2. 로봇 총질량·TF·브리지 12개가 실제로 확인되었는가?
3. Gazebo 20초 기립 중 자세 오차와 미끄러짐을 기록했는가?
4. Ch10으로 인계할 관절 영점·이름·부호·소유권 계약을 문서화했는가?

**통과 기준:** 정적 규칙과 실제 물리 성공을 독립 PASS/FAIL 판정하고 근거 로그를 확보해야 다음 장의 보행 코드에 연결한다. 현재 이 PR만으로 Ch09 전체 기능을 PASS 판정하지 않는다.

## 원고·교재 수정 및 후속 구현 권고

원고의 '마무리/기립 성공' 서술은 테스트 실제 증거 확보 후에만 승인할 수 있다. 현행 루트는 base_footprint이고, WSL2 오버레이 충돌도 재현성 위험이다.

실제 코드 변경은 별도 승인된 수정 작업에서 담당하도록 남긴다. 수정 후에 같은 명령으로 RED→GREEN, 빌드·runtime·Evidence를 남겨야 한다. [실습 가이드](LAB_9_8_GUIDE_KO.md) · [Ch09 원본](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
