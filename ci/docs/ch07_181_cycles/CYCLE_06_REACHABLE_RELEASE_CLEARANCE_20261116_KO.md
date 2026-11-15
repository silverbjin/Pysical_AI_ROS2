# G04B Cycle 06 — 도달 가능한 하강·해제 포즈로 실제 물리 배치

- 날짜: 2026-11-16 / Issue #181 / Draft PR #202
- 기준 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 물리 원본: [Cycle05 #43767407800](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43767407800), Artifact **14183066802** / ZIP SHA256 `3b7b1aa84ec750e029b89a1f2e7c2b130cef8d04b2b58477028bcc34643e2ade`
- **G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY**
- 참고: Cycle05의 PGS + 정확한 5DOF jaw 세계를 이번 A/B의 물리 기준선으로 재사용한다. 기본 도서 world에서 PGS를 무조건 켜지 않는다.

## 1. 현상과 근본 원인 분석 수준

원본은 실제 50g 원통 0.13289m 상승, 1.3초 hold drift 0.000759m, high bin XY 0.01325m까지 PASS. `lower_into_bin`은 MoveGroup 자체가 성공이라고 했지만 실제 joint3 목표 1.253174rad에 대해 `q3≈1.1274rad`. 이어진 FJT 역시 status6/error−5, 최종 q3 **1.132099rad**, 잔차 **0.121076rad**. native ECS 명령은 마지막에도 약 **1.21076rad/s**, 실제 native velocity 중앙값 약 `1.12e−11rad/s`; 물리 제약/접촉 근처 **정체**는 확인했지만 DART 내부 세부 원인 단정은 금지한다.

기존 q3=1.253 목표를 반복해서 보내는 것은 새 정보 없는 재실행이다. 로봇 프로젝트의 필수 요구는 임의 특정 q3 수치가 아니라 **실제 물체를 집어 운반하여 목적지에 자연스럽게 놓는 것**이다.

## 2. 단일 인과 가설

**물리적으로 도달하지 못한 joint3 각도를 명령하지 않고도**, 원래 bin 상공 XY 중심·최소/최대 해제 높이·gripper world 방향을 유지하면서 현실적인 하강·물리 낙하·안착이 가능하다.

- native plateau≈1.132rad에서 **0.082rad 아래인 q3=1.05rad**를 목표로 한다.
- 원본 5DOF의 `Rz(q1)Ry(q2+q3)Rz(q4)Ry(qw)` 정확 회전으로 world jaw를 고정하고 q1/q2를 bounded 2변수 Gauss–Newton으로 결정한다.
- 목표 원통 중심 [0.55,0.25,1.90]m, support 높이 1.73m, 실제 원통 중심 안착 예상 1.77m. 물리 낙하 예상 0.13m (낙하 안전 성공 보증 아님).
- 기존 Cycle05 실제 high pose 기준 오프라인 계산 예시: q1≈0.43858, q2≈−0.29507, q3=1.05, q4≈1.18439, wrist≈−0.09989rad; 예상 rod xyz≈[0.549844,0.249933,1.899639]m, XY <1mm, world jaw 변화≈0rad, tool 변화≈0.212rad.
- 예측 값은 **실제 동적 물체/로봇 접촉 관측을 대신하지 않는다.**

## 3. 한 사이클에서 변경한 요인

**하강 waypoint 한 개만 변경**한다. 원본 7관절 URDF·물리 collision·질량 0.05kg·gravity·마찰·controller·MoveGroup/FJT 허용차·양손가락 native 접촉·1.3초 hold·최종 안착 ROI **모두 그대로**.

본 시험은 이전 Cycle05에서 high transfer에 성공한 **PGS+WORLD jaw** world 조건을 그대로 고정해 비교한다. Cycle06의 새로운 제어 변수는 `G04B_CYCLE06_REACHABLE_RELEASE=YES`일 때의 하강 waypoint만이다. 다른 모든 PR 변경에 자동 Gazebo를 실행하지 않는다.

## 4. 개발 코드와 TDD

- `ci/ch07_181_reachable_release_waypoint.py`: 순수 Python closed bounds 최적화, q3 제한, 목표 world rod XY/z와 방향, 실제 관절 한계 검사.
- `ci/tests/test_ch07_181_reachable_release_waypoint.py`: 이전 실제 high 관절·rod offset positive fixture, NaN·관절 누락·미파지 offset·효과 없는 하강 제한 negative tests.
- `ci/ch07_77_g04b_actual_physics_witness.py`: flag에서만 waypoint 사용. real MoveGroup 완료 후 **모든 5관절 오차 <=0.01rad**가 아니면 FJT retry 없이 STOP.
- `ci/ch07_77_g04b_verify_contacts.py`: 최종 native contact/ROI와 별개로 새 하강 actual joint gate 추가.
- `.github/workflows/book-ch07-77-g04b-real-grasp.yml`: auto PR L0, 실제 Gazebo L2는 새로운 `g04b-physics-once` 승인 라벨 이벤트로 한 번만.

## 5. 반증·중단 규칙

실제 q3=1.05가 목표 오차 0.01rad 밖에서 정체하면 **접근 가능 가설 기각**. 실측 원통 center XY >0.06m 또는 z [1.78,1.92]m 밖, 실제 양손가락 힘/접촉 없음, release 후 안정된 0.09m XY·0.055m height ROI 미충족도 FAIL. 성공하면 전체 동일 세션의 원본 native 물리 증거를 감사하고 SCOPED_PASS 여부 판단.

**다른 테스트의 PASS를 합성해 G04B 성공이라고 주장 금지.** G00–G04A NOT_RERUN, G05 NOT_RUN, Ch10 HOLD.

## 6. 실행·리뷰·종료 보고(실측 후 갱신)

- 개발 commit: PENDING
- L0: PENDING
- L2: NOT_RUN
- raw Artifact 및 ZIP SHA256: NOT_RUN
- G04B: BLOCKED

**교육용 회고:** TDD로 기구학 수치 정합성을 입증한 것과 Gazebo에서 실제 접촉·중력 낙하·최종 안착을 입증하는 것은 전혀 다른 검증 계층이다. 물리 관절 제약을 우회하는 경로 설계는 허용차 완화가 아니라 목표 기능을 충족하는 새로운 동작 계획이어야 한다.
