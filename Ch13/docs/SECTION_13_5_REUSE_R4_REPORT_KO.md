# R4 실제 촬영·작업 위치 접근 완료 보고서

**개발 단계 PASS.** R5의 별도 고정본 전수 인수는 아직 남아 있다. 아래 값은 실제 실행 JSON에서 생성했다.

실행 UUID: [35857406-1e97-43da-89cd-f793e767cf46](../evidence/section_13_5_reuse/35857406-1e97-43da-89cd-f793e767cf46/RUN_REPORT_KO.md).

| 항목 | 실제 결과 |
|---|---|
| NavigateToPose terminal | 4 (SUCCEEDED) |
| 실제 이동 | 0.978432 m |
| 실제 위치/방향 오차 | 0.037869 m / 0.009163 rad |
| terminal 뒤 실제 정착 | 1.667734 wall s |
| 정착 독립 검증 | PASS; 251 samples / 1.104734 wall / 0.500000 sim s |
| 최종 촬영 원본 age | 0.118387 wall s |
| 최종 IK 위치 잔차 | 0.004261 m; jointlimit/collision PASS |
| 처리 선택 | 15.0 wall Hz; default10Hz 전체 접근 PASS를 주장하지 않음 |
| 힘 cap 비율 | 1.0 |
| 정상 회수 | launch 11/11; 잔여 []; renderer exit0+join |

## 증거 의미

실제 Renderer RGB/depth의 색 영역·축방향 depth를13.4 geometry로 역투영했다. 관측 노드에는 작업물 정답 좌표를 입력하지 않았다. goal header는 후보 계산 후 받은 실제 새 촬영 원본 stamp다. 최종 READY는 성공 terminal+실제 root오차+정착+fresh observation+실제 root/joint의 IK 뒤 발행했다. 팔 명령·파지 실행은 하지 않았다. 저장 RGB/depth/calibration/TF로 점을 독립 재계산해 일치를 확인했다.

[85개 회귀](../evidence/section_13_5_reuse/r4_preflight/tests_85_reliable_camera.log) PASS/29.098s. 카메라 생존 확인은 완전한 RGB-D/hash/calibration/과거TF에서 수행하며 인식 cap과 분리한다. 오래된·손상된 촬영과 중복 재수신은 health를 갱신하지 않는 회귀를 포함한다. 물체 점은 goal 승인과 최종 인계에서 신선도를 별도 요구하며, 물체 검출 손실은 latch한다.

## 보완과 실패 이력

[S1](SECTION_13_5_REUSE_R4_S1_REPORT_KO.md), [S2](SECTION_13_5_REUSE_R4_S2_REPORT_KO.md)의 실패를 보존했다. 이후55e9·876d·ef88·469f도 FAIL 원본을 보존한다. 고정300ms 계약을 확대하지 않고, 촬영/scan wall cadence·renderer 별도 프로세스·프로세스 내부 CPU 추론 제한·C++Release·네 촬영분 relay·camera Reliable depth2로 실행 경로를 정리했다. 고해상도 장식 메시 대신 원본 충돌 형상을 촬영하는 교육용 시각 profile을 명시한다. 원본 모델 동역학·가중치·명령규약·2ms/50Hz·모터cap은 유지한다.

R5 준비로 blocked를 비어 있는 목표+전폭 장벽으로 바꿨고 연결성 RED→GREEN을 확인했다. raw 손실 도구는 소유 publisher PID를 pause/restore하여 실제 TTL과 자동 재개 금지를 시험하도록 했다. 실행 경로는 저장소 위치와 별도 build/venv 변수를 지원한다. R5에서 새 install과 여섯 실제 시나리오를 다시 동결 인수한다.
