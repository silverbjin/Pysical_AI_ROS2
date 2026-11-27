# G09 WSL2 사용자 인수 (고정 실행 PIN)
## 1. 검증 범위
Linux CI 새 공통 실행기에서 build/mock/cube/joint/faults(F06), ICD/markers/contract/design 실제 PASS. 기존 G04 physical basic V6 성공 계승, 신규 positive native wrapper와 all 전체 실행 NOT_RUN. WSL2 L3 NOT_RUN. GUI 별도 사용자 시각 검수. Full physical 및 physical fault BLOCKED.

## 2. 환경
WSL2 Ubuntu24.04 amd64, Python3, Git, curl, Docker Desktop WSL integration 또는 Docker Engine (docker info), 가용 CPU≥4, 충분한 디스크. Docker image digest 고정, 필요한 apt/pip 격리 컨테이너에서만 설치. GHCR 접근 필요 시 사용자 인증으로 docker login ghcr.io (토큰 로그 금지). Native physical은 별도의 clean Ch13 checkout pinned main 1931cac92585fc155357880b584c72c76d67257c, 기존 승인된 94개 자산/lock 및 검증 venv/build 필요. CH15_NATIVE_ROOT, CH15_ASSET_APPROVAL, CH13_REUSE_BUILD, CH13_REUSE_VENV 절대 경로; native 환경을 임의로 덮어쓰지 않는다.

## 3. 고정 실행기 다운로드
```bash
export CH15_SOURCE_SHA=70ed8b509809b09db26f57e4f9a7aea9f83d095c
export CH15_BOOTSTRAP_SHA256=40c306ac8cf2ff7e652e9b36e3f880f771e2f9276ec17a5589a5e149d403c606
export CH15_WORK_ROOT="$HOME/ch15-owner"
mkdir -p "$CH15_WORK_ROOT"
curl -fsSL "https://raw.githubusercontent.com/silverbjin/Pysical_AI_ROS2/$CH15_SOURCE_SHA/Ch15/scripts/bootstrap_ch15.sh" -o "$CH15_WORK_ROOT/bootstrap_ch15.sh"
```

Native 환경과 승인 JSON의 실제 경로가 준비된 경우 아래 단일 실행으로 all 인수 시도. 사전조건 누락 시 실행 전 BLOCKED (exit2); all 전체는 이번 CI에서 재실행하지 않았다.
```bash
# 실제 준비된 환경의 절대 경로로 네 환경변수를 먼저 export할 것:
# CH15_NATIVE_ROOT CH15_ASSET_APPROVAL CH13_REUSE_BUILD CH13_REUSE_VENV
bash "$CH15_WORK_ROOT/bootstrap_ch15.sh" --check all --headless --acknowledge-assets
```
Native 준비가 안 되면 다섯 격리 경로만 별도 실행한다 (physical 또는 all PASS 아님).
```bash
for check in build mock cube joint faults; do
  bash "$CH15_WORK_ROOT/bootstrap_ch15.sh" --check "$check" --headless || break
done
```
all 순서 build→mock→physical_basic→cube→joint→faults. all과 개별 경로를 중복 실행하지 않는다. faults 단독 대표 F06만 확인하려면 --check faults --scenario F06 --headless. 다른 상세 절별 경로는 LAB 가이드 참조.

## 4. 증거 제출
터미널 CH15_OWNER_EVIDENCE 및 CH15_ARCHIVE_SHA256. 각 run의 .evidence.tar.gz와 .sha256, .archive-verification.json은 $CH15_WORK_ROOT/runs/ 아래 생성. exit0 scoped pass/1 fail/2 blocked/130 canceled. 원본 MCAP·외부 모델은 로컬에 보존하고 공개 업로드 금지; 필요한 경우 정제 영수증만 제출. WSL2 L3와 main merge는 실제 증거 검토 및 승인 후에만 결정.
