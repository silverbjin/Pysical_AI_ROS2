# 입력 손실 정식 판정 수정 계획

2026-11-04. 사용자가 승인한 범위: 과거 FAIL은 보존하고 수정한 정식 판정기로 새 실행을 PASS하도록 마무리한다. 단일 작업자, 기존 격리 branch/build를 유지한다.

설계: 안전 제어·300ms 수명·350ms 손실 판정 예산·정착 수치를 바꾸지 않는다. Guard가 최초 만료 때 어떤 clock/graph/source 항목이 만료했는지 원본 시각과 함께 한 번만 기록한다. 주입기는 pause 전/후 시각과 직전 상태를 저장한다. 13.5 판정기와 과거 결과를 보존하고 13.6 정식 navigation 판정기를 둔다. 기존 정지/힘/회수 수치를 그대로 재계산하며, platform fault 조건만 시나리오별 명시 계약으로 대체한다.

정상 시나리오는 engine fault가 없어야 한다. raw_loss는 실제 owned publisher pause 뒤 gateway의 raw 만료·실제 정지·재활성화 없음·정상 회수가 필요하다. engine timeout이 함께 있으면 최초 실패 항목이 safe 입력의 원본 wall/sim 수명이어야 한다. clock/graph/소유자·주입 전 fault·다른 fault는 허용하지 않는다. 구체 기록이 없는 과거 FAIL은 이 새 계약의 PASS로 소급하지 않는다.

- [ ] RED: 실제 Guard에서 safe/raw 만료 원인 기록·첫 원인 고정·기존 판단 유지 시험. 정식 계약은 정상 timeout/clock·graph·중복·주입 전·정지 뒤 움직임/원인 누락을 거절한다.
- [ ] GREEN: 진단 snapshot과 주입 기록, 정식 CLI·계약 구현. 기존13.5 판정기는 수치 계산을 재사용하되 변경하지 않는다. 정식 출력은 독립 경로에 모든 check와 원래 수치 계산 결과를 포함한다.
- [ ] 전체 부품 시험 한 번, 별도13.6 build, source v14 동결. 이전 v13과 변경 파일을 명시한다.
- [ ] 새 UUID raw_loss 한 번 실행→정식 verifier PASS·원인 확정·정상 회수. 기존 다른15개 인수를 이번 실행으로 덮거나 전체 matrix를 반복하지 않는다.
- [ ] 결과/가이드/게시 보고서 갱신, 모델 제외 증거·선택 commit/non-force push·remote SHA 확인.

실행 경로는 기존 run_case.sh를 유지하고 13.6 navigation 실행 후 정식 verifier가 자동 실행되도록 한다. 따라서 runner 종료 성공과 정식 판정 성공이 함께 확인된다. 작은 부품 시험→단일 실제 사례 순서로 진행한다.
