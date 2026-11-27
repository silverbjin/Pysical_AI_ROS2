# G09-R03 실제 시계 전진·역행 안전 회귀시험
판정 PASS_SCOPED_R03_CONTROLLED_ROS_CLOCK_GUARD. [CI 45979686052](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45979686052), job140440118378, artifact15189555018, source 170adb7a7d3c90a700cfac1d0ce445b1939e7c4a; ZIP SHA256 6b90a9d6c1c9168f85cc21d189f28ad90caa75226fca6c380dcac98bf0ecb368, 16/16 내부 독립 검증.
| 항목 | 전진 +2.927308797s | 역행 -0.5s |
|---|---:|---:|
| trigger→Guard 관측 |21.985171ms|21.715824ms|
| trigger→Arbiter latch 관측 |50.254477ms|50.158953ms|
| native Scan 수신 age|21.348330ms|21.074056ms|
| native block→zero publish 완료|0.071028ms|0.072559ms|
| 새 Scan 복구 후 nonzero/clear|0/0|0/0|
3개 패키지 실제 build, 기존 watchdog/arbiter 원본 클래스 사용, 4/4 child exit0, 강제0, domain97/98 10개 잔여 그래프 샘플씩 0. 두 사례 각각 positive mock output 5개 이전 확인. 스캔은 끊기지 않으며 source stamp는 점프 전의 값으로 유지되어 age 위반. 회복 시 새 ROS 시간에 맞는 실제 fresh scan 공급 후에도 래치 유지.
범위: 독립 /clock fixture의 실제 ROS DDS/안전 출력이며 OS 시스템 시간 변경 아님. 전체 mission/UUID/epoch acceptance를 새로 주장하지 않는다. G08 F10 BlackboardContext L0 evidence 및 steady timeout retained. 원래 WSL2 발생 원인 미확정. R04 archive 분류로 이어감; owner 4/5 partial, main HOLD.
[receipt](../../evidence/g09/r03_receipt.json).
