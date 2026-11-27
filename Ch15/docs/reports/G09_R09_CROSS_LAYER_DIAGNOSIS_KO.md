# G09-R09 교차 계측 구현 및 범위 제한 검수
R08/R09 실행 PIN bd07d22da44e725e36ff2099b64f76f7b5e688c2.
EVIDENCE: F06 host/container/ROS clock step 동반, 후반 RAW/MONOTONIC 상대율 9.0962%.
HYPOTHESIS: guest discipline / host synchronization / clocksource를 분리해야 한다.
FIX: QPC RPC bracket, elapsed rate bounds, C adjtimex modes=0, idle/load 구분, 기존 digest-pinned Docker image pull 금지 및 read-only mount, NTP query only. 
GREEN: 실제 GitHub Actions run 46014690435, Linux job 140558701631 및 Windows parser job 140558701292 success. 17 unit tests, Linux 12초 live smoke, short smoke not accepted, scope diff PASS. Artifact 15205386857, GitHub reported SHA256 e0d99c49f9d86a961e78883bc5fca6dca5e6bc76954c24b43fe96fca3f31582d. 독립 artifact bytes 검증 미수행.
REVIEW: 실제 WSL2/Hyper-V/Docker 사용자 검수 NOT_RUN. Windows parser PASS는 실행 검증이 아니다. 외부 UTC는 NTP 응답 품질에 의존하며 QPC도 절대시간 기준이 아니다. provisional 1000ppm, 600초, 100ms step 기준은 환경 진단 후보이며 안전 threshold와 무관하다. 제어된 simulation clock의 별도 검수 및 sleep/resume 재현은 원인 관련성 확인 후 필요. 기존 로봇 안전 코드 무변경.
NEXT: 사용자 원샷 증거, 최초 경계 확인, 단일 변경 승인 및 변경 전후 동일 계측.

Bootstrap independent source-download QA: run 46015190135 completed success; Linux 140560398573, Windows 140560399151. VerifyOnly checks all seven hashes without WSL launch; actual WSL2 NOT_RUN. Bootstrap blob 4c9c26d8fae3472ee5124e9c525098e627aa0037, SHA256 836c89750a891cffd4e23bb5906f7fccfadfcc3d5f224d0f8dc953249746b77b, immutable commit cefd11e02c780392b8b8f2816840e3ee25a87499. G01-G07 tag refs directly rechecked 7/7. No merge.
