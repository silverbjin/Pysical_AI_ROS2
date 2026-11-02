# R5 동결 인수 보고서

**결과: FAIL**. 이 표는 실제 실행 JSON에서 자동 생성했다. FAIL/미실행을 성공으로 간주하지 않는다.

고정본: `section_13_5_reuse_acceptance_v1.json`, SHA256 `48ead0ae2fb0868e8036c2c464904bb62a841e86c7bed2f7da36696a78198782`. 필수 각1회;3회 반복은 미실시 확장이다.

| 시나리오 | 증거 | 실행/독립검증 | terminal | 실제 위치 오차 m | 정착 wall s |
|---|---|---|---|---|---|
| free | [eb4cf77b](../evidence/section_13_5_reuse/eb4cf77b-ae6c-4e27-812f-d54d88f43503/RUN_REPORT_KO.md) | FAIL/NOT_RUN | 5 | None | None |
| obstacle | [4a2d7f11](../evidence/section_13_5_reuse/4a2d7f11-8548-4986-bba3-6a59f92c90cb/RUN_REPORT_KO.md) | PASS/PASS | 4 | 0.04299810386716916 | 1.8598258370000025 |
| blocked | [6f846088](../evidence/section_13_5_reuse/6f846088-498a-46ad-8e02-92c1aaf58254/RUN_REPORT_KO.md) | PASS/PASS | 6 | 2.24913542359228 | 5.8478999989119984e-05 |
| cancel | [7ea779c4](../evidence/section_13_5_reuse/7ea779c4-ba0f-4371-86b8-24cb06f7b54f/RUN_REPORT_KO.md) | PASS/PASS | 5 | 2.206290263852297 | 1.9864356219999877 |
| vision | [f93779fc](../evidence/section_13_5_reuse/f93779fc-47a2-4acc-a0c5-766c6be09f80/RUN_REPORT_KO.md) | FAIL/NOT_RUN | 5 | None | None |
| raw_loss | [9b2672e5](../evidence/section_13_5_reuse/9b2672e5-2758-41f9-8fc0-6a666e4294e5/RUN_REPORT_KO.md) | PASS/PASS | 5 | 2.233893914345554 | 0.9596518019999962 |

세부 고장·정착 metrics·실제 RGB-D hash/과거TF·정상 회수는 각 실행 보고서와 JSON을 따른다. 도달 불가는 비어 있는 목표와 통로 차단을 사용한다. raw 손실은 소유 경계 PID를 일시 정지했다 복귀시켜 만료와 자동 재개 금지를 확인한다.

## 검증 범위

MuJoCo, 고정 장애물, engine ground-truth localization, 붉은 고정 작업물의 실제 RGB-D 표면 관측과 위치 IK다. 충돌 형상 기반 카메라 화면이며 일반 인식·AMCL/SLAM·Gazebo·실기·MoveIt/파지·동적 물체 추적은 검증하지 않았다. 기본10Hz와 선택15Hz를 구분하며 이 고정본의 비전 인수는15Hz다.

원본13.3/13.4의 별도 회귀, 신규 isolated 설치 감사, 출처·환경 및 게시 SHA는 최종 종합 보고서에서 따로 기록한다.
