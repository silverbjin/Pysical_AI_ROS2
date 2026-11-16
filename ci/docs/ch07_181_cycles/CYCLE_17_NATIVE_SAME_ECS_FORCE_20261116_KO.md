# G04B Cycle17 — 동일 Gazebo PostUpdate 프레임의 native 접촉력 계측으로 해제 전 오판 제거

_2026-11-16 / Issue #181 / 활성 Draft PR #202 / BOOK_ROS2_DEV_DEBUG_CI_STD_V1_

## RED — Cycle16 실제 원본과 최초 불일치

- [L2 #43799242462](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43799242462), Artifact **#14195708042**, ZIP SHA256 `d632f336048853d9c1d72d4c44a21c50153732c9cd688c52392a952ae90b9528` (다운로드 원본 독립 감사).
- 50g rod 실제 lift 0.140390m, hold1.3s drift 0.00095136m, high native bin XY 0.00358434m, lower MoveIt plan-only 22점 SUCCESS, actual lower 22점 SUCCESS.
- 해제 직전 rod `[0.503899,0.235408,1.91191]m`, bin XY 0.048355m, custody drift 0.008570m, 실제 양쪽 finger q≈0.0115m. 이전 충돌 안전 하강 성공.
- 실제 해제 전 CLI 텍스트 tail parser는 `/clock=65.818s`에서 두 손가락 최근 접촉 0건이라 FAIL, release/settled NOT_RUN.
- **사후 원본의 독립 대조:** `diag_finger1_contacts.log`, `diag_finger2_contacts.log`의 sim 65.418..65.818에는 양측 401개씩 실제 collision pair+positive wrench (65.818s finger1≈0.701N, finger2≈0.582N). read-only `gazebo_rod_finger_contact_same_ecs_frame.csv`의 같은 시각 38개 프레임 모두 native pair count 1/1. 이 결과는 '물리 접촉이 사라짐'이라는 가설과 충돌하나, 비동기 CLI가 **그 실시간 순간** 얼마나 뒤처졌는지는 사후 파일만으로 확정 불가.

## 원인 후보/단일 변경 요인

**Gazebo 현재 접촉 정보의 계측·판정 경로만 교체**. 기존 Gazebo Sim8 `RodTrace` PostUpdate read-only `ContactSensorData`의 실제 손가락–원통 collision pair와 body1 wrench force magnitude를 같은 실측 frame으로 저장, timestamp는 `UpdateInfo.simTime` 사용. embedded contact header stamp가 0이므로 절대 시각 증거로 간주하지 않는다. 무거운 `gz topic -e` 텍스트 로그의 출력 지연과 분리하기 위해 작은 CSV 줄은 매 PostUpdate 즉시 flush.

원래 알고리즘의 **sim time age<=0.4s**, 실제 양손 각각 **3개 이상 양의 contact sample**, **force>0.05N**을 그대로 적용. Missing field/force, 0 pair, nonfinite, stale/future, 한쪽 센서 누락 시 **RED**. 이미 성공한 고위치/하강 관절 목표·물리 solver·마찰·충돌형상·bin/world pose·rod 50g·FJT/MoveGroup tolerance·최종 배치 ROI 전부 불변.

## 변경 및 검증

- `ci/ch07_181_rod_trace/rod_trace.cc`: 양손 `f1_max_rod_contact_force_N`, `f2_max_rod_contact_force_N` 컬럼, 같은 프레임에서 native wrench 절대값 계산, 매 CSV 줄 flush. No ECM mutation.
- `ci/ch07_181_native_recent_contact.py`: 원래 CLI 함수 **그대로 보존**, 별도 same-ECS-frame 접촉력 입력 판정. 과거 비동기 CLI의 0건도 진단 receipt에 보존.
- `ci/tests/test_ch07_181_native_recent_contact.py`: 정상 same-time force, stale/zero/missing/NaN/미발행/스키마 에러 및 C++ read-only 계측 불변식 TDD.
- `ci/ch07_77_g04b_actual_physics_witness.py`: C17 명시적 flag에서만 ECS positive native force를 해제 전 독립 oracle에 적용. 기존 `pre_release_valid` 함수 및 마지막 native 원본 접촉 감사·진짜 release/settled gate는 **절대 완화하지 않음**.
- `ci/ch07_77_g04b_physical_once.sh`, 공개 CI workflow: 명시적 flag로 C17 활성화, 새로운 `g04b-physics-once` label event 1회 L2. 정상 PR synchronize는 L0뿐.

## 교육용 과정·승인 기준

1. First RED는 물체를 놓친 것이 아니라 **비동기 관측 시각의 불일치 가능성**임을 source-level로 입증한다.
2. 기존 원본 positive force가 있어도 새 oracle의 **현재 frame 실측**은 새 물리 run에서 독립 검증해야 한다.
3. 성공 조건은 real bilateral contact/lift/hold/high/lower/native pre-release, 해제 Goal, 실제 동적 settled ROI(원통 높이 1.77m ±0.055m, XY ≤0.09m), **마지막 native raw parser PASS** 전부 충족. FCL/CSV 단독 Green 절대 금지.
4. L0 (대상 단위검증·정적) 및 승인형 L2 Run/Artifact는 결과 확보 후 이 문서에 원본 SHA와 함께 append; 실패하면 최초 불일치만 다음 사이클에서 해결.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
