# Ch07 §7.7 G04B — Issue #181 실제 계측·차단 경계 진행 기록

> 작성 기준: 2026-11-14, 공개 CI 원본 ZIP 독립 감사. **G04B BLOCKED, G05 NOT_RUN**. ROS 2 Jazzy / Gazebo Harmonic **시뮬레이션만**, 실제 하드웨어 안전 승인 아님.
>
> 기준 저장소: `silverbjin/Pysical_AI_ROS2` / 기통과 `main@9431fb535ce7a51416c19c4395fb2ba3fabdad40` / [총괄 #118](https://github.com/silverbjin/Pysical_AI_ROS2/issues/118) / [G04B #181](https://github.com/silverbjin/Pysical_AI_ROS2/issues/181). `Ch10 #123` **HOLD**.

## 1. 확정한 사실과 허용되는 보고 범위

- G00~G04A 기존 공개 실측 성공을 유지하고 다시 실행하지 않았다. Gazebo 원본 로봇 URDF, 원본 `ros2_control`의 original finger axes, 원본 센서 및 관절 제한을 수정하지 않았다.
- 물리 원통은 질량 50g, 지름 24mm, 높이 80mm, 동적 모델. Test-only 6mm 실제 충돌 지지대는 상면 world z=1.900m를 유지하며 원통 바닥을 물리적으로 받친다. **강제 attach, set_pose, teleport, FakeSystem 없음**.
- 원래 손목↔받침대 네이티브 충돌(667건)은 시험용 지지대 하부를 좁히고 높이를 줄여 차단됨을 확인했다. 이후 시험들에서는 손목–지지대 실제 접촉 0건.
- 실제 Jazzy JTC 메시지는 `reference/feedback/error`를 사용한다. 기존 `desired/actual` 추출 오류를 수정했으며, **FJT Action SUCCEEDED는 독립 JointState 성공의 충분조건이 아니다**. 실제 손가락이 목표를 추종하지 못하면 명시 FJT tolerance로 ABORTED(-5) 처리하고 G04B를 실패로 판정한다.
- 별도 조건의 *자유공간* 시험에서는 실제 양손가락 구동이 가능하다. 하지만 물리 원통 접근 이후에는 finger2가 q≈0으로 멈추는 실패가 남아 있다. 지금까지 **양쪽 손가락 실제 접촉 + 5cm 상승 + 1초 유지 + 배치 성공을 한 세션에서 동시에 증명하지 못했다**.

## 2. 공개 원본 검증 이력 — PASS의 범위를 넓히지 않음

| CI | 신규 실패 경계 및 원본 실측 | 판정 |
|---|---|---|
| [#43574030542](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43574030542) | q4≈π/2 pregrasp, finger2 목표 12mm, 실제 q≈0; FJT SUCCEEDED가 거짓 양성 | G04B RED |
| [#43579545607](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43579545607) | ground-only 자유공간 동시 두 finger 목표 12mm→각 실제 11.985mm | FREE_SPACE_SCOPED_PASS |
| [#43580533046](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43580533046) | ground-only 순차 단독 finger1→reopen→finger2 실제 각 구동 PASS | FREE_SPACE_SCOPED_PASS |
| [#43580998856](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43580998856) | 원통/받침대 존재하나 접촉 전, **직접 팔 FJT** 자세 + 순차 gripper 각 실제 PASS | PRECONTACT_SCOPED_PASS |
| [#43581398334](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43581398334) | 동일 조건에 초기 open FJT 1건 추가 후 정상 | PRECONTACT_SCOPED_PASS |
| [#43583477227](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43583477227) | MoveGroup 실제 사전접근 성공 직후 finger1 목표 12mm `reference` 도달, 실제≈0, native 외부 접촉 0 | RED |
| [#43584052832](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43584052832) | MoveGroup 이후 직접 arm FJT 정밀 보정 1건, 사전접근 양손가락 12mm 실제 추종 | PRECONTACT_SCOPED_PASS |
| [#43584676926](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43584676926) | 정밀 보정 + 자유공간 7개 관절 시험 PASS; 이후 실제 접근 중 원본 20cm 받침대와 손목 네이티브 충돌 667건 | RED |
| [#43585645201](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43585645201) | 시험용 실제 지지대 상면 유지·하부 6mm로 변경해 손목 간섭 0. finger1 선행 닫힘으로 원통 world Y ≈+10.9mm 이동, finger2 물체 접촉 중 q≈0 | RED |
| [#43586210350](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43586210350) | 실제 충돌면 기준 대칭 11mm 동시 닫힘, finger1 실제11mm, finger2≈0, 이때 native finger2↔rod 접촉 0 | RED |
| [#43586568591](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43586568591) | 최종 MoveGroup 접근 이후 실측 팔 자세 직접 FJT 정밀 보정 실제 성공, 그래도 물리 닫힘 finger2≈0 | RED |
| [#43587221825](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43587221825) | **실제 실패 당시 최종 팔 자세 그대로** 빈 월드, 직접 arm FJT 이후 단일 finger2 11mm → 실제 10.986mm | POSE_ONLY_FREE_SPACE_SCOPED_PASS |
| [#43587538228](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43587538228) | 같은 빈 월드·동일 관절 목표에서 MoveGroup 실제 팔 Action으로 경로만 변경, finger2 11mm→실제≈0, FJT ABORTED(-5) | CONTROL_PATH_RED |
| [#43588053392](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43588053392) | MoveIt OMPL `plan_only` 경로를 직접 arm FJT로 실제 실행. pregrasp→삽입→최종 정렬 모든 팔 관절 목표 PASS. 실제 물리 닫힘은 finger1 11mm, finger2≈0, **양 손가락 native rod 접촉 0**, FJT ABORTED(-5) | G04B RED |

### 가장 최근 공개 원본 Artifact 및 체크섬

- [#43586568591 Artifact #14110703166](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43586568591/artifacts/14110703166): `99b64e3d7d2bd6a45ad56eb4ce64256a219b7961fa3363f105c26c3db7ea8abd`
- [#43587221825 Artifact #14109999369](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43587221825/artifacts/14109999369): `a9af459319aaccc3b48f645deddf36ec7d93271539a4d2c1b8105257ac97b13e`
- [#43587538228 Artifact #14111650082](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43587538228/artifacts/14111650082): `afa4db8ca5d1e57b24f61677b6c9ea85898d129aed3e740422519bc305579f3e`
- [#43588053392 Artifact #14111330810](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43588053392/artifacts/14111330810): `33ae2870dc1db2e1f556aad12242c5d0cb495789915d79e00ec973522935752a`

## 3. 아직 원인을 확정할 수 없는 이유

동일한 최종 arm 자세에서 *ground-only / direct arm FJT*는 finger2 실구동 성공이지만, *ground-only / MoveGroup 실제 팔 실행*에서는 finger2가 0이다. 이는 **MoveGroup 실행 경로가 유의미한 변수임을 실측**한 것이다. 그러나 완전한 G04B 물리 월드에서는 MoveIt 경로 계획 결과를 **직접 FJT로 실행해도** finger2가 0이다. 따라서 “MoveGroup 실행만 제거하면 해결”이라는 결론은 반증됐다.

원본 물체 접촉이 **0건인 채 finger2가 움직이지 않는 기록**도 존재하므로, 현재 실패를 원통의 물리 접촉만으로 설명하거나 즉시 그리퍼 목표 허용오차를 늘려서는 안 된다. GazeboSimSystem의 finger2 음의 축 SDF 매핑, 접촉 플러그인의 동역학/스케줄링, 팔 동작 이력 및 실제 월드 구성의 상호작용은 미확정이다.

## 4. 다음 세션에서 이어야 할 정확한 단일 실험

1. G04B 전체 파지 런 재실행 전에, **실제 물리 지형과 동일한 ROS-Gazebo 컨트롤러를 사용하면서 finger2가 q≈0에 남는 시점의 전체 JTC `reference/feedback/error`와 실제 `/joint_states` 시계열을 원본으로 보존**한다. 기존 witness는 마지막 100개 controller 샘플만 저장하므로, 진단용으로 최대 약 1,000개 원본 샘플 및 Goal 구간별 min/max를 기록하되 판정 자체는 변경하지 않는다.
2. 앞서 성공한 최종 자세 *ground-only* 시험의 전체 245개 JTC 표본을 보존하여 정적 오프라인 비교한다. 실제 적용한 joint2 음의 축 SDF/URDF, native Gazebo joint position/velocity를 읽기 전용으로 대조한다. 어떤 명령 인터페이스가 필요한 물리 조건에서만 추종하지 않는지 **직접 증거로 구분**한다.
3. 원인이 입증된 1개 관절·1개 물리 경계만 테스트 전용으로 수정, 한 번의 공개 CI로 검증한다. 그 전에는 반복 full G04B, 임의 fixture 파라미터 변경, tolerance 완화, 강제 attach/teleport를 금지한다.
4. **두 원래 손가락 구동이 실제 물리 월드에서 입증된 경우에만** G04B 동일 세션 양측 native 물리 접촉력 → world Z 상승 ≥0.05m → 상대 자세 안정 ≥1초 → 목적 영역 release/정착으로 복귀한다. 해당 G04B 원본 인수 전에는 G05 동일 실제 RGB-D부터 최종 물리 배치까지 시험·출판 PASS 불가.

## 5. 브랜치·PR 판정

- 기준 합격 소스 `main@9431fb5` **그대로 유지**. 관련 [Draft PR #180](https://github.com/silverbjin/Pysical_AI_ROS2/pull/180), [#182](https://github.com/silverbjin/Pysical_AI_ROS2/pull/182), [#183](https://github.com/silverbjin/Pysical_AI_ROS2/pull/183), [#184](https://github.com/silverbjin/Pysical_AI_ROS2/pull/184), [#185](https://github.com/silverbjin/Pysical_AI_ROS2/pull/185)는 전부 **미병합**. 테스트 가설을 합격 브랜치로 병합하지 않는다.
- **Issue #181: OPEN/BLOCKED**, 부모 **Issue #173: OPEN/BLOCKED**, 총괄 **Issue #118: OPEN**, **Ch10 Issue #123: HOLD**.
- 사용자 WSL2 GUI 인수는 아직 필요 없음. 공개 CI에서 실제 물리 G04B 증거를 확정한 뒤, G05를 진행하고 현장 요청한다.
