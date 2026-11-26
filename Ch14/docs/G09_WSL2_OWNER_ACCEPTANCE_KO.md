# G09 WSL2 사용자 인수 안내 — CPU headless Docker 제한 인수 완료
2026-11-26 / OWNER_L3_SCOPED_PASS / Owner L3 scoped PASS / full release HOLD.

## 1. 검수된 고정 실행 소스
PIN `6c458e345236b124c9aa60f65788f35cfed74e62`. Bootstrap SHA256 `0939ce653d896fb84a381e494600d77ce1cbbafd95e4aa86618cff33b7c2e30f`. 보고서/원장 커밋이 이 SHA 이후에 존재해도 실행 PIN을 변경하지 않는다. 원격 main과 무관한 검수 소스이다.

Linux CI 실제 raw bootstrap build+negative drift [45815645513](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45815645513), 실제 세 물리 옵션 [45816276822](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45816276822) 모두 SUCCESS, same exact PIN. Build 6 packages/5.69s; perception actual RGB-D 13/13; MuJoCo 400/400, Gazebo 399/399, both 50Hz and clean exits; every owner invocation exit0, owned container absent, matching source. All four choices exercised separately, not one sequential all CI execution. `--check all` simply invokes four tested branches sequentially; combined owner trial succeeded on user WSL2 on 2026-11-26. Do not repeat successful physical tests in CI. WSL2 native ROS install, WSLg GUI, GPU, stable walking and actual HW are not accepted by this headless run.

## 2. 사전 확인
Windows PowerShell: `wsl -l -v`로 Ubuntu가 version 2인지 확인. Ubuntu 터미널에서 `cd "$HOME"; cat /etc/os-release; uname -a; python3 --version; docker context show; docker info; df -h "$HOME"`. Ubuntu24.04 x86_64/Python3.12, Docker Desktop WSL integration 또는 WSL 내부 Docker Engine 중 하나, Docker daemon 사용 권한 및 네트워크/디스크 필요. Linux filesystem에서만 진행. 기존 작업물, 이미지 및 다른 컨테이너 삭제 금지. 사용자 환경 자체를 직접 조작하지 않음. 이 검수는 Docker 환경이며 native apt/pip 설치와 다름.

## 3. G07 원본 ZIP 및 권리 확인
Actions artifact 15090667475 (run45763347165) original ZIP SHA256 `c8defc1a154c3d0ec92ddd3a7fbd70f8d3b012dc21d375acde9f5c5f9be9641d`, 2,272,024 bytes, internal23/23. 사용자에게 전달한 CH14_G07_ORIGINAL_SMOKE_EVIDENCE.zip을 WSL의 $HOME에 복사. 재압축/대체/신규 학습 금지. 실행기가 원본 ZIP 및 11개 필수 payload를 검증한다. 외부 YOLO/scene terms 확인 후에만 --acknowledge-assets; 실제 로봇 없이 시뮬레이션에서만 --enable-sim-control. 실험 동의는 공개 배포 권리 승인 아님.

## 4. 전체 단일 인수 명령
ZIP을 복사하고 외부 자산 사용 조건에 동의한 경우, WSL Ubuntu 터미널에서 다음 블록을 한 번 실행. 각 경로가 성공한 독립 Linux rehearsal을 재사용한 WSL2 combined trial이다. 전체 순차 all은 CI에서 따로 중복 실행하지 않았다.
```bash
(
  set -euo pipefail
  cd "$HOME"
  PIN=6c458e345236b124c9aa60f65788f35cfed74e62
  BOOT="$HOME/ch14-bootstrap-$PIN.sh"
  ZIP="$HOME/CH14_G07_ORIGINAL_SMOKE_EVIDENCE.zip"
  test -f "$ZIP"
  printf '%s  %s\n' 'c8defc1a154c3d0ec92ddd3a7fbd70f8d3b012dc21d375acde9f5c5f9be9641d' "$ZIP" | sha256sum -c -
  docker info >/dev/null
  curl --proto '=https' --proto-redir '=https' -fsSL --connect-timeout 15 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/Pysical_AI_ROS2/$PIN/Ch14/scripts/bootstrap.sh" -o "$BOOT"
  printf '%s  %s\n' '0939ce653d896fb84a381e494600d77ce1cbbafd95e4aa86618cff33b7c2e30f' "$BOOT" | sha256sum -c -
  CH14_SOURCE_SHA="$PIN" bash "$BOOT" --profile cpu --headless --check all \
    --acknowledge-assets --enable-sim-control --reuse "$ZIP"
)
```
첫 실패에서 중단; 반복 전체 실행 금지. 권리 또는 ZIP 미확보이면 build-only로 제한: 위 블록의 ZIP 검사와 마지막 두 줄 대신 `CH14_SOURCE_SHA="$PIN" bash "$BOOT" --profile cpu --headless --check build`만 사용 (bootstrap 다운로드/해시는 동일). 개별 경로는 --check perception --acknowledge-assets / --check mujoco 또는 gazebo --enable-sim-control --reuse "$ZIP". 이전 성공 증거를 유지하고 실패 경로만 재개.

## 5. 증거 제출 및 판단
마지막 `CH14_OWNER_EVIDENCE=/home/.../evidence.tar.gz`와 같은 경로의 .sha256을 제출. 실제 출력 경로로 `ARCHIVE=/absolute/.../evidence.tar.gz; sha256sum -c "$ARCHIVE.sha256"; tar -tzf "$ARCHIVE" | head -30`. 성공/실패/취소 모두 원본 제출. owner-result.json의 status, exit_code, stage, source_sha==actual_source_sha, level=WSL2_OWNER_REVIEW_REQUIRED를 검토한다. Exit0은 요청 범위만 성공, 2 BLOCKED, 130 취소, 1 FAIL. 스크립트 다운로드 이전 실패 등 archive가 없는 경우 터미널 로그 제출. 실제 L3 승격은 원본 검토 후만 가능. 사용자 인수 준비와 인수 완료는 구분한다.

## 6. 배포 제한
G01 절대 의미 기준, 모델/외부 자산 권리, 일반 Gazebo 종료, 최종 합성 원고 QA, 모든 절 자동 실행/GUI/native ROS 미검증. WSL2 L3는 지정된 네 경로에 한해 PASS. main merge 없음. 

## 7. 실제 인수 결과 (2026-11-26)
기존 사용자는 재실행하지 않는다. [보고서](reports/G09_WSL2_OWNER_ACCEPTANCE_REVIEW_20261126_KO.md) 및 [정제 증거](../evidence/g09_wsl2_owner_acceptance_20261126.json): 82/82 해시, source exact, --check all, 4/4, exit0. 신규 독자는 권리/자산 조건과 동일 PIN을 따르며 본 기록은 해당 환경의 제한적 인수이지 모든 PC에 대한 보증이 아니다. 공개 출고 HOLD.

공용 legacy Ch07 sparse preflight는 독립 PR #207/run45828900636으로 수정 및 main 병합 완료. Ch14 PR 검사 상태는 출고 결정서 참조. 기존 사용자 성공 PIN 재실행 불필요.
