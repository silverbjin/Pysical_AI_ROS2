# G09-R02 읽기 전용 시간 불연속 진단
R01 원본 4/5 owner 결과를 재사용한다. 본 변경은 안전/runtime 알고리즘 변경 아님.
- host MONOTONIC으로 각 REALTIME/BOOTTIME/MONOTONIC_RAW 읽기 bracket; 컨테이너 ROS SYSTEM_TIME/STEADY_TIME/실제 Node ROS_TIME 동시 수집. host는 별도 프로세스, container_idle은 독립 노드(domain96), 실제 fault probe에서는 node clock을 기존 관측 루프에서 읽는다.
- offset interval [value-m1,value-m0], 연속 interval 차이의 lower/upper bound. 100ms는 진단 전용 threshold, 5ms 초과 bracket 또는 250ms 초과 sample gap은 coverage 불완전. ROS sim time은 시스템 시간 비교 대상 제외. BOOTTIME/RAW 차이는 별도 기록; Windows 시간 조정 원인 자동 추론 금지.
- 50ms cadence, read-only host/ROS, no settime, no /clock publisher. 정상 안전 임계값 300ms/1s/heartbeat 그대로. 시간 step 발견해도 PASS 강제/자동 재시도 없음. CI는 R02 contract9, standalone pinned launcher 및 F03 transient 대표 actual instrumented path만 수행. R03 forward/rewind safety injection 별도.
- 결과는 owner archive에 host-clock/samples.jsonl, summary.json, container-clock/ 또는 F03 clock-samples.jsonl, clock-diagnosis.json. 진단 수집 PASS와 시간 안정성 별개. Linux CI PASS로 WSL2 원인 확정하지 않음.