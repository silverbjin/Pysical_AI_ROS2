# 13.7 BT 실습 개발 결과

2026-11-04 KST. 단일 작업자. 실제 정상·이동 중단·파지 후 취소·BT 비활성 기본 경로의 선택 인수를 마쳤다. 최종 게시 자료와 부품 검증 결과는 아래에 구분한다.

## 구현 범위

새 `ch13_mission_orchestration` 패키지는 실제 동일 엔진의 Nav2→새 RGB-D 관측→기존 MoveIt 파지→회수를10Hz Behavior Tree로 지휘한다. 각 잎은 별도 시작 요청과 완료 snapshot을 사용한다. 기존 run_pick 전체를 하나의 subprocess 잎으로 감싼 것이 아니다. 원본 보행/PD·MoveIt·물리 대상·수명·힘 한도를 재사용한다.

Blackboard에는 session과 원본 관측을 보관하고 최종 보완본에는 소유 Nav goal ID도 연계한다. memory=False 우선순위 root와 memory=True mission sequence, 비동기 수락/결과·취소 추적, abort/정상 terminal latch, native ROS snapshot과 tick JSONL을 제공한다. worker는 기존 robot node의 유일한 spin 소유자이며 BT node는 별도 context/executor다.

운반 귀환·기립·충전은 명시적인 mock 프로필이다. 실제 배터리 센서·YOLO·일반6D pose·물체 운반·실기·새 WBC/학습을 검증한 것이 아니다. 원고의 개념 코드와 실제 연결 차이는 [가이드](LAB_13_7_BT_GUIDE_KO.md)와 [공식 패턴 조사](SECTION_13_7_RESEARCH_KO.md)에 정리했다.

## 실제 결과와 정확한 소스 범위

| 사례 | 소스 동결 / UUID | 결과 |
|---|---|---|
| 정상 BT fetch | v3 / 80fcd4d7-f475-412b-86dc-cf98c746ef9e | 정식 mission PASS,18 checks true. 최소100.0367mm 상승·2.18sim초 hold·양 finger 접촉100%·TCP 상대 slip0.0273mm. 실제 원본 RGB-D 중심 재계산 PASS. 자식12개 정상 종료·잔여 없음. |
| 이동 중 저전력 BT 중단 | v3 / ca2256a9-1800-4dfa-b174-49fc8362c827 | 정식 mission PASS,20 checks true. 취소 ACK→실제 CANCELED→실측 정착·회수. Pick 미시작. 배터리는 교육용 주입값. |
| 파지 후 BT 취소 | v5 / e546e92d-2653-478d-9bbf-fe22855e886c | 정식 mission PASS,20 checks true. 실제 LIFT 실행1sim초 뒤 취소 ACK·CANCELED, 이후2.18sim초 유지·낙하0mm·양 finger 접촉100%·상대 slip0.0334mm. 자식12개 정상 회수. 성공적인9cm lift 판정과 구분한다. |
| BT 비활성 기존 navigation | v5 / 9ccb809e-ff0c-4363-b60a-1e8b2ac0ed60 | 기존 정식 navigation PASS,23 checks true. opt-in hook이 없는 기본 경로·실제 도달·정착·자식10개 정상 회수·잔여 없음. |

정상 v3 engine 구간은368.79wall초/161.90sim초, BT runner 전체는386.18wall초였다. 저전력 중단 engine9.54wall초/4.42sim초, BT runner25.398wall초였다. 파지 취소 engine257.34wall초/118.73sim초, BT runner274.93wall초였다. 기존 navigation 회귀 engine15.17wall초/11.13sim초였다. 다운로드·설치 감사·build·사후 판독 시간은 runner 시간 밖이다. 각 선택 사례1회 측정이며 반복 강건성 자료가 아니다.

정상 session은 fdc03d89-64fc-41db-b123-9b85a8ac919a, 요청 순서는 navigate/find/pick/finish다. 관측과 파지 시작은 같은 살아 있는 engine에서 이어졌고 모든 소유 goal의 terminal은 SUCCEEDED, 남은 goal0이었다. 미션 후 REVOKED와 planner 선회수→engine 정상 종료·thread join을 확인했다.

중단 사례의 정착 수치는 평면 RMS속도0.006202m/s, yaw RMS0.006010rad/s, 평면 변위3.043mm다. 원래 edu_stop_v2 수치와 native joint/force 한도를 유지했다. summary는 실제 시나리오를 case=cancel, 원래 접근 프로필을 navigation_profile=vision으로 함께 기록한다. 기존 계산기의 정상 vision 도착/READY 조건을 중단에 적용하지 않으며 원본 증거를 사후 수정하지 않는다.

