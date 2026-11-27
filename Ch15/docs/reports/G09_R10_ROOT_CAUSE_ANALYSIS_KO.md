# G09-R10 근본 원인 분석 — HOLD
관측: 9101 host samples, 15 forward/3 backward; 후반 세 실행 RAW/MONO 상대율 +9.0962%, 반복 전진 보정 약 32.365초 및 2.94초. F03 transient 70–80초 상대율 전환. F06 scan monotonic 간격 약 100ms이나 ROS stamp 3.031초.
가설 A: guest timex tick/discipline 왜곡. RAW가 정확하다는 조건에서 MONO/RAW=0.91662, nominal tick 10000us일 경우 약 9166us 예측. timex 실제값과 QPC rate로 반증.
가설 B: Hyper-V host/guest time correction. Windows QPC/UTC 안정, guest REALTIME step만 존재하면 guest 경계 우선; Windows UTC 동시 step이면 host 경계 조사.
가설 C: Windows W32Time/NTP. QPC/UTC 및 외부 NTP와 서비스/event log 교차검증. 서비스 활성 여부만으로 인과 확정 금지.
가설 D: clocksource/TSC. RAW vs QPC rate와 kernel/clocksource 상태 확인. Docker/ROS는 동반 step 전파 증거가 있으나 독립 원인 여부는 교차 계측.
관련 자료: https://github.com/microsoft/WSL/issues/12583 ; https://github.com/microsoft/WSL/issues/11790 ; https://docs.kernel.org/virt/hyperv/clocks.html ; https://man7.org/linux/man-pages/man2/adjtimex.2.html . 유사 이슈는 원인 확정 증거 아님.
판정 UNKNOWN. 실제 사용자 환경 데이터 없이는 채택/기각 및 변경 금지.
