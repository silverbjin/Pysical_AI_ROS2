# G04B Cycle 03 — DART contact PGS solver 단일 물리 비교

- 날짜: 2026-11-15 / Issue #181 / Draft PR #202
- 기준 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`, 기준 코드 `11090b223daa74aea5beb3dfa4c8040306d451ba`
- 고정 원본 동적 물리 FAIL: [#43719033640](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43719033640), Artifact #14164070632 ZIP SHA256 `96362eace97d021acfeb47979f35d2fefcd516054547d0b937213e97fbe211e5`
- 이전 Cycle 01/02: high joint2 최종 0.0130665rad 오류, high 종료+0.2~+0.7초 native cmd median 0.123818rad/s, 실제 velocity median 0.000140rad/s. **G04B BLOCKED**.

## RED 및 가설

원래 DART Dantzig contact constraint solver를 사용하는 현행 앵커 고정 테스트 월드에서, 실제 50g 원통 물체를 잡고 운반할 때 joint2 velocity command 대비 물리 운동이 정체된다. **가설:** DART 접촉 제약 solver 방식이 이 말기 오차의 원인일 수 있다. 기존 Draft #197에서는 다른 구동 기준선에서 PGS가 물체 custody에 개선을 보였지만 완주 FAIL; 현행 SHA에 성공 근거를 이전하지 않는다.

## 변경 요인 단 하나

이미 검증했던 Draft #197의 `ci/ch07_181_dart_solver_single_factor.py`와 negative TDD를 재사용한다. `world/physics/dart/solver/solver_type = pgs` 필드만 test-only world SDF에 추가. XML equality로 다른 요소의 변경을 거부한다. 원본 DART 충돌 검출 ODE, 1ms physics step, world gravity −9.8m/s², 50g 동적 원통, 마찰, ROS 7개 관절/컨트롤러, finger test-only 하한 −0.001m 및 world anchor, ROS Goal, 물리 안전 판정은 모두 동일하게 유지한다.

## 개발 결과물

- 코드: `ci/ch07_181_dart_solver_single_factor.py`, `ci/ch07_77_g04b_physical_once.sh` (한 세계에서 한 요인)
- 단위 테스트: `ci/tests/test_ch07_181_dart_solver_single_factor.py` (질량·중력·검출기·기타 물리 변환 금지)
- GitHub Actions: 관련 소스 SHA와 L0 테스트, 승인형 Gazebo 물리 Job 유지
- **L0:** PENDING / **L2:** NOT_RUN / Artifact: PENDING

## 1회 검증과 중단 조건

L0 성공 시 **동일 SHA 승인형 Gazebo L2를 한 번** 실행. PGS 조건에서 실제 joint2 고착과 원본 native 물체 최종 배치 여부 확인. 실패하면 G04B BLOCKED 유지, 동일 solver를 다시 시험하지 않고 원본을 감사해 다음 실패만 추출한다. 물체 teleport/attach, Goal 허용오차 확대, 가짜 접촉, 기존 성공 결과 재실행 금지.

**교육 목표:** 이론적 solver 대안이 실제 인수 오류를 해결하는지는 하나의 물리 요소만 바꾼 A/B 실험으로 검증한다. 통과하지 못한 실험을 억지로 PASS로 만들지 않는다.
