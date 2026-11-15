# G04B Cycle 07 — 목적지 지지면의 실제 접촉 원인 계측

- 날짜: 2026-11-16 / Issue #181 / Draft PR #202
- 기준 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 이전 Cycle06 실제 원본: [Run #43769574949](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43769574949), Artifact #14183955993 / ZIP SHA256 `4ee87eeccaef5f40d46b9807bfd511d1659147492b902351a976d92baab20878`
- 현재 G04B **BLOCKED**, G05 NOT_RUN, Ch10 HOLD

## 1. 첫 실패와 아직 모르는 것

동적 원통 파지·상승 0.11407m, high bin XY 오차 0.01282m, custody 유지. 목표를 물리 정체 구간 밑으로 낮춘 새 Cycle06 q3=1.05rad에서도 실제 q3가 **0.99816rad** 근처에서 정체, command≈0.525rad/s 대 actual velocity≈0.0000001rad/s. 물체 실제 중심 ≈[0.51458,0.23484,1.93606]m, 그리퍼 FK 위치와 거의 일치. 최종 release/settled ROI NOT_RUN.

이 관찰은 q3의 고정 상한에 의한 실패와 다르며, 하강 중 **다른 물체 또는 목적지 지지면 충돌**이라는 후보를 남긴다. 하지만 기존 native contact는 rod↔finger 및 원래 shelf의 contact만 기록했으므로, 목적지 support와 arm link의 실제 접촉쌍은 아직 증거가 없다.

## 2. 한 가지 반증 가능한 관측 가설

**목적지 bin collision geometry가 arm/link 또는 rod와 접촉한 시간에 q3의 native 실제 속도가 정체하는지** 실측한다.

- static bin support centre [0.55,0.25,1.63]m, collision box 0.30×0.30×0.20m, top 1.73m.
- bin_support의 **기존 bin_collision에만 read-only contact SENSOR**를 추가한다. Bin collision 크기, pose, static, gravity, friction, robot/rod/Goal은 모두 불변.
- 비교 물리 조건은 직전 Cycle06의 PGS + exact WORLD jaw + reachable lower waypoint를 동일하게 유지한다. 새 변수는 **contact sensor 하나**.
- collision records가 q3 정체와 겹치면 접촉 후보를 좁히고, bin 접촉이 없더라도 contact 시스템·시각 유효성 없는 단정은 금지. 원인 확정까지 G04B BLOCKED.

## 3. 코드와 검증 계획

- `ci/ch07_181_bin_contacts_readonly.py`: 테스트 월드 XML 구조 검증, bin contact sensor 한 개 추가, 제거 후 전체 XML 동일성 검증. Contact system/plugin 중복 불허.
- `ci/tests/test_ch07_181_bin_contacts_readonly.py`: 변경 범위 및 0.30m bin geometry·PGS physics·mass 불변·중복 센서/가짜 collision 거부.
- `ci/ch07_77_g04b_physical_once.sh`: Gazebo Goal 전 native bin topic 유효성 검증 후 원본 `diag_bin_contacts.log`로 기록. 센서가 준비되지 않으면 시험 전 STOP.
- `.github/workflows/book-ch07-77-g04b-real-grasp.yml`: L0에서 해당 코드/TDD를 검사, 실제 L2는 opt-in `g04b-physics-once` 이벤트 1회.
- CI Artifact에 raw bin contact, 기존 joint3 JTC→HW→native ECS 및 dynamic rod 좌표·native contact 원본을 함께 보존.
- **L0:** PENDING / **L2:** NOT_RUN / Artifact: NOT_RUN.

## 4. 교육용 디버깅 기준

1. 관측 사실(토픽 존재·native collision pair·timestamp)과 원인 주장(DART contact constraint)을 구분한다.
2. READ-ONLY sensor를 추가하면서 충돌 형상·물리 mass·마찰을 바꾸지 않아 인과 실험을 보존한다.
3. 실제 new BIN contact가 없으면 collision 가설을 기각하기 전에 기록 시각과 sensor 활성 상태를 검증한다.
4. 실제 Gazebo가 FAIL하면 그 원본을 감사한 뒤 **같은 시험 재실행 없이** 다음 판단으로 이어간다.

**Cycle07 보고서는 L0/L2 원본 실측 후 갱신·커밋한다. G04B BLOCKED 유지.**
