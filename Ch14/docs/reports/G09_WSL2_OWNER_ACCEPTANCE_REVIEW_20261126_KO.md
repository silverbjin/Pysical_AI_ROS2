# G09 WSL2 실제 사용자 인수 — 교육용 검수 보고서 (정제본)
2026-11-26 | OWNER_L3_SCOPED_PASS | CPU headless Docker | full release HOLD.

## 증거 검증
원본 evidence.tar.gz 3,155,152 bytes, SHA256 ff05c8c7c83808ecd24709d6c766c2abbff48ba0fd70f43d33243a40bd342568; 제출 sidecar와 일치. 정규 파일 manifest 82/82, 누락/목록 외 파일 0 (manifest 자신 제외). Python 독립 해시 검증. 실제 WSL2 커널, x86_64, Docker Engine 29.9.3; host doctor PASS. 호스트 OS-release 원문 없음, native ROS 설치 검수 아님. 고정 source 6c458e345236b124c9aa60f65788f35cfed74e62, requested=actual; bootstrap SHA256 0939ce653d896fb84a381e494600d77ce1cbbafd95e4aa86618cff33b7c2e30f 기존 기록과 일치. 다른 세 스크립트의 원격 bytes 독립 재해시 미수행. 원본 owner-result status SCOPED_PASS, level WSL2_OWNER_REVIEW_REQUIRED, check all, stage complete, raw_exit_code/exit_code0, GUI NOT_RUN, full_release HOLD. 원본을 수정하지 않고 리뷰 판정을 별도 기록. G07 원본 artifact 15090667475 (run45763347165)의 필수 payload 11개 검증 기록이 host/두 RL 경로에 있음. 원본 ZIP 자체는 이 tar에 없어 이번 리뷰에서 다시 해시하지 않음. 외부 scene evaluation-only. 원본 로그/로컬 경로/호스트 식별정보/모델 및 자산 바이너리는 공개 커밋에서 제외.

## Linux CI 대비 실제 WSL2
| 지표 | CI | WSL2 |
|---|---:|---:|
| build packages/time | 6/5.69s | 6/7.34s |
| perception GT/3D | 13/13 | 13/13 (10 normal + 3 resumed) |
| MuJoCo active/matched/feedback | 400/400/400 | 400/400/400 |
| Gazebo active/matched/feedback | 399/399/399 | 398/398/397 |
| rate both | 50Hz | 50Hz |
| owned exits | clean | 9/9 zero, 4 owned containers absent |
Build: NumPy1.26.4, Torch2.5.1+cpu, ORT1.20.1, pip check PASS. 초기 wheelhouse offline certifi miss → 정상 네트워크 fallback 성공; APT FIRST_PASS, Get:404는 항목 순번. Perception confidence .831025, bbox IoU .921887, RGB-D alignment .993447, odom point [2.253160,-.085889,.940952] m; pause guard and resume PASS, 4 exits0.

## 원시 데이터 재계산 및 차이 분석
| RL metric | MuJoCo | Gazebo |
|---|---:|---:|
| target scalar exact | 4800/4800 | 4776/4776 |
| max difference | 0 | 0 |
| positive direction pairs | 58 | 323 |
| min height m | .378468 | .391640 |
| max inference ms | .350460 | .494820 |
| expiry | PASS | PASS |
| pause/resume | PASS | NOT_RUN |
| clean exits | 2/2 | 3/3, server stop ACK |
관측48/target12 유한성, monotonic sim rate, 높이, 추론시간, command expiry, target 값 차이 및 저장 response 수 재계산. Gazebo headerless Float64 receipt window max 차이 5.57865ms는 source timestamp latency 아님. 저장 response 레코드 방향 재집계이며 전체 물리 witness 재실행 아님. Gazebo 마지막 명령 t9.100은 12관절 값 모두 일치. pre 60개, post 0개; post 최소 t9.119보다 마지막 JointState t9.113이 먼저 종료됨. 사후 관측 부족으로 한 쌍 제외, 해당 명령 실제 물리 응답은 미확인. 고정 검수 기준 active>=100, matched>=100, feedback>=50, 35~55Hz, 높이>.14m, 양의 물리 응답 존재 모두 충족. 기준 변경 또는 반복 실행 불필요. 두 엔진 SMOKE_ONLY, LOCOMOTION_QUALITY NOT_ACCEPTED 유지. MuJoCo pause recovery PASS.

## 판정 및 교육적 의미
CI와 owner 인수는 분리한다. 동일 SHA, 동일 계약의 실제 환경 증거로 인수하며 미세 표본 차이는 기준과 raw 측정창으로 설명한다. G09 네 경로의 L3 SCOPED_PASS 승인 기록. G00~G08 개별 L3 일괄 승격 금지. 원래 G01 absolute semantic FAIL, 외부 자산 rights, 일반 동시 Ctrl+C, legacy Ch07 preflight, full manuscript QA, native WSL2/GUI, GPU, 안정 보행 및 실제 HW 범위는 기존 원장과 출고 결정에 따름. 재실행/재학습 없음. 공개 Git에는 정제 증거만 보존. Main 병합 조건 미충족.

CI: [build](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45815645513), [physical](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45816276822). [정제 JSON](../../evidence/g09_wsl2_owner_acceptance_20261126.json).
