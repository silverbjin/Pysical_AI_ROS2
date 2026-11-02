# R5 동결 인수 보고서

**결과: PASS**. 이 표는 실제 실행 JSON에서 자동 생성했다. FAIL/미실행을 성공으로 간주하지 않는다.

고정본: `section_13_5_reuse_acceptance_v3.json`, SHA256 `c4f40b5d10a9a87b7ae7edc82c45cc77e51696e850c43f72c73c4ff77f73bc6a`. 필수 각1회;3회 반복은 미실시 확장이다.

| 시나리오 | 증거 | 실행/독립검증 | terminal | 실제 위치 오차 m | 정착 wall s |
|---|---|---|---|---|---|
| free | [ea2a6075](../evidence/section_13_5_reuse/ea2a6075-6b10-4291-8167-f8325e2b2637/RUN_REPORT_KO.md) | PASS/PASS | 4 | 0.05050649560733046 | 1.6310445000000016 |
| obstacle | [0919f36a](../evidence/section_13_5_reuse/0919f36a-f40d-41a4-bdd0-66fb77cd235c/RUN_REPORT_KO.md) | PASS/PASS | 4 | 0.04102902810966663 | 1.4446693699999997 |
| blocked | [cf2d34d2](../evidence/section_13_5_reuse/cf2d34d2-1b24-4669-910f-399ea886aa08/RUN_REPORT_KO.md) | PASS/PASS | 6 | 2.2489004920358275 | 3.9100000009284486e-05 |
| cancel | [c1caa48c](../evidence/section_13_5_reuse/c1caa48c-3357-4583-bf0f-9f725b222b65/RUN_REPORT_KO.md) | PASS/PASS | 5 | 2.1888175731049504 | 1.8489568759999884 |
| vision | [3b1fcc07](../evidence/section_13_5_reuse/3b1fcc07-525d-4211-806e-72249a78b9be/RUN_REPORT_KO.md) | PASS/PASS | 4 | 0.052764297430114675 | 1.897058109999989 |
| raw_loss | [80a22757](../evidence/section_13_5_reuse/80a22757-7888-49e2-8ddb-420992158fd1/RUN_REPORT_KO.md) | PASS/PASS | 5 | 2.168269633265024 | 1.4625651540000035 |

세부 고장·정착 metrics·실제 RGB-D hash/과거TF·정상 회수는 각 실행 보고서와 JSON을 따른다. 도달 불가는 비어 있는 목표와 통로 차단을 사용한다. raw 손실은 소유 경계 PID를 일시 정지했다 복귀시켜 만료와 자동 재개 금지를 확인한다.

## 검증 범위

MuJoCo, 고정 장애물, engine ground-truth localization, 붉은 고정 작업물의 실제 RGB-D 표면 관측과 위치 IK다. 충돌 형상 기반 카메라 화면이며 일반 인식·AMCL/SLAM·Gazebo·실기·MoveIt/파지·동적 물체 추적은 검증하지 않았다. 기본10Hz와 선택15Hz를 구분하며 이 고정본의 비전 인수는15Hz다.

원본13.3/13.4의 별도 회귀, 신규 isolated 설치 감사, 출처·환경 및 게시 SHA는 최종 종합 보고서에서 따로 기록한다.

## 판정과 배포 확인

terminal4는 성공,5는 실제 취소,6은 도달 불가 종료다. blocked는 처음부터 정착 상태였으므로 표의 작은 추가 대기값은 감속 성능을 뜻하지 않는다. cancel/raw_loss의 남은 목표 거리는 미도착을 그대로 기록한 값이며, 실제 이동과 취소/정착을 별도 검사했다.

최종 신규89개 검사27.817s, 기존 관련 순수 회귀50개1.74s, 새 isolated 설치32항목과 외부94자산 hash 감사 PASS다. 전체500Hz 관측에서 original torque cap ratio는1.0 이하이고 native hinge 제한 soft overrun은 최대0.000526rad 미만이었다. 카메라·원본 RX/worker·부모·launch 자식61개를 정상 회수했고 촬영 worker와 tracker PID도 소멸했다. 여섯 실행 모두 post residual/engine lock PASS다.

실행별 engine sim/wall 시간은 원본 engine.json에 기록한다. 빌드·검사·실행을 동시에 돌리지 않았다. 능동 분석 공수의 정확한 합계를 날짜 차이로 산출하지 않는다. v1/v2 실패와 취소 검증 누락은 별도 보고서/추가 재분석으로 보존했다. 최종 publisher의 local/remote SHA 대조는 게시 확인 보고서가 기록한다.
