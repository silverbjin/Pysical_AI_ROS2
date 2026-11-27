# R05/R06 WSL2 targeted owner acceptance — 4개 PASS 재실행 금지
기존 owner execution SHA 70ed8b509809b09db26f57e4f9a7aea9f83d095c의 build/mock/cube/joint는 R01에서 증거 보존. 아래는 R02 read-only 진단 추가 실행 PIN 0b044f528ffd99b23d563f32eddf27833dea7566. R02 V1 actual F03 transient PASS, V2 idle apt dependency only. R03 controlled /clock regression2/2 PASS. R04 offline archive classification 별도. Windows/WSL2 원인 자체는 미확정; 시간/안전 기준 변경 금지.
```bash
export CH15_SOURCE_SHA=0b044f528ffd99b23d563f32eddf27833dea7566
export CH15_BOOTSTRAP_SHA256=40c306ac8cf2ff7e652e9b36e3f880f771e2f9276ec17a5589a5e149d403c606
export CH15_WORK_ROOT="$HOME/ch15-owner"
mkdir -p "$CH15_WORK_ROOT"
curl -fsSL "https://raw.githubusercontent.com/silverbjin/Pysical_AI_ROS2/$CH15_SOURCE_SHA/Ch15/scripts/bootstrap_ch15.sh" \
  -o "$CH15_WORK_ROOT/bootstrap_ch15.sh" && (
  set -e
  for scenario in F03_transient F03_persistent F04 F06 F01; do
    bash "$CH15_WORK_ROOT/bootstrap_ch15.sh" --check faults --scenario "$scenario" --headless
  done
)
```
첫 F03_transient 실패 시 즉시 종료. 성공한 경우에만 R06 네 시나리오를 각 독립 run으로 순차 실행. 자동 재시도 없음. 각 프로파일의 원래 result/exit code 유지; fault clock 진단에서 no step observed는 전체 시간 안정성 보증 아님. 각 run local archive + .sha256 제출. host-clock/samples.jsonl+summary.json, F03 등 clock-samples.jsonl+clock-diagnosis.json, 원래 mission/scan/guard traces. OS clock 수정/NTP 변경/sudo 불필요. 원본 MCAP/환경 로그 공개 업로드 금지. 필요 시 독립 idle `--check clock_diag --headless` (진단 수집 자체의 PASS이며 시간 안정 보증 아님). R05/R06 owner NOT_RUN; native physical basic positive 별도 NOT_RUN; main HOLD.
