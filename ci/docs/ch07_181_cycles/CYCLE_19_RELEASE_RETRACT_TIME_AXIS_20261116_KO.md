# G04B Cycle19 — 실제 후퇴 초기 응답 지연에 대한 단일 FJT 시간축 수정

_2026-11-16 / Issue #181 / Draft PR #202 / BOOK_ROS2_DEV_DEBUG_CI_STD_V1_

## RED — Cycle18 원본 근거

- 공개 L0 [#43806636196](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43806636196) **SUCCESS**, Book Lab [#43806636229](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43806636229) **SUCCESS**.
- 승인형 Gazebo [#43806722104](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43806722104) **FAIL**, Artifact #14198364217, 원본 ZIP SHA256 `f8186a2ee776241e1a5756875b7a5d222cff4c0e70d9717b58a1c2afd0dc658e`; source PR HEAD `42905211c062b4a6806af798caf0443f3e2f536f`. 원본 ZIP·native contacts·sim-time joint trace 독립 대조.
- 실제 rod lift **0.13144m**, hold drift **0.00098952m**, high bin XY **0.003337m**, real lower→release→settled 전 단계 성공. 최종 XY **0.061265m** / height error **0.028m**, 각 원래 0.09/0.055m 내. 원래 5mm high/기존 native bilateral contact/원래 bin/URDF 유지.
- 신규 동시 Goal: MoveIt plan_only **5 points SUCCESS**, 손가락 release FJT **SUCCEEDED**/실제 q≈0.000377m, 팔 후퇴 FJT **SUCCEEDED**, 실제 q3 목표 오차 <2e-8rad. 그러나 독립 감사 `native_wrist_rod_contact_events=620` **FAIL**, 최대 실제 접촉력 **16.30N**. **G04B BLOCKED 유지**.
- 최초 충돌 시각 **70.675s**: FJT 병렬 송신 기준 sim 시작 **70.578s**로부터 97ms. 실제 q3는 t70.702s에도 **1.045864rad** (초기 **1.049362rad**, Δ≈0.0035rad)만 이동했으며, 목표 **0.994359rad**에는 t71.60s 이후 도달. 손목이 원래 추정 낙하 경로에서 멀어지기 전에 rod가 움직이며 손목 충돌 발생. 0.8초 time_from_start가 실제 97ms 응답에서 충분하지 않았다.
- 실제 물리 첫 충돌은 원통-손목 접촉. 충돌 0건 규정 수정/무시 금지.

## 하나의 기계적 가설과 최소 변경

**오로지 신규 후퇴 FJT `time_from_start`만 0.80s→0.25s로 단축**한다. 시작 q3와 목표 delta -0.055rad, 동시 finger FJT 2초, 동일 MoveIt FCL plan_only, 동일 native contact/rod/placement 판정, Gazebo 물리 파라미터, bin yaw=.35/shape/pose, 로봇 URDF/limit 변경 없음.

- q3 평균 요구속도 **0.22rad/s**. 원본 URDF `joint3` velocity limit **1.5rad/s**. 보수적 smooth interpolation peak factor1.875 적용 시 **0.413rad/s**로 limit 아래. 단, 실제 Gazebo 액션 결과·hardware introspection이 이 계산을 독립 검증해야 한다.
- `ci/ch07_181_release_wrist_retract.py`: `C19_RETRACT_FJT_DURATION_S=.25`, 현재 source 1.5rad/s limit, 제한적 사전계산.
- Witness에서 `release_and_retract_fjt`의 원래 arm q3 FJT duration만 같은 상수로 변경, result에 정확한 명령 시간과 native controller feedback 보존.
- `ci/tests/test_ch07_181_release_wrist_retract.py`: timing limit·source/witness 일치·손목 충돌 제로 판정/other gates 보존.
- L0 PASS 후 새 라벨 이벤트 물리 **1회**. 실제 0.25s를 줬다고 역학 collision-free를 주장하지 않는다.

## 다음 기준

0건 wrist↔rod 충돌, 실제 bilateral grip→lift/hold/high/lower→release→settled world ROI와 독립 native audit **모두** PASS만 G04B 완성. 동일 첫 충돌 반복 시 시간축 단축 반복 대신 **하드웨어·그립 배치 아키텍처**를 재검토. 원본 ZIP 해시를 보고서에 연결하고 다음 사이클을 추가.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
