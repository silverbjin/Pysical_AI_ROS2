# 13.6 최종 자체 검토

2026-11-04 KST. 범위는68cb78972ebf861d8ed5fd09b2fe062df0d1e908→fd846261541dc9dafe69a07270a1bcbaaf188da0(15 commits)와 게시 문서 보완이다. 사용자 단일 작업자 지시로 별도 agent/reviewer를 생성하지 않았다. 작성자 자체 검토이며 독립 검토보다 약하다.

전체 변경 파일 목록·범위와 주요 제어/수명/모델/판정 코드를 별도 확인했다. 생성 데이터·긴 관측·압축 증거는 줄별 수동 검토 대신 원본/manifest hash 대조로 확인했다. 전체 diff 자료는 보존된 작업 기록의 review-68cb7897..fd846261.diff(57,049,194bytes)에 있다. 이 수치를 실행 코드 크기로 해석하지 않는다.

검토 초점:

- lease: 원본 capture/receipt와 seq/session/goal·TF를 구분하며 반복 heartbeat가 수명을 늘리지 않음. 만료·중복·과거 session 실측/시험과 대조.
- 단일 PD 쓰기·action reservation·C2 bounds·실측 terminal·취소 감속/hold: trajectory·action_bridge·engine_extension·planning을 대조. 새 보간은 독립 spline 비교와 실제6축/취소/손실/파지로 검증됨.
- 동적 freejoint: 원래27/26 로봇 상태 뒤에 추가, joint/actuator indexing·질량·힘 cap 불변 대조. target truth는 post-run 판정 전용. planning scene attach는 물리 부착이 아님.
- MoveIt: 실제 base TF·고정 TCP/FK·단일 scene와 실행 직전 revision/hash/실측 상태/관측 재검사. partial Cartesian·충돌·불가 거절과 실제 취소 결과 대조.
- 수명: 성공/실패 때 RX/renderer/native worker·자식 정상 join, planner를 engine보다 먼저 회수, 잔여 검사. 16개 실제 사례의 clean count10/11/12를 각 실행 구성과 대조.
- 게시 경계: 원본94자산·모델/가중치·생성 description을 재배포하지 않음. sources/·다른 장·사용자13.4 debugging 문서가 이번 stage에 없음. 기존114파일 동결·R5 install을 새 성공으로 덮지 않음.
- 판정: raw_loss 기존 FAIL 보존과 좁은 별도 검토를 명시. 새 검토는 실행 소스 변경이 아니며 별도 hash로 식별. 원래16/16 PASS라는 표현을 사용하지 않음.

이번 검토에서 새 Critical/Important 수정 항목은 확인하지 않았다. 확정한 미처리 Minor는 없다. 확인 근거는199개 부품 시험, 별도12개 판정 시험,15개 기존 판정 PASS+1개 보완 검토 PASS, source/install/asset/증거 감사다. 정적 검토로 모든 결함이 없음을 증명한 것은 아니다.

판단 범위에서 제외한 사항과 이유: 실기 하중/드라이버·전신 CoM 보상·새 보행 정책·SLAM/일반6D 인식은 원고 연결의 이번 교육 profile 밖이며 검증 환경이 없다. 각 시나리오1회는 반복 강건성을 증명하지 않는다. raw_loss의 특정 platform freshness 항목은 당시 증거가 없어 확정하지 않으며 좁은 안전 정지 분류만 인정한다. 이 한계를 최종 보고서에 유지한다.
최종 문서/가이드 검증 보완: 새 sparse clone에서 package-data config 누락을 실제 build FAIL로 발견하고 Ch13/config 다운로드 범위만 수정했다. 원래 runtime은 불변이다. 같은 별도 build6개62초, 설치34+23/원본94hash PASS, 빈복원39+39+38+25파일, 대표판정4개 및 grader12PASS0.19s. 첫 실패 로그도 보존했다. 이 보완은 소스/제어 변경이 없어 기존 engine 인수를 반복하지 않았다. 새 OS 설치 검증은 아님.
## 2026-11-04 정식 입력 손실 판정 후속 자체 검토

사용자 승인 범위의072bf763→873ad8fe와 후속 보고서/증거를 별도 확인했다. 안전 _fresh 조건·명령/PD·물리 주기·수명 한도는 불변이며 진단은 최초 _fresh=false 때만 고정 기록한다. 정식 CLI는 기존 물리 계산기의 모든 수치/회수 검사를 유지하고 fault-empty 항목만 시나리오 계약으로 대체한다. 정상 timeout·무관한 source/clock/graph/owner 만료·주입 전 fault·이력 은폐·재움직임은 거절한다. 주입 기록은 실제 owned PID 검증 뒤 SIGSTOP 전/후를 구분한다. 테스트213 PASS와 새 실행의22검사 PASS·실측 최초 raw/safe wall 만료를 대조했다. 새 Critical/Important 미해결 항목을 확인하지 않았다. source251/94의v14는 이 입력 손실1회만 실제 재검증했으며 이전15개를v14PASS로 확대하지 않는다. 단일 작업자 자체 검토의 한계는 유지한다.