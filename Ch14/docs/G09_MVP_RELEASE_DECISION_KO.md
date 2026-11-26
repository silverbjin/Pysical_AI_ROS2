# Ch14 MVP 출고 결정 — G09 WSL2 인수 이후
2026-11-26 | owner limited technical PASS | public release HOLD | Draft PR #206 유지.

## 기술 범위 (확정)
CPU simulation-only 실습: G01 PT→ONNX 및 원본 대비 parity(절대 의미 미달 보존), G02 ORT/OV CPU 비교, G03 실제 RGB-D, G04 atomic/hot swap 및 ordered shutdown, G05 60s profiling, G06 CPU Docker replay, G07 smoke policy export/shadow, G08 두 엔진 ROS 실제 제어, G09 네 경로 WSL2 headless Docker. 각 Gate 원장 범위만 인정. A 인지와 B 제어는 독립 실습, 통합 자율조작 제품 아님. 기존 PIN 6c458e345236b124c9aa60f65788f35cfed74e62 유지. 새 성공 SHA로 가장하지 않는다.

## 미충족 조건 및 처리 순서
| 항목 | 현재 판정 | 다음 조치 / 완료 조건 |
|---|---|---|
| G01 필수 표적 | n14/16, s15/16 FAIL | 사용자/출판사 명세 변경 승인(원본 대비 parity 교육 목표) 또는 원래 조건 충족 증거. 실패 기록 보존, threshold/fixture 변경 금지 |
| 외부 권리 및 G00 | HOLD | AGPL/COCO/person_standing/vendor/의존성/모델 권리 담당자 검토 및 승인, 필요한 notice/source 제공 방식 확정. 바이너리 비공개 유지. 다운로드 방식 자체가 권리 승인은 아님 |
| 일반 Gazebo 종료 | HOLD | ordered runner 한정 출판 승인 또는 동시 Ctrl+C 원인 및 별도 검증. 기존 ordered 성공 반복 금지 |
| legacy PR 검사 | FAIL | Book Lab Acceptance 45817052187 job139899387907: ModuleNotFoundError vision_basics, Ch07 sparse 범위 문제. 기존 챕터/공용 CI 수정은 별도 승인·독립 PR, 실제 document-preflight GREEN 확인; 우회/skip 금지 |
| 원고 전체 QA | HOLD | S1/S2/S3 전문 확보, 코드 14-1~19와 가이드·주장 대조; 14.9 체크리스트 개정 승인 |
| GUI/native ROS/GPU/모든 절 자동실행 | NOT_RUN/optional | CPU headless Docker 제한 배포 문구 명시; 제외 승인 또는 필요한 경로만 신규 검수. TensorRT 14-5 미구현 |
| G07 장기 보존 | private retention required | exact original ZIP + sidecar 승인된 보존소에 보관; 만료 시 자동 재학습 금지 |
| G09 owner L3 | SCOPED_PASS | 완료, 재실행 금지(관련 변경/새 결함만 예외) |

## 최종 배포 권고 (승인 전 제안)
출판용 CPU 제한 MVP로 기술 범위를 명시하고 GPU/보드/안정 보행/일반 종료 등 미검수 항목은 완료 기능에서 제외. G01 절대 의미 실패는 교육 사례로 공개하되 전체 PASS로 바꾸지 않는다. 권리/필수 PR 검사/원고 검토는 생략할 수 없는 별도 게이트. 공개 배포 승인 및 조건 충족 후 Draft 해제, exact expected head로 main merge, Ch01~13 변경 없음 확인. 현재 main 유지. 이번 문서 작업은 기술 인수 기록 권한에 한정하며 외부 권리 또는 전체 명세 변경을 사용자 대신 승인하지 않는다.
