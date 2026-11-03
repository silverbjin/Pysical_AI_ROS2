# 13.6 M2 실제 팔·그리퍼 실행 경계

2026-11-03 KST. 단일 작업자. **6축 작은 실제 궤적·그리퍼 개폐·취소·입력 손실의 안전 hold를 확인했다. MoveIt 계획과 물리 파지는 아직 이 결과가 아니다.**

## 구현

표준 FollowJointTrajectory/GripperCommand action을 engine-local extension에 연결했다. 궤적은 joint1~6 전체 집합, 실제 시작 상태, 유한값·단조시간·한계·속도0.05rad/s·가속도0.1rad/s²·종료속도/가속도0을 검증한다. quintic 내부 극값도 검사한다. 새 궤적/목표와 joint1 시험 parameter의 병렬 쓰기는 없다. 취소/lease 소실 시 현재 궤적의 위치·속도·가속도를 잇는 유계 감속 후 실제 hold를 확인하고 terminal을 반환한다. torque0/무조건 수납은 하지 않는다.

실제 q/qd/actuator_force만 feedback/완료 판정에 사용한다. 그리퍼는 joint7(m)만 명령하고 joint8=-joint7의 실제 관측을 확인한다. 개별 요청 effort도 원본0.5N 상한 이내로 제한한다. action ACK와 실측 종료/정착을 구분한다. 별도 build/R5 보존/원본94 hash/설치 대조를 유지했다.

## v1의 제한과 명시적 v2 보정

첫 v1 정상 시험(`6f6f2ec6-98ca-4c8e-a13e-374c8b55d639`)은 action 허용오차 안에서 종료했지만 독립 판독 결과 joint2/3의 실제 변위가 각각0.000106/0.000064rad에 불과했다. **원본 navigation_summary의 PASS는 당시 약한 판정 결과이며 실제6축 성공으로 인정하지 않는다.** 새 `verify_arm.py`는 이 기록을 거절한다. v1 취소(`e9ebfd07-5f79-4126-aa3a-bbffbde194e0`)와 손실(`1fe9dba5-32f5-4497-aa9d-877d803b949d`)도 그대로 보존한다.

로컬 forward dynamics 조사에서 joint2/3 bias는 약+2.941/-6.269Nm, Kp50의 미보상 오차는 약+0.0588/-0.1254rad였다. 20mrad 목표만으로 중력/마찰을 이기지 못했다. gain/힘 cap/질량/정책을 탐색하지 않고 **13.6 모델 bias feedforward profile v2**를 명시적으로 추가했다.

v2는 기존 native PD 적용자 하나에 내부 servo reference=`planned reference + ramp*qfrc_bias/Kp`를 준다. 첫 arm action 뒤0.5sim초 ramp로 활성화하며 이후 hold/취소에도 유지한다. 이는 원본 그대로의 제어가 아니라 **native PD + 모델 bias 보정**이다. 원래 Kp50/Kd4와32/8Nm cap·2ms physics·50Hz 다리 정책은 그대로다. 현재 simulator 모델에 의존하며 실제 하드웨어 중력 보정의 실증이 아니다. 외부 가중치/모델 파일은 변경하지 않았다. planned reference와 내부 servo reference를 별도 기록하며 정착/추종은 planned reference에 대해 판단한다. [v1 수치](../dependencies/section_13_6_control_v1.json), [v2 변경 계약](../dependencies/section_13_6_control_v2.json).

v1 정상 종료 후 publisher teardown이 이미 회수한 lease를 MANIPULATION_GRAPH_LOST로 덮는 문제도 발견했다. REVOKED 이후 graph 검사를 중단하도록 실패 재현→수정→통과를 확인했다. 물리 지지/actual shutdown 검사는 계속 유지한다.

## 실제 v2 결과

| 사례 | UUID | 독립 판정 |
|---|---|---|
| 20mrad 왕복6축+그리퍼 개폐 | `39ce0059-583a-4910-a177-bd74fbe8e9d1` | PASS, 실제6축 변위11.1/11.6/11.3/20.0/30.2/20.1mrad, 최대오차12.24mrad |
| 이동 중 action 취소 | `c672b3ae-bae5-46a1-a67d-ef2f2e12140b` | PASS, 실제 감속·hold 후 CANCELED |
| 이동 중 heartbeat 손실 | `ae100b1b-7ba3-48b4-8cfe-05a89bff7bd6` | PASS, MISSION_EXPIRED latch·감속·hold 후 ABORTED |

gripper open0.03m 실측 joint7=0.0298145m/joint8=-0.0298117m, close0 실측0.0001270m/-0.0001293m. 양쪽0.002m 오차·연동 기준 안이다. 물체 접촉 없이 개폐만 시험했다.

v2 손실의 앞선 실행(`f89526c0-edbc-48d7-a8df-3bebff5c2303`)은 팔 action 이전 Nav2 접근 중 VISION_EXPIRED(관측 나이약0.338초)로 취소됐다. 이 실패를 보존하고 코드/300ms 기준 변경 없이 새 경로에서 손실 주입을 다시 시험했다. 기존13.5에서 알려진 지연 문제를 해결됐다고 주장하지 않는다.

세 v2 인수 실행 모두 정상 engine 종료, RX/원본 thread/renderer join, child11개 clean exit, 잔여 없음/lock free를 확인했다. 원본 힘 cap 이내이며 실제 종료 후 joint속도≤0.05rad/s·platform 정착을 확인했다. 입력 복귀 자동 재활성화는 없다.

## 부품 시험과 한계

M2 관련34시험 PASS: lease13, trajectory15, action boundary3, 종료회수1, bias 수학계약2. 각 신규 기능은 missing module/실패 재현을 먼저 확인했다. 초기 M1 전체102 PASS와 M2 변경 뒤 최종13.5 실제 회귀는 구분한다. 마지막 회귀는 M5에서 수행한다.

실제 중복 lease 발행자는 M1에서 거절했다. 중복 action server는 경계에서 검사하고, 표준 action 자체를 인증된 DDS client identity로 주장하지 않는다. M3 모델/FK/계획 연결 및 M4 물리 picking은 계속 진행한다. 전체 완료·최종 freeze·강건성 성공을 이 M2 결과로 선언하지 않는다.