v3 freeze는 소스281·외부94자산, SHA256 c374d501d7412fe68437786c86322602af828069fd916eabea167767d9299f35다. 정상/저전력은 이 동결의 결과다. v5는 소스284·외부94자산, SHA256 a682fa060dd07d50b3541264ebc2dab22cef570eaeea44b6bb6c6e90e32afe36다. 후속 변경은 클라이언트 지연 파괴·worker 예외 회수·실제 취소 뒤 HOLD 기록·goal 메타데이터·lift 주입 시점·개발 회귀 도구다. v5 정상 전체 mission을 다시 돌린 것으로 표현하지 않는다.

v6 이후는 판정 파일의 덮어쓰기 방지·새 출력 이름 지원·파지 취소 판정 항목 이름과 archive 복원 metadata 보완이다. 제어·물리·임계값을 바꾸지 않았다. 세 실제 BT 사례는 원래 mission_verification.json을 보존하고 mission_verification_v6.json으로 오프라인 재판정하여 모두 PASS를 확인했다. 물리 계산 결과도 새 이름의 로그/JSON으로 보존했다. 판정 보완 때문에 장시간 engine을 다시 돌리지 않았다.

최종 배포 동결은 v7의 소스285·외부94자산이며 SHA256 2f024c9362e1ab5d50d8c6cac7163ef0c6bc6daedff928a3338a65748ce6a179다. v5 이후 제어 경로는 그대로이고 판정 보존·archive 복원 연계만 보완했다.

v3 실행 시점의281개 소스는 source_v3_verified/runtime_source.tar.gz에 보관했다. 현재/과거 Git 객체와 당시 default 값을 이용해 동결 SHA256과 **모든 바이트가 일치**하는지 확인한 사후 소스 보존이며, 새 물리 실행 증거는 아니다. 외부94모델·가중치는 포함하지 않는다. 동적 profile 세 사례의 compiled model hash는 모두 a11a9aa45cca680b879ea137c81f9a903d78326f10ae245d80ce716ab5610e78로 같았다.

## 부품 검증과 실패 보존

- 초기 기존+신규232 PASS/64.02초.
- 공식 패턴 대조 후 ACK/ROS snapshot·실행 Python 경계 시험을 추가했다. v4 checkpoint의 전체240 PASS/63.56초.
- lift 주입 helper 포함 신규28 PASS/4.97초, 판정 보존 보완 후 전체242 PASS/64.79초. **archive 모델 제외·hash 복원·기존 판정 보존까지 포함한 최종 전체243 PASS/61.24초**.
- 별도 build6+1개 성공. 설치 감사에서 기존 navigation34항목·manipulation24항목·새 BT6모듈 및 외부94자산 일치.

정상 archive는 빈 별도 폴더에44개 파일을 hash 검증 복원한 뒤 오프라인 BT/물리 재판정 PASS를 확인했다. 원격 clone을 새로 검증하거나 engine을 새로 실행한 것은 아니다. 최종 잔여 검사도 소유 스택 없음·공유 lock free로 PASS다. 집계는 Ch13/evidence/section_13_7_bt/ACCEPTANCE_FINAL.json에 있다.

모의 CLI도 실제 실행했다. normal/fallen은 SUCCESS, low_battery는 ABORTED와 navigate/charge, not_found는 FAILURE와 navigate/find만 기록했다. 모든 모의 출력은 profile=mock다.

첫 실행 준비4423fd3b-41c7-438e-bc62-154a049f7d83은 엔진 시작 전 설치 감사에서 pydot 미노출로 실패했다. 원래 기록을 보존했다. 시험 실행기의 sys.path 보완이 실제 child Python에 전파되지 않는 원인을 재현했다. 개별 pydot 노출만으로는 argcomplete도 누락돼,13.7 전용 startup 경로가 ROS apt Python 의존성을 시뮬레이터 venv 뒤에 추가하도록 구조를 정리했다. NumPy는 계속 지정 venv 것을 쓰는 child-process 시험으로 확인했다. 전역 Python/venv 설정을 바꾸지 않았다.

과거13.6의213개 부품·v13 성공/FAIL·v14 정식 입력 손실 PASS와 동결은 보존했다.13.7을 v14 전체16개 PASS로 해석하지 않는다. 이번에는 영향받는 취소 경계·기본 hook 회귀만 선택하며 전체 engine matrix를 반복하지 않는다.

## 작업·게시 상태

기준 f9957a5535ff56b321db334a241cd689b4f3e583에서 별도 `feat/ch13-section-13-7` worktree를 만들었다. 기존13.6 worktree와 사용자 인계 파일은 보존했다. PR #115는 기존에 병합 완료였다. 이 작업에서 main 병합·기존 PR 수정·새 branch push/PR 게시를 수행하지 않았다. 로컬 commit으로 개발 결과를 보존한다.

이 검토는 단일 작업자 자체 검토이며 독립 검토보다 약하다. 검토 항목·수정 근거는 [자체 검토](SECTION_13_7_REVIEW_KO.md), 실행 순서와 판단 기록은 [진행 기록](SECTION_13_7_PROGRESS_KO.md)을 참조한다.
