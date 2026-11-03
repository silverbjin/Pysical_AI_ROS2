# R5 동결 인수 보고서

> 해석 보완: 이 판의 취소 PASS는 verifier가 platform 최종 fault와 실제 움직임을 빠뜨린 결과다. 실제 이동 약1.3mm와 SOURCE_REORDER:safe가 있어 최종 인수 증거로 사용하지 않는다. 원본 JSON은 그대로 보존하고 별도 v3 재분석에서 FAIL을 확인했다. raw_loss는 실제0.337870m·platform fault 없음으로 별개이며, 최종판에서는 다시 실행한다.

**결과: FAIL**. 이 표는 실제 실행 JSON에서 자동 생성했다. FAIL/미실행을 성공으로 간주하지 않는다.

고정본: `section_13_5_reuse_acceptance_v2.json`, SHA256 `7cf18354a087153349a2c75f7919d0c7381318912fbee5a90d7b35d87927f2f8`. 필수 각1회;3회 반복은 미실시 확장이다.

| 시나리오 | 증거 | 실행/독립검증 | terminal | 실제 위치 오차 m | 정착 wall s |
|---|---|---|---|---|---|
| free | [e42811f6](../evidence/section_13_5_reuse/e42811f6-8233-4ba1-abbe-ca4abf2a04a9/RUN_REPORT_KO.md) | FAIL/NOT_RUN | 6 | None | None |
| obstacle | [bee76014](../evidence/section_13_5_reuse/bee76014-abc7-4086-a7c2-25319ca3378e/RUN_REPORT_KO.md) | FAIL/NOT_RUN | 6 | None | None |
| blocked | [fd6bcda2](../evidence/section_13_5_reuse/fd6bcda2-fc6b-48ac-aa3c-4cadc79ee76b/RUN_REPORT_KO.md) | PASS/PASS | 6 | 2.2490694293037956 | 5.390300000840398e-05 |
| cancel | [f5c2285d](../evidence/section_13_5_reuse/f5c2285d-6972-456b-9deb-fa765f0b6156/RUN_REPORT_KO.md) | PASS/PASS | 5 | 2.4999887996395196 | 4.110199998308417e-05 |
| vision | [59268844](../evidence/section_13_5_reuse/59268844-61a3-4d8e-a21f-c1127788a454/RUN_REPORT_KO.md) | FAIL/NOT_RUN | 6 | None | None |
| raw_loss | [8f962ac5](../evidence/section_13_5_reuse/8f962ac5-7b0d-4305-b9fc-7e70f56584f9/RUN_REPORT_KO.md) | PASS/PASS | 5 | 2.1611475729080394 | 1.443374929000015 |

세부 고장·정착 metrics·실제 RGB-D hash/과거TF·정상 회수는 각 실행 보고서와 JSON을 따른다. 도달 불가는 비어 있는 목표와 통로 차단을 사용한다. raw 손실은 소유 경계 PID를 일시 정지했다 복귀시켜 만료와 자동 재개 금지를 확인한다.

## 검증 범위

MuJoCo, 고정 장애물, engine ground-truth localization, 붉은 고정 작업물의 실제 RGB-D 표면 관측과 위치 IK다. 충돌 형상 기반 카메라 화면이며 일반 인식·AMCL/SLAM·Gazebo·실기·MoveIt/파지·동적 물체 추적은 검증하지 않았다. 기본10Hz와 선택15Hz를 구분하며 이 고정본의 비전 인수는15Hz다.

원본13.3/13.4의 별도 회귀, 신규 isolated 설치 감사, 출처·환경 및 게시 SHA는 최종 종합 보고서에서 따로 기록한다.
