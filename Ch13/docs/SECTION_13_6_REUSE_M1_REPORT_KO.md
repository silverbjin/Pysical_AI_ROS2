# 13.6 M1 live 인계 검증

2026-11-03 KST. 사용자 설계 승인 후 단일 작업자로 실행했다. **같은 engine에서 접근 후 작업 권한을 유지·회수하는 연결을 구현했다. 팔 궤적/MoveIt/파지는 아직 이번 결과에 포함되지 않는다.**

## 변경

`ch13_manipulation_reuse`에 ROS 독립 Lease와 engine-local extension을 추가했다. native ingress가 실제 DDS GID/최초 receipt와 원본 CDR을 전달한다. engine session UUID, Nav2 goal UUID의 실제 status SUCCEEDED, 실제 root 목표오차/정착·armed zero, navigation IDLE, 신선한 원본 관측을 함께 확인한다. 과거 summary/string READY는 명령 권한이 아니다.

`run_navigation_probe.main(argv=None,handoff=None)`의 opt-in callback에서 navigation 소유권과 engine 수명을 그대로 유지한다. callback이 없으면 기존 READY 짧은 발행→회수→shutdown이다. 새 launch flag 기본값은 false. extension 활성 때 joint1 시험 parameter는 거절하여 후속 trajectory와의 경쟁을 차단한다. 기존 PD/보행 cap/physics/가중치/외부 자산을 바꾸지 않았다.

13.6 별도 build `/home/jinho/ch13_reuse_13_6_build`에 네 패키지를 설치했다. 기존 R5/R2 경로는 새 build 도구가 거절한다. 시스템 apt/pip 설치는 하지 않았다. 원본94 해시 및 이번 source↔실제 install(기존32 산출물+새3모듈)을 대조했다.

## 검증

ROS 독립 lease13시험과 기존13.5 89시험: **102 PASS / 37.90초**. 새 시험은 원본 capture 반복의 수명 연장 금지, 과거 session, owner교체, 만료/TF오류/시계역행, 실제 action status와 정착 요구, 새 goal 회수 및 실행 중 base support를 검증했다. 실행기 자체의 spawn 진입점 문제로 초기 suite를 59 PASS 지점에서 중단한 기록을 남겼고, main guard 수정 후 전체 suite를 다시 완료했다. 이 중단을 전체 PASS로 세지 않았다.

실제 engine은 아래 네 경우를 순차 실행했다. 각 폴더의 install audit, engine observations, manipulation_status, navigation_summary, RGB-D/원본 관측 및 pre/post residual을 보존했다. `verify_handoff.py`로 독립 판독했다.

| 사례 | UUID | 실제 결과 |
|---|---|---|
| 정상 유지/명시 회수 | `5b9806ef-7074-48aa-a619-8ce5044a5321` | READY 2.039672wall초/1.12sim초, 새 capture들로 유지 후 REVOKED |
| heartbeat 손실 | `7a4b7b0c-c343-4a63-b0bf-01d254521e8d` | MISSION_EXPIRED latch, 자동복귀 없음 |
| 과거 engine session | `0cc28552-7814-44bd-b672-7063fe725082` | SESSION_MISMATCH, READY 미발행 |
| 실제 중복 lease publisher | `97b4e2f4-7152-4c08-839b-2e904ac93575` | DUPLICATE_OWNER:mission latch |

네 실행 모두 Nav2 비전 접근의 actual terminal을 받았고 같은 session의 live 상태에서 판정했다. 각 실행 child11개 clean exit, launch exit0, RX/원본 thread/renderer join, 잔여 없음 및 lock free를 확인했다. 정상 사례 engine PID2347/session `437762ad-fb22-4b2b-b8be-cd84e210616c`. 실제 force cap 비율≤1 유지. 성공/고장 실험마다 새 session/증거 경로를 사용했다.

## 범위와 다음 단계

정착 전·새 goal·관측 자체 만료는 순수 계약 시험으로 확인했다. 실제 engine의 새 Nav2 goal/관측손실 injection은 최종 matrix에 남아 있다. M1은 팔이 움직이지 않는 live 인계 단계다. M2의 실제 궤적·취소/hold와 그리퍼 검증, M3 MoveIt 모델·실행, M4 물리 파지, M5 최종 freeze/회귀/가이드는 계속 진행한다.

기존 v3 freeze/evidence는 변경하지 않았다. 공유 source가 확장됐으므로 이번 수정본을 기존114파일과 동일하다고 주장하지 않는다. 13.6 freeze는 최종 인수 전에 별도로 만든다.
