# 13.6 M3 실제 MoveIt 계획·실행 인수

2026-11-03 KST. 단일 작업자. M3는 PASS이며 물리 픽킹 전체 인수와 구분한다.

## 기준과 실행

동결 `section_13_6_reuse_acceptance_v2.json`: 소스230개, 원본 외부94자산. manifest SHA256은 `3620227a258b8c8fcdef914a7af61bc6d7ea5724b7d186f49bd669415ac7491c`다. 실행마다 설치 Python·설정·생성 URDF/SRDF·C++ ELF와 외부 자산을 감사했다. 별도13.6 build를 사용했고 기존 R5와114파일 동결은 덮지 않았다.

실행 UUID `04149479-7145-4b6f-8d99-b313526e12a0`. `run_case.sh moveit` exit0, `verify_moveit.py` PASS. 단위/부품 회귀는 실제 installed MoveIt RobotModel FK 시험을 포함해162개 PASS(43.47초)였다.

| 실제 검증 | 측정/결과 |
|---|---|
| 작은 관절 계획→native action→실제 팔 | 위치3.8742mm, 방향8.9695mrad |
| 6D pose 계획→실제 팔 | 위치3.8349mm, 방향7.7384mrad |
| Cartesian 경로→실제 팔 | fraction1.0, 위치3.0088mm |
| 도달 불가 목표 | 계획 거절, 실행 없음 |
| 실제 상태 충돌 조회 | 원래True→TCP 주위 fixture 추가False(이름 있는 접촉)→제거True |
| 충돌 fixture의 경로 계획 | 계획 거절, 실행 없음 |
| 사용자 취소 | cancel ACK와 같은 goal의 실제 CANCELED terminal 확인 |
| 수명 | 살아 있는 engine 시계에서 planner 먼저 회수,12개 정상 자식 종료, RX/renderer/upstream join, 잔여/lock 없음 |

## 모델·실행 계약

통합 MuJoCo 기준 mount/축/한계/mass·inertia와 모든 물리 collision geom의 보수적 표현을 로컬 URDF/SRDF로 생성한다. 무작위20자세의 링크/TCP FK는1e-8 수준으로 MuJoCo와 대조했고 실제 MoveIt RobotModel FK도 비교했다. floating base와 실제 joint_states/TF는 engine이 소유한다. MoveIt에 fake joint publisher나 고정 trunk를 추가하지 않았다.

TRAC-IK2.0.2·OMPL RRTConnect·MoveIt2.12.4의 단일 장면을 Python 서비스 래퍼에서 사용한다. 원고의 개념 API를 그대로 가정하지 않는다. native FollowJointTrajectory가 실행 경계이며 원본 native PD가 유일한 actuator 적용자다. scaling0.08, 원본 관측300ms/과거TF100ms, 장면 hash·시작 관절·원본 capture 재검증, 전체 Cartesian fraction1, C2/한계/속도·가속도 증명과 실제 terminal을 적용한다.

TOTG의0.532510ms 끝 구간 때문에 v1 `4732687c`는 실제 세 이동과 충돌 거절 이후 취소 전에 거절됐다. 원본 경로점을 모두 보존하고 최소2ms가 되는 전체 배율을 먼저 계산한 뒤 같은 bounded 검증을 적용했다. 실제 실패 궤적을 회귀 fixture로 보존했고 RED→GREEN을 확인했다. v1 manifest는 수정하지 않았다.

기본 MoveGroup 종료·ExecuteTrajectory 취소 문제, 작은 호스트의 수명 완화책, 모델 bias PD profile, gateway hold 가정 수정과 이전 FAIL은 [설계 변경 기록](SECTION_13_6_REUSE_ENGINEERING_DECISIONS_KO.md) 및 [중간 기록](SECTION_13_6_REUSE_M3_PROGRESS_KO.md)에 남긴다. 과거 `660ec362` summary PASS의 gateway fault 누락은 계속 전체 PASS로 인정하지 않는다.

## 재현

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh moveit Ch13/evidence/section_13_6_reuse/새로운_UUID
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_moveit.py Ch13/evidence/section_13_6_reuse/새로운_UUID
```

게시 사례는 [실습 가이드](LAB_13_6_REUSE_GUIDE_KO.md)의 archive 복원 후 같은 verifier로 확인한다. 이 결과는 M4 물리 파지·하중 강건성·실기·새 WBC 성공을 뜻하지 않는다.
