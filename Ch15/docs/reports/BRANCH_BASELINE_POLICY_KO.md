# Ch15 기준선 및 병합 정책

G07 종결 d05c67b1e88e06e5323722403e459afa6eaa2027에서 G08 착수. PR #208 single linear branch, main 1931cac92585fc155357880b584c72c76d67257c. [기준선 manifest](../../evidence/gate_baselines.json)는 종결 SHA와 실제 CI 실행 SHA를 구분한다.

- G01 `ch15-g01-scoped-v1` → `92f50d6c1dba7814c9952bce74da4e94bb510583` (T01/T02 L0 scoped; runtime not accepted)
- G02 `ch15-g02-scoped-v1` → `1501416d5e399ee308c4ba38b6e4cb78c8e6d185` (T03–05 L0/L1 scoped)
- G03 `ch15-g03-mock-v1` → `30fa2fa012404ba83d110e308e201eeda5bf5d6c` (T06–09 mock only)
- G04 `ch15-g04-basic-v1` → `0f67d0222a9737ddc07c447a35a9be50ed2e761d` (T10 V6 alternative basic + T11; original native FAIL; physical F01 BLOCKED)
- G05 `ch15-g05-evidence-v1` → `d4405ebb7d65aecb9d54e3d124da6bb31d699509` (T12–14 mock record/replay)
- G06 `ch15-g06-visualization-v1` → `00e6e2d33b616dcd9e93891e9431e19ed824cfb4` (T15 DDS, GUI NOT_RUN)
- G07 `ch15-g07-joint-v1` → `d05c67b1e88e06e5323722403e459afa6eaa2027` (T16/T17 isolated MuJoCo and synthetic LPF)

태그 생성 시도는 실제 CI HTTP 403으로 실패했고 원격 태그 0/7을 조회했다. 권한 우회 및 재시도 금지; write workflow 제거. 저장소 소유자가 인증된 clone에서 `bash Ch15/scripts/pin_g01_g07_tags.sh`를 실행한다. 기존 태그와 SHA 불일치 시 전체 preflight 실패; atomic push, force/update/delete 금지. 원격 7/7 확인 전까지 태그 BLOCKED로 판정. 태그는 편의용이며 실행기는 full commit SHA로 고정한다(태그 보호 ruleset은 별도 관리자 설정, 현재 미확인). G08 변경 경로 및 영향 범위 검수, 이전 원본 성공/실패 증거 유지. G09 source closure 및 owner one-shot. WSL2 실제 증거 검토와 사용자 승인 후만 non-squash merge, 최종 릴리스 태그. 공개 소스와 외부 자산 재배포 권리 별개. Artifact 장기 보존은 원본 권리 범위 내 해시 및 receipt 보존 우선.
