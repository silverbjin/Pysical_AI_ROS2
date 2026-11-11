# 13.8 Level 2 v45 최소 연결 보완 명세

Owner 결정: 정상 완주 기준 유지, 인수 보류. Level 2 정상 파지→운반→놓기 연속 실행을 목표로 한다. 개발 순서는 RED → GREEN → REFACTOR → REVIEW → COMMIT → 공개 CI 확인 → 실제 검증 → Owner 인수다. 전체 성공 전 10회 평가를 다시 시작하지 않는다.

## 원인과 근거

v44 기본 실행은 survey를 통과했으나 최종 위치·방향 동시 조건이 미달이었다. 기존 SE2 실험은 역주행과 RotationShim을 함께 선택하며 survey 진행 실패였다. 두 실패를 같은 구성으로 취급하지 않는다.

설치 Nav2 1.3.13 공식 NavFn 구현은 2D 경로 끝에 목표 방향을 부여한다. 경로의 마지막 진행 방향까지 일치시키는 보증은 아니다. Smac Hybrid는 DUBIN 전진 모션 모델로 목표 방향을 포함한 경로를 계획한다. 공식 구현과 테스트를 먼저 확인했다.

- https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_navfn_planner/src/navfn_planner.cpp
- https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/src/smac_planner_hybrid.cpp
- https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/test/test_smac_hybrid.cpp

설치된 실제 planner와 기존 static map으로 저장 출발 위치를 재현했다. v45_level2_heading_geometry/comparison.json의 실제 survey→최종 목표 비교에서 NavFn 마지막 4cm 이상 구간 방향 오차 .78454rad, DUBIN .12271rad였다. 두 경로의 보수적 filled footprint 검사 위반은 0건, 길이는 1.524m/1.545m다. 초기→survey도 두 경로 모두 계획 및 footprint 검사를 통과했다. planner lifecycle 정리 후 exit0이다. 이 결과는 계획 비교이며 실제 이동 성공이나 6.9도 잔여 오차의 제어 가능성 증거가 아니다.

가설: 최종 접근 방향이 목표 방향과 크게 다른 2D 경로가 마지막 제자리 회전을 요구하고, 원본 보행 정책의 회전 중 이동과 결합하여 XY/yaw 동시 도달을 방해한다. 전진 방향 고려 경로만 분리 적용하면 이 연결 문제를 줄일 수 있다. 실패하면 원본 로그로 가설을 재검토하며 제어기나 안전 임계값을 추가 변경하지 않는다.

## 순차 작업과 합격 조건

1. RED: 실제 launch와 ROS parameter parser 시험에서 Level2 기본 planner가 DUBIN이도록 기대하고 실패를 확인한다. controller는 기존 전진 RPP, 역주행 금지, stateful false, XY .015m/yaw .06rad와 기존 속도 상한을 동시에 검사한다. 다른 Level 기본 및 기존 실험 opt-in을 보존한다.
2. GREEN: Level2 carry_v1 기본에만 planner_server 전용 YAML을 추가한다. 설치된 nav2_smac_planner 의존성을 재사용한다. RotationShim·역주행 설정을 포함하는 기존 experimental overlay는 채택하지 않는다.
3. REFACTOR/REVIEW: 중복이나 불필요한 추상화 없이 설정 경계를 검토한다. 관련 시험과 전체 부품 시험을 실행한다. 검토자는 단일 작업자 자체 검토임을 밝힌다.
4. COMMIT/공개 CI: 선택 파일을 커밋·branch 게시하고 실제 공개 Job/runner/steps를 확인한다. portable CI를 ROS·물리 성공으로 확대 해석하지 않는다.
5. 별도 v45 source freeze/build/audit/runtime staging 및 새 UUID로 단일 Level2를 실행한다. overlap1/10Hz/SE2=0 조건을 명시하고 기존 제어·관측 수명·동시 도달·접촉·종료 기준을 유지한다. 정식 판정, 원본 source와 압축 증거, child/lock 종료를 보존한다.
6. 정상 연속 성공 이후에만 정식 평가와 최종 가이드/Owner 검토를 진행한다. 한 번의 개발 사례를 10회 평가로 대체하지 않는다.

## 범위

새 제어기, WBC, 학습, executor 재구성, freshness/TF/접촉/성공 수치 완화는 범위에 없다. 이 명세는 설정 재사용에 한정하며 정상 완주 또는 Owner 인수 완료 문서가 아니다. 공개 CI 실행 장애·Scan 수신 gap·Supervisor callback·localization shutdown의 층위를 섞지 않는다.
