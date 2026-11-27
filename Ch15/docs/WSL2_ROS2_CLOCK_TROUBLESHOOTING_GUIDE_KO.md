# WSL2 ROS 2 Clock 장애 진단
REALTIME은 UTC 조정 영향을 받으며 MONOTONIC은 역행 방지와 경과 시간 기준이지만 Linux 주파수 보정 영향을 받을 수 있다. RAW는 Linux NTP discipline의 영향을 받지 않는 하드웨어 기반 경과 시간이며 절대 정확성 보장은 아니다. BOOTTIME은 suspend를 포함한다. Windows QPC와 guest monotonic은 epoch가 다르다. ROS SYSTEM_TIME/STEADY_TIME/ROS_TIME의 관계는 use_sim_time 및 /clock 설정에 따라 달라진다.
시간 읽기 전후의 monotonic bracket과 장기 구간의 경과 시간 차이를 이용한다. 계측 공백과 실제 step을 분리한다. F06 사례에서는 실제 센서 간격 약 100ms임에도 ROS stamp 약 3.031초 간격이 나타나 안전 래치가 정상 차단하였다. timeout 완화/자동 latch 해제/타임스탬프 덮어쓰기 금지.
진단 순서: Windows UTC/QPC 및 NTP query → Hyper-V/WSL clocksource 및 timex → guest 서비스 → Docker → ROS. R09 guide에 따라 원샷 수집한다. 데이터는 원본 해시와 정제된 보고서를 분리한다.
복원 절차: 원인 후보를 독립 계측으로 반증한다. 변경 전에 원 설정과 복구 명령을 보존하고 승인 후 단일 변경만 적용한다. 동일 조건 재계측 후 개선 없으면 원 설정으로 복원하고 재계측한다. 아직 이 사례의 승인된 변경/복원 명령은 없다. 근거 없이 w32time/Hyper-V/NTP 비활성화 또는 clocksource 강제 금지.
