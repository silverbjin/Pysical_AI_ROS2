# 13.5 따라 하는 실습 가이드 개정 보고서

작성: 2026-11-03. 대상: `LAB_13_5_REUSE_GUIDE_KO.md`. 실행 소스와 v3 인수 기준 변경 없음.

## 변경

사용자가 제공한 원고의 아홉 절을 설명→구현 위치→실행 명령→기대 결과로 개정했다.

- Ubuntu/WSL bash·ROS2 Jazzy 준비, GitHub sparse clone, 실행114파일 확인, upstream 고정94자산 다운로드·hash 확인.
- 추론 venv와 ROS 시스템 Python 분리, 새 터미널 환경 파일, Ch13 세 패키지 빌드·설치 감사·검사 명령.
- 자유 이동/장애물 우회, 실제 YAML·스무더·게이트, 모델 FK/IK, RGB-D 접근과 액션 terminal, 모드 인계, 실패 세 사례, 전체 인수.
- 터미널 A의 실행 소유권과 B의 선택적 조회 구분, 결과 경로 재사용·잘못된 Python·만료·실패 보고서 미생성·과거 PASS 문서 오인에 대한 확인법.
- 별도 로컬 브랜치에서 목표0.65→0.80m 변경과 새 source snapshot을 만드는 부록. 이 변경은 출판 v3 성공 결과에 포함되지 않는다.

실제 Navfn/RPP·TwistStamped·ground-truth profile을 따른다. 원고의 미검증 문턱 등반, 낮은 장애물 일괄 무시, 고정0.4m/팔 길이 비율의 최적성, crawl 전환, AMCL/SLAM, 일반 객체 인식, MoveIt/파지는 성공 범위로 옮기지 않았다.

## 검증

[요약](../evidence/section_13_5_reuse/guide_revision_20261103/validation_summary.json), [준비 명령](../evidence/section_13_5_reuse/guide_revision_20261103/commands.log), [판독·검사](../evidence/section_13_5_reuse/guide_revision_20261103/results.log)를 남겼다.

- 실제 GitHub의 새 sparse clone, 당시 HEAD `5af76221db286fa148e8c883eedca0502e56b0c6`. 실행114파일 hash 일치.
- 같은 상위 폴더의 기존 upstream94자산은 읽기 전용 hash 확인. 기존 venv/build를 명시해32설치 산출물 감사 PASS.
- bash28블록 문법, Python heredoc13개·설명 코드1개 AST, 상대 링크 PASS. 부록 목표 치환은 메모리 사본의 문법만 확인.
- YAML/Guard 출력/FK·IK 명령 PASS. slew3개·safe handoff1개·approach geometry2개, 총6검사 PASS.
- 자유 이동·비전 판독 코드는 이번 결과로 실행. obstacle/blocked/cancel/raw_loss 판독은 기존 v3 해당 기록을 읽어 확인했으며 새 엔진 실행으로 세지 않는다.

## 실제 대표 실행

| 폴더 | 결과 | 실제 위치/방향 오차 | terminal→정착 | 정상 회수 |
|---|---|---|---|---|
| free | PASS | 0.044305m / 0.009666rad | 1.780wall초 | launch10개, 잔여 없음 |
| vision | FAIL: VISION_EXPIRED | 도착 판정 전 취소 | 미완료 | launch11개, 잔여 없음 |
| vision_retry | PASS | 0.036725m / 0.016198rad | 1.667wall초 | launch11개, 잔여 없음 |

첫 비전 실행은 관측 나이0.3474wall초로300ms 조건을 넘겨 fault/cancel했다. 실패 원본·별도 회수 검사·보고서를 보존했다. 코드·가중치·게이트 변경 없이 새 폴더에서 재실행해 READY와 최종 IK를 확인했다. READY 촬영 나이0.10177초, IK 잔차0.00428m다. 조회 동시 실행은 원인 후보지만 인과관계를 확정하지 않았다. 재실행 성공을 최초 실패 수정이나 강건성 검증으로 표시하지 않는다.

선택적 live 조회 호출은 해당 시점에 topic/node를 발견하지 못했다. 실행 중 조회의 성공으로 세지 않는다. 타입/이름/값은 소스와 설치 YAML로 대조했고, 가이드에는 종료 후 조회 메시지와 로그 시각 확인을 명시했다.

## 한계와 보존

관리자 apt/pip 설치, 새 venv,94자산 전체 네트워크 재다운로드, 신규 build, 전체6개 엔진 matrix, 부록0.80m 실제 이동은 재수행하지 않았다. 기존 환경을 사용한 명령 검증과 대표 실행을 구분하며 새 PC 설치 전체를 검증했다고 주장하지 않는다.

114실행 파일·94외부 자산·stop gate SHA 불변. 문서·본 증거·manifest만 게시하고 외부 모델/가중치, 다른 장, 기존 실패와 사용자 문서는 수정하지 않는다. 계획의 reviewer 요구는 사용자의 단일 작업자 지시에 따라 자체 전체 대조로 수행했다. 문서 개정에 구현을 복제하는 새 단위 테스트는 추가하지 않았다.
