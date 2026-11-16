# 도서 실습 검수 — G04B 19사이클 최종 종료 보고 (2026-11-17)

**판정:** 반복 실험 작업 **STOP/FROZEN**. G04B 엄격 물리 무충돌 **BLOCKED**. Ch07 §7.7 동일 세션 RGB-D→MoveIt→물리 Pick-and-Place **NOT_ACCEPTED**. G05 **NOT_RUN**, Ch10 **HOLD**, Owner WSL2 **NOT_READY**. 성공하지 않은 L2를 PASS로 승격하거나 임계치를 변경하지 않는다.

## 1. 기준

- 저장소 [silverbjin/Pysical_AI_ROS2](https://github.com/silverbjin/Pysical_AI_ROS2), 확인 당시 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`.
- 활성 물리 [Draft PR #202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202), C19 소스 `0ffc821911bef64eeb02d0ec2a6a320ad703c67f`; **base는 main이 아닌** `diagnostic/ch07-181-worldpose-component-source-20261115`. 단독 main 병합 금지.
- 별도 방법론/CI [Draft PR #203](https://github.com/silverbjin/Pysical_AI_ROS2/pull/203), `BOOK_ROS2_DEV_DEBUG_CI_STD_V1` 승인 내용: Architecture/Evidence-First, 선택적 TDD, 관련 L0, 새 가설에만 승인형 실제 Gazebo L2 1회, 원본 감사.
- G00~G04A의 기존 scoped PASS는 보존/NOT_RERUN. [Issue #118](https://github.com/silverbjin/Pysical_AI_ROS2/issues/118)의 101개 LAB 전체 PASS와 혼동하지 않는다. Ch07 §7.2~7.6 RGB/Depth/Cloud, synthetic detection/TF, 그리퍼는 각 증거 범위에서만 scoped PASS.

## 2. 19사이클 전체 개발 흐름

개별 보고서: [`ci/docs/ch07_181_cycles/`](ch07_181_cycles/), `CYCLE_01_*.md` ~ `CYCLE_19_*.md`.

| 사이클 | 개발·분석·디버깅의 성과 | 다음 최초 실패 |
|---|---|---|
| 01~04 | FJT 목표/reference/feedback/error, native 관절 구동 경계와 DART contact solver 진단 | 한 손가락/고위치 구동·물리 수렴 |
| 05~09 | world-frame jaw 계산, 안전한 해제 자세/기구학, 실제 bin collision과 MoveIt PlanningScene, elbow 분기 | bin↔link4 고위치 충돌 |
| 10~12 | collision-aware high 실제 움직임; 엄격 5mm 목표·3mm clearance 문제 분리. **test-only bin yaw=0.35rad** 적용(원본 yaw=0과 동등하지 않음) | 측정 held offset 및 정확도 |
| 13~16 | 실제 held offset 보정, high 및 실제 lower MoveIt/FJT, 하강 성공, 원본 contact 로그 시간 불일치 발견 | 해제 직전 접촉 오판 |
| 17 | Gazebo **same-ECS-frame native contact/force**로 읽기 지연 영향을 줄여 실제 release/settle까지 도달 | 손목↔rod 충돌 648건 |
| 18 | 손가락 open과 joint3 후퇴 동시 FJT, plan_only와 실제 관절 검증 | 충돌 620건 |
| 19 | 후퇴 FJT 시간만 0.80→0.25s 단축 | 충돌 535건, 최종 배치 ROI 실패 |

## 3. 원본 기반 C17~19 판정 비교

| 시험 / 소스 | 실제 공개 Gazebo L2 / Artifact | 손목-원통 native 충돌 | 최종 XY 오차 | 물리 판정 |
|---|---|---:|---:|---|
| C17 `839e44ff9e7012c21e1a8718b57a3dc13ff34637` | [43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279) / `14196048989` | 648건 | 0.04244m | FAIL |
| C18 `42905211c062b4a6806af798caf0443f3e2f536f` | [43806722104](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43806722104) / `14198364217` | 620건 | 0.061265m | FAIL |
| C19 `0ffc821911bef64eeb02d0ec2a6a320ad703c67f` | [43807639093](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43807639093) / `14198349320` | 535건 | **0.137081857m** (한계 0.09m) | FAIL |

원본 ZIP SHA256:
- C17 `9abea85bad69d41d9a77fafa123bd37b9c5d8b19359f43856d523e4861062f0c`
- C18 `f8186a2ee776241e1a5756875b7a5d222cff4c0e70d9717b58a1c2afd0dc658e`
- C19 `83ac0c074872bf883404687dd8b83c3f882ceba2fc6758eaa531a954a40ed417`

C19 **최종 사후 원본 감사 기록**: L0 [43807540609](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43807540609) SUCCESS, Book Lab [43807539674](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43807539674) SUCCESS, 물리 L2 FAIL. 실제 50g rod lift 0.14615m, hold drift 0.00090177m, lower 전 XY 0.04433m, 최종 높이 오차 0.028m; finger/arm FJT 완료. 하지만 release 이후 native wrist-rod 충돌 535건(시뮬레이션 65.355~65.936s)과 settle XY 0.13708m로 인수 실패. C19 사전 계획 문서에는 시험 결론이 없어 **본 보고가 최종 사후 감사 결과를 보완**한다.

**교훈:** 648→620→535건으로 접촉 횟수가 줄어든 것이 안전성 PASS를 의미하지 않는다. 최종 ROI는 4.24→6.13→13.71cm로 악화됐다. C01~17은 실패 경계를 옮긴 유효한 연구였으나 C18~19 이후 단순 속도 sweep은 중단한다. 기존 무충돌 게이트 임의 완화 금지.

## 4. 세 가지 독립 결과

**(A) `BOOK_DEMO_CANDIDATE_WITH_LIMITATION`: C17 증거 보존.** 실제 bilateral contact, ≥5cm lift, 1s+ hold, collision-aware high/lower, release, 목적지 XY 4.24cm·높이 2.8cm. **하지만** native wrist-rod 648회, 약 17.13N의 접촉과 test-only yaw 0.35 bin/world-fixed base 조건이 있다. '교육용 실패·한계 설명용 후보'일 뿐 **안전한 데모/정식 출판 인수/원본 월드 성공**이 아니다.

**(B) `G04B_PHYSICAL_CLEAN=BLOCKED`.** C17~19 모두 독립 raw 무충돌 기준 실패. Action SUCCEEDED, L0 SUCCESS, 최종 ROI 일부 만족은 이를 대체하지 않는다.

**(C) `CH07_77_E2E=BLOCKED / G05_NOT_RUN`.** 현재 `main`의 `Ch07/ros2_ws/src/vision_basics/vision_basics/mission_controller.py`에는 **G01의** `/camera/target_valid`, `/camera/target_3d_base` 구독, 1회/시간/좌표 차단, `/ch07_77/target_ready`, `/ch07_77/pregrasp_candidate` 발행 코드가 존재하며 `setup.py`에 콘솔 엔트리도 있다. **단 NO_GOAL 단계**로 MoveIt·물리 인수는 없다. `main`의 `LAB_7_7_GUIDE_KO.md`는 구독/엔트리가 없다는 과거 설명이 남아 있어 후속 출판 시 G01 존재/전체 미검증으로 갱신해야 한다.

## 5. 비효율 분석·종료 조치

2026-11-12~15 저장소 전체 **548 Actions Runs / Book Lab 190 Runs**는 [PR #203](https://github.com/silverbjin/Pysical_AI_ROS2/pull/203)의 정책 진단 근거다(물리 G04B 횟수와 동일시하지 않는다). 파일별 빈번 커밋·광범위 경로 트리거·동일 환경 설치·대형 raw 재생성이 시간을 증가시켰다. 이제 **한 변경+보고서 한 커밋**, 관련 L0만 자동, 핵심 새 물리 가설/승인 있을 때만 L2 1회, 재실행보다 이미 확보한 원본 활용을 적용한다.

| 항목 | 최종 처리 |
|---|---|
| C01~19 보고서, raw Run/Artifact/SHA | KEEP/ARCHIVE |
| 후퇴 속도 실험 반복 | STOP |
| PR #202 / #203 | Draft OPEN, 근거 보존, 자동 병합 금지 |
| Issue [#181](https://github.com/silverbjin/Pysical_AI_ROS2/issues/181) | OPEN/BLOCKED. 개발 반복 종료 ≠ 기능 완료 |
| Issue [#173](https://github.com/silverbjin/Pysical_AI_ROS2/issues/173), [#118](https://github.com/silverbjin/Pysical_AI_ROS2/issues/118) | OPEN, 통합/전체 LAB 미완료 |
| Ch10 / Owner WSL2 | HOLD / NOT_READY |

향후 필요 시 **G01 기존 코드 재사용 → 실제 RGB-D 같은 stamp의 목표(G02) → IK/MoveIt plan_only·안전 Goal(G03) → 물리 인수(G04) → E2E 문서/Owner(G05)** 를 별도 좁은 작업으로 진행한다. 손목 충돌의 물리 무접촉 목표는 기하 구조·해제 위치 자체를 바꾸는 가설을 오프라인 선행 검증한 후에만 다시 다룬다.

**종결:** 본 19사이클 G04B 개발/디버깅 반복 스트림을 2026-11-17부로 종료한다. 미완료 Gate는 가감 없이 유지하며, 기존 검증 증거와 교육용 디버깅 내역을 보존한다.
