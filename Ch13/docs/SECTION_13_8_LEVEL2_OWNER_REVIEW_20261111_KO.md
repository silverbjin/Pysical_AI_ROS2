# 13.8 Level 2 Owner 검토 자료

2026-11-11 KST. **정상 완주 인수는 보류다. Level 2 완료·성공을 선언하지 않는다.** 사용자가 요청한 도서 제공 수준을 고려해, 새 제어기·학습·WBC·실기 드라이버·executor 개편을 추가하지 않고 기존 구성의 작은 연결과 설정까지만 보완했다. 정상 완주 요구는 아직 충족하지 못했다.

## 현재 확인한 범위

| 항목 | 증거와 판정 |
|---|---|
| 개발 절차 | 변경마다 RED→GREEN→REFACTOR→자체 REVIEW→선택 COMMIT→공개 CI 확인 수행. 독립 검토자로 포장하지 않음 |
| 전체 부품 | 최신 native snapshot 478 PASS/79.76초. 실제 임무 성공과 구분 |
| 공개 CI | 소스 commit93f675b9, run42971985231, job130362337728, runner1000005543, 모든 step success. 공개 CI는 portable 계약9건이며 ROS/물리478건과 다름 |
| 원본 소스 | v44 source395/assets94, manifest SHA2448a88ee2392b33af2198519722c8723ca252f7f84de86bffea05f71246bdb9, tested/runtime 전수 일치 |
| 관측 이동 | v41 이후 실제 survey 성공·정착·새 관측 확인. 기존120wall 단독 예산은120sim/240wall의 명시적 작업 예산으로 수정함 |
| 경사/대상 확인 | v41 overlap1 사례에서 실제 ramp 접촉251.49N 및 final approach/find 확인 |
| 준비 팔/그리퍼 | v42에서 실제 arm SUCCEEDED 및 양 gripper 정상 terminal 확인. 이 사례의 이후 파지 실행은 미완료 |
| 실제 파지·연속 운반·놓기 | 이번 Level2 수정 사례에서 전체 PASS 미확인. 서로 다른 소스에서 통과한 부분을 하나의 연속 성공처럼 합치지 않음 |
| Owner 인수 | 명시적 인수 결정 미수신. 정상 완주 인수 gate는 FAIL/보류 |

## 최신 실제 결과

**기본 경로 설정 v44, UUID b949c443-0529-415c-98cb-125d0eafb3ca**: survey 뒤 최종 접근의 위치·방향 동시 조건을 만족하지 못해 NavigateToPose240wall deadline에서 종료했다. trial88.970sim/394.671wall초 FAIL. 실제 read-only GetParameters는 goal_checker.stateful=false/FollowPath.stateful=false, 최종XY.015m/관측XY.06m를 확인했다. 저장 표본에서 XY 최소1.720mm일 때 yaw오차1.121rad였고, XY/yaw 동시 통과 표본은0개다. 이는 연속 시각 전체의 부재 증명이 아니라 저장 표본의 대조다. 원래 허용 오차를 늘리지 않았다. engine/12child 정상 종료·잔여[]·lockfree다.

**기존 방향 고려 실험 설정의 단일 대조 v44, UUID3593fe57-b619-4ea7-a7bf-05374efb2651**: 새 소스/제어기를 만들지 않고 기존 CH13_EXPERIMENTAL_SE2=1을 선택했으나 survey 중 Nav2 Failed to make progress/ABORT로 실패했다. 기본값으로 채택하지 않았다. engine/12child 정상 종료·잔여[]·lockfree다. 두 실제 사례는 사전 고정10회 평가가 아니며 기존 v28의0/10을 대체하지 않는다.

원본 위치는 `Ch13/evidence/section_13_8_system/<UUID>`이며 각 raw.tar.gz/raw_manifest.json·source_v44 archive/hash·판정·실행 설정을 보존했다. 중복 원본 정리는 별도 원장으로만 기록한다. 복원은 `reuse_13_6/restore_evidence.py`의 기존 hash 검증 경계를 사용하고 새 빈 폴더에서 수행한다.

