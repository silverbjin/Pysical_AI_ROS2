# G09 다음 작업 프리뷰 — §14.9 최종 통합·배포 검수 (NOT_STARTED)
## 1. 목표와 선행 조건
G08 T19 CPU SMOKE_ONLY SCOPED_PASS를 보존하고 G00~G08의 evidence/원고/실행 경로를 하나의 도서 배포 기준으로 정리한다. G09 원래 기획 명세 CH14_DEVELOPMENT_SPEC_KO.md 원문 및 S1/S3 전량 대조가 미확보이므로 아래 순서는 인계·원장 기반 제안이며 원 명세 대조를 먼저 수행한다. 본 문서 자체는 착수 또는 인수 승인 아님.

## 2. 제안 단계
| 단계 | 작업 | 완료 조건 |
|---|---|---|
| G09-A | 원고 14-1~19 및 §14.9 추적, 파일/가이드/패키지 audit | 모든 코드 번호의 실제 entry point, 예제/실측/미실행 표시; 누락만 수정 |
| G09-B | 의존성/모델/fixture provenance 및 재사용 검수 | exact SHA, license/재배포 결정; G07 original archive 장기 보존 계획; no auto-train |
| G09-C | 독립 CPU 실습 배포 경로 및 fail-fast preflight | 기존 evidence에 영향을 주는 변경만 selected regression; 설치/실행/종료 경계 구분 |
| G09-D | 독립 package 및 문서 검수 | 신규 사용자 관점 path/commands, 실패 안내, evidence archive, GPU optional 명시; 실제 환경에서 미실행 항목 표시 |
| G09-E | WSL2 owner L3 인수 준비 | immutable SHA runner 및 원본 evidence 수집; owner 승인·실행 결과 없으면 NOT_RUN |
| G09-F | final acceptance ledger / release review | blockers 명시, PR checks 및 main 영향 확인; 사용자 별도 승인 및 모든 release 조건 충족 시에만 병합 |

## 3. 필수 release blockers
G00 권리/fixture/profile, G01 absolute semantic n14/16 s15/16 FAIL (교육용 변환 scoped만), G04 일반 동시 Ctrl+C/native hang root cause, legacy Book Lab Acceptance sparse checkout failure (기존 workflow 무단 변경 금지), WSL2 L3, GPU optional NOT_RUN, G08 smoke-only walking NOT_ACCEPTED. G07 RL lock reinstall은 G08에서 실제 성공하여 해당 blocker 해소. Gazebo G08 ordered owned shutdown scoped 성공은 일반 종료 문제의 해결로 승격하지 않음. 필요하면 미검수 Gazebo negative guard를 별도 범위 결정(기존 정상 반복 금지). 
## 4. 실행 정책
단일 feat/ch14-ai-deployment / Draft PR #206, main baseline 9431fb535ce7a51416c19c4395fb2ba3fabdad40. OBSERVE→ISOLATE→HYPOTHESIZE→REPRODUCE→FIX→VERIFY→REVIEW→COMMIT. 원본 실패 보존, 동일 fingerprint 최대 두 수정, evidence 없으면 HOLD. G00~G08 blanket re-run, 새 학습/ONNX export, 실제 HW, 타 장 변경 금지. G09 착수는 사용자 명시 승인 이후.
