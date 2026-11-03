# 입력 손실 정식 판정 수정 및 새 실행 인수

2026-11-04 KST. 사용자 요청에 따라 과거 FAIL은 보존하고, **수정한 정식 판정기로 새 실행 PASS**를 확인했다. 별도 사후 검토 PASS를 새 실행 결과로 대체 사용하지 않았다.

## 실제 결과

- 새 UUID: c8be6d60-e73d-4b55-ad16-fa7bea011977.
- 정식 판정: 13_6_navigation_formal_v1, 결과 PASS, 검사22개 모두 true. run_case.sh가 새 판정기를 자동 실행했고 종료코드0이었다.
- 소스 commit873ad8fe7f332b97b3d74d092d7b4e38d3d2372c, source freeze v14의251파일·원본94자산. 동결 SHA2569605c2c9d3b411b3f89f3c8b533f110042aa48d8cff5331983a3f58dcea6c000.
- 부품 시험213 PASS/64.69초, 별도13.6 build6개/21.7초. 새 engine 실행은 이 입력 손실1회뿐이며 engine 구간9.09wall초/4.986sim초다. 시작·감사 시간은 별도다.
- 실제 정착 수치: 평면 RMS속도0.008816m/s, yaw RMS0.027680rad/s, 평면 변위2.929mm. 기존 edu_stop_v2 한도를 변경하지 않았다.
- 입력 복구 후 자동 재활성화 없음. RX·원본 thread join, 자식10개 정상 종료·잔여 PID 없음·post residual PASS, actuator cap 비율1.0.

## 원인 확정

이번에는 Guard가 첫 만료 판정에서 원본 sample stamp/최초 receipt, 현재clock, clock receipt, graph 시각, owner count와 실패한 조건을 고정 기록했다. 그 뒤 수신 상태가 변해도 첫 기록을 덮지 않는다.

| 역할 | 최초 실패 항목 | 원본 입력 wall age | clock wall age | graph wall age |
|---|---|---:|---:|---:|
| 상위 gateway | sample_wall_expired:raw |302.580ms|11.533ms|0ms|
| engine platform | sample_wall_expired:safe |300.015ms|0.00394ms|4.169ms|

따라서 이 새 사례는 시계나 그래프의 만료가 아니라 의도한 원본 입력의 수명 만료였다. pause 전에는 두 감시기 모두 ARMED·무fault였다. pause 전송 뒤 gateway301.171ms, platform302.542ms에 각각 만료를 판정했다. 두 역할 모두 zero를 유지했다. 과거 v13 사례에는 이 구체 기록이 없으므로 과거 원인까지 같은 항목이라고 소급 확정하지 않는다.

## 정식 수정

안전 제어의 _fresh 판정,300ms wall/sim 수명,2ms physics,50simHz 정책,350ms 손실 판정 예산·힘/정착 기준은 변경하지 않았다. 수정은 첫 만료 snapshot·주입 전/후 시각 기록·정식 시나리오별 판정이다.

기존13.5 verify_navigation.py는 변경하지 않고 실제 운동·정지·힘·관절·회수 수치 계산을 그대로 재사용한다. 새13.6 정식 verify_navigation.py가 platform fault 조건을 명시 계약으로 평가하고 모든 공통 검사를 유지한다. 정상 실행은 timeout이 있으면 FAIL이다. raw_loss는 실제 owned pause 뒤 raw 만료·정지·재활성화 없음이 필요하다. 하위 engine timeout이 동반되면 최초 원인이 safe 원본 입력 만료여야 한다. 기록 누락·clock/graph/owner 문제·주입 전 fault·다른 fault·정지 뒤 재움직임은 거절한다.

새 최종 판정은 사례 루트의 navigation_verification.json이다. 기존 계산기의 *_physical_metrics.json/log는 계산 근거로 보존하며, 거기에 남는 공통 fault-empty 항목을 정식 최종 판정으로 사용하지 않는다. 예전 review_loss.py에 의존하지 않으며 특정 UUID에만 적용되는 예외도 아니다.

실제 Guard로 최초 원인 고정/reset/기존 판단을 검증하고, 정상 timeout과 무관한 fault·가짜 원인 label·주입 전 오류·이력 은폐·정지 후 움직임을 거절하는14개 시험을 추가했다. RED는 모듈 미구현으로 관찰했고 전체213개 최종 시험에 포함했다.

## 보존과 검증 범위

과거 a854efd7-67fc-4964-aced-0fd36b59f7bf의 원판정 FAIL, 별도 검토 PASS, v13집계와 archive는 그대로 보존했다. 새로운 결과는 ACCEPTANCE_FORMAL_RAW_LOSS_V14.json과 새 UUID 증거로 구분한다. 이전 다른15개 성공은 기존 소스의 검증 이력이며 새v14 전체 matrix라고 주장하지 않는다. 수정 범위에 맞춰 부품 시험과 새 raw_loss1회만 수행했다.

[실습 가이드](LAB_13_6_REUSE_GUIDE_KO.md), [기존 전체 인수와 이력](SECTION_13_6_REUSE_REPORT_KO.md), [수정 계획](SECTION_13_6_RAW_LOSS_FORMAL_FIX_PLAN_KO.md)을 함께 제공한다. 자체 검토는 단일 작업자로 수행했으며 실기·반복 강건성 검증으로 확대하지 않는다.