## 도서용 범위와 남은 결정

이번 보완은 기존 waypoint·작업 시간 예산·결과 대기·지원10/15Hz 인자·기존 goal checker 설정에 한정했다. 300ms 관측/heartbeat·TF100ms·접촉 guard·원본 정책/PD·명령 상한·실제 terminal/회수·3cm/120sim초/높이20mm 평가 기준은 완화하지 않았다. 호스티드 실행·Scan RX·callback 지터·lifecycle 종료를 혼동해 성공 원인이나 완화 근거로 삼지 않았다. 이 저장소의 ground-truth localization profile에 없는 Supervisor/localization manager 장애를 발생한 것으로 기록하지 않았다.

남은 기술 과제는 좁은 최종 접근에서 **기존 로봇 정책의 회전 중 이동과 Nav2 위치·방향 동시 도달의 연결**이다. 아직 모든 가능한 작은 설정을 소진했다고 주장하지 않는다. 다만 정상 완주를 보장하려고 새 제어기나 반복적인 임계값 튜닝을 도서 기본 범위에 자동 추가하지 않는다.

Owner가 확정할 경계는 다음과 같다. 원래 정상 완주 gate를 유지하면 Level2는 계속 개발 중이며, 다음에는 저장 경로·정착 오차만 좁혀 추가 분석한다. 도서용 최소 제공 범위를 관측 이동·실제 센서·실패 원인 판독 실습으로 확정하려면 **범위 변경에 대한 명시적 Owner 결정**이 필요하다. 후자를 선택해도 파지·운반·놓기의 정상 성공으로 표시하지 않는다. 본 문서는 실패 상태와 선택지를 검토하기 위한 자료이며 인수 승인 기록이 아니다.

공개 CI: https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/42971985231

상세 단계·반복 장애: SECTION_13_8_LEVEL2_GATE_LEDGER_20261111_KO.md.

추가 보존 정리: 닫힌11사례의 큰 비추적 중복86파일764,073,110bytes는 전체archive SHA와 각 멤버/로컬 SHA를 확인한 후 삭제했다. 원장 `retention_level2_duplicates_20261111.json`이 삭제 경로와 복원 멤버를 기록한다. 원래 manifest의 `raw_originals`는 생성 당시 상태이며 현재는 압축본에서 복원해야 한다.

## Owner 결정 수신 — 정상 기준 유지

Owner는 정상 완주 기준 유지·인수 보류를 명시했다. 앞의 결정 미수신 기록은 작성 당시 상태다. 실패 판독 중심 실습으로 범위를 축소하지 않고, 기존 구성 안에서 저장 경로와 실제 오차를 분석한 뒤 필요한 최소 변경만 진행한다. 인수를 대신 승인하지 않는다.

## 재개 후 갱신 — v48 실제 검증 전

Owner가 선택한 정상 완주 기준과 인수 보류를 유지한다. v45에서 실제 survey→최종 이동(14.847mm)→find를 통과했으나 팔 준비 중 원본 관측 만료로 종료했다. v46은 시작 명령 지연과 최종 접근 관측 만료를 따로 보존했고, v47은 초기 인식 모듈 준비 지연을 보완했으나 실제 최종 접근에서 생산→render→검증 지연 누적으로 실패했다. 부품 개선을 연속 임무 성공으로 합치지 않는다.

최신 전체 부품은 v48 485PASS/82.10초다. v47 코드 공개 CI run43016918196의 실제 runner/모든 step 성공을 확인했다. v48 공개CI와 실제 사례는 다음 단계이며, 아직 이 문서에서 성공으로 선언하지 않는다. 도서 제공을 위한 남은 핵심은 같은 실행에서 Level2 파지·운반·놓기·안전 종료를 통과한 뒤 원래 기준으로 정식 평가/가이드/Owner 검토를 마치는 것이다. L3 확장이나 새 제어기는 현재 최소 보완에 추가하지 않는다.
