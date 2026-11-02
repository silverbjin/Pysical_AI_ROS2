# R2 단계 3 — 설치 실행과 R2 기술 검증 완료

작성일: 2026-11-02 KST. 보존 증거의 PASS, 실행 소스 불변, 동일 boot 회수, 명령 램프를 확인한 뒤 자동 생성한 보고서다.

**R2 기술 작업 완료.** 단계별 로컬 commit을 보존한다. GitHub 게시와 원격 SHA 대조는 자동 승인 검토의 목적지 확인 요청 때문에 대기 중이다. R3/Nav2는 미착수다.

## 최종 결과

전체 작은 검사 **45/45 PASS**, 15.966초. [전체 로그](../evidence/section_13_5_reuse/r2_stage3_20261102/final_tests.log). 원본94파일hash 및 설치 Python/data/launch/ELF11항목을 대조했다. C++ install RPATH 차이는 기록하고 text/rodata를 검증했다.

실제 UUID `b5c33be2-25f1-4c2b-8f74-2ad1706840ec`. 격리 설치의 ros2 launch를 사용했다. ROS CLI는 시스템 Python, 추론/노드는 기존 venv이며 시스템 설치나 업그레이드를 하지 않았다.

| 실제 검사 | 관측 |
|---|---:|
| 첫 전진 | 0.413816 m |
| 회전 | 0.376051 rad |
| 전진 zero→정착 | 2.587992 wall초 |
| 회전 zero→정착 | 1.991050 wall초 |
| raw 손실→zero 결정 | 0.311488 wall초 (사전0.35 이내) |
| joint1 목표0.02의 실제 관측 | 0.010632 rad, 이후0목표 원복 |
| 실제 실행 | 14.002 sim초 / 33.264 wall초 |
| physics step / ROS 상태 | 7001 / 700 |
| 실제 힘 / 원래 cap 최대비 | 1.000 |

최종 독립500Hz 정지 창은 1.340286 wall초 / 0.500 sim초, 251표본이다. 평면속도 RMS 0.026337 m/s, yaw속도 RMS 0.040808 rad/s, 평면변위 0.009965 m, yaw변위 0.008135 rad로 edu_stop_v2를 통과했다. 수치는 바꾸지 않았다.

raw손실은 **gateway FAULT latch**를 남기며 입력 복귀에도 재개되지 않았다. 정상 zero를 계속 받는 platform은 이번 실행에서 **ARMED**였다. platform도 FAULT였다고 기록하지 않는다. platform 자체 safe입력 손실·중복·교체·clockpause의 latch는 별도 실제 DDS 부품4검사에서 확인했다. scripted clock 경계 검사이며 각 고장을 MuJoCo에서 모두 재현한 주장은 아니다.

RX/upstream thread join, launch 자식3개 clean exit, 부모 exit0/wait, 잔여 PID 없음, flock 해제를 확인했다. 실행 전후 동일 boot ID는 `fc02d252-a65e-46dd-96df-19678862a266`다. 상태 결과·실측 정지·프로세스 회수는 별도로 판별했다. 명령 slew는 vx 0.300000, wz 0.500000 /sim초이며 몸체 가속도 상한 주장은 아니다.

[실행 요약](../evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/probe_summary.json), [엔진](../evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/engine.json), [독립 정착](../evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/edu_stop_verification.json), [설치 감사](../evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/install_audit.json), [잔여 검사](../evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/residual_processes.json), [검증 요약](../evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/completion_verification.json).

## 발견과 수정

- service 공개 직후 SIGTERM에 context가 종료되는 경계를 결정적 RED로 재현했다. node생성까지 종료처리 범위에 넣었다. 살아 있는context의RCLError는 숨기지 않는다. 기준본 간헐exit1의 유일 원인으로 단정하지 않았으며 회귀와 최종 clean exit를 확인했다.
- platform exit1 이후 gateway/ingress가 남는 launch 수명을 실제 프로세스로 RED 확인했다. platform exit에 launch shutdown을 연결했다. CLI의 lark 누락은 시스템 ROS Python 사용으로 해결했고 추론환경/시스템 패키지는 변경하지 않았다.
- 첫 물리 실행 `15991e3a-81ab-421f-982d-237ccb9b6922`는 전진·회전·정착 뒤 팔 원복에서 입력 만료 FAIL이었다. 엔진은 계속 진행했으며 fault 인근 최대 상태간격은0.0781wall초였다. 시험 도구의 blocking service discovery가 자체 명령timer를 막는 경계를 실제 지연생성 DDS service로 RED 재현했다. spin을 계속하는 대기와client재사용으로 수정했다. 안전 만료값/정책/물리는 변경하지 않았다. 실패·오류종료 원본을 보존하고 새UUID에서 재실행했다.
- 정상 명령의 원본stamp·최초receipt·실제GID를 보존한다. 생성된 안전zero는status에서 원본명령과 구분한다.

## 완료 범위와 한계

R2의 단위/축/joint order, 실제상태·TF·시각, 소유권·만료/미래·clock pause/rollback·명시재무장, 설치일치, 실제기립유지/이동/회전/정착/제한된 팔 독립성, 정상종료 연결을 완료했다. 실행runtime의hash는snapshot과 동일하다. 이후에는 플랫폼 부품 검사파일만 추가했다. 새두패키지 빌드로 이전장 빌드를 요구하지 않는다.

원본home 초기조건과 제한된팔hold를 쓴다. down→stand 과도, 전체수납/보행envelope, 정확한팔추종·IK·MoveIt, 센서·카메라·Nav2·지도·비전접근, 모델/가중치별 재배포권리 및 새PC재현/U7은 이 결과로 완료 처리하지 않는다. R0 라이선스 출처 open 항목을 유지한다. R3–R5는 미착수다.

단일작업자로 전체변경을 자체검토했다. 미해결 R2 기술 항목은 없다. 기존사용자파일/Task8실패를 보존했고 main병합·PR·강제push는 하지 않았다. 전체R0–R5계획이 끝나지 않아worktree/ledger를 유지한다.

## 단계별 기록과 게시

[단계0](SECTION_13_5_REUSE_R2_STAGE_0_KO.md) / [단계1](SECTION_13_5_REUSE_R2_STAGE_1_KO.md) / [단계2](SECTION_13_5_REUSE_R2_STAGE_2_KO.md).

브랜치 `feat/ch13-section-13-5-reuse-r2-20261102`, 목적지 `https://github.com/silverbjin/Pysical_AI_ROS2.git`. 자동 승인 검토가 구체적 목적지와 업로드범위 확인 부족으로 push를 거절했다. 사용자에게 소스·보고서·증거(로컬 경로 포함, 모델/가중치 제외)의 게시 승인을 요청했다. 답변 전 재시도하지 않는다. 승인 후 각 단계commit을 순서대로 non-force push하고 실제 remoteSHA를 대조한다.
