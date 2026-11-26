# 14.1 실습 — 실제 YOLOv8 CPU 계측 (검증 후보)

> 출고 상태(2026-11-26): [최신 인수 원장](CH14_ACCEPTANCE_LEDGER.md), [출판 QA](reports/G09_RELEASE_CLOSEOUT_QA_20261126_KO.md) 우선. 아래 기존 checkpoint는 역사적 증거이며, G09 WSL2 L3는 14.9의 네 선택 경로에만 해당합니다. 전체 출고 HOLD, 권리 및 범위 승인 필요. 실제 실행 PIN은 G09_WSL2_OWNER_ACCEPTANCE_KO.md를 참조합니다.

고정 CPU lock 및 원본 체크포인트 해시 확인 후 Ch14에서 실행. 가중치 사용 조건 확인 후 `python scripts/fetch_models.py yolov8n --cache /absolute/models --fetch --acknowledge-agpl`. GPU 기본 아님. `python python/benchmark_torch.py --manifest models/model_manifest.json --cache /absolute/models --model yolov8n --threads 1 --warmup 10 --iterations 100 --output evidence/t01_1`. 2 threads 별도 출력으로 비교. 모델 순수 forward, 전송 제외, CUDA explicit sync. 실제 device/threads/affinity, CSV, P50/P95/P99, 평균/std/max, 그래프 확인. 모델 파일 크기는 export 결과에서 확인. 예상 수치를 PASS로 대체 금지. CPU CI 및 owner WSL2는 분리. 현재 신규 실행 전 후보; 실제 결과 보고서 참조.

## 실제 CPU 검증
Run 45744146299: 1 thread 147.36367963ms 평균, 2 threads 96.65377883ms, 각 100 samples, 10 warmups. P95 155.2705937/103.3305025ms. 실제 GitHub Actions 4 affinity CPU, transfer 제외. [원본 CSV/plot](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45744146299/artifacts/15081689764). WSL2 성능 보장 아님.
