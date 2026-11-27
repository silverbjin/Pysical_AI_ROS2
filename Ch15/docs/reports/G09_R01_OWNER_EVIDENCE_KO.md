# G09-R01 — WSL2 인수 증거 고정
실행 PIN 70ed8b509809b09db26f57e4f9a7aea9f83d095c, bootstrap 40c306ac8cf2ff7e652e9b36e3f880f771e2f9276ec17a5589a5e149d403c606. 첨부 원본 5개를 다시 열어 외부 SHA 및 manifest 157/157을 검증했다. 각 소스 영수증 368개, bootstrap verified true. 원본은 사용자 로컬 보존, 원본 MCAP/환경 로그는 공개 Git 미업로드. [영수증](../../evidence/g09/owner_l3_r01_receipt.json)에 archive SHA 및 manifest SHA 고정.
| 경로 | 판정 | 파일 |
|---|---|---:|
| build | PASS | 25 |
| mock | PASS | 37 |
| cube | PASS | 29 |
| joint | PASS | 34 |
| faults | FAIL | 32 |
4개 성공 경로 반복 금지. F03 transient 첫 탐색에서 Scan stamp 증가 3027390005ns / monotonic 증가100081208ns, 차이2927308797ns. Watchdog 최초 latch receipt age34.413591ms, exact nav terminal4, END ABORTED, all_terminal true, child7/7 exit0. 다른 장애4종 NOT_RUN; graph audit 미실행. 소스 시간 불연속은 확인했지만 Windows/WSL2 시간 조정 원인은 미확정. 안전 latch 해제/허용 age 완화/타임스탬프 덮어쓰기 금지. R02 read-only host/container/ROS clock 진단, R03 deterministic forward/rewind safety test, R04 환경 분류, R05 F03 단독, R06 나머지. Main HOLD.
