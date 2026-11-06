# v35 실제 결과와 기준 제어 복귀 대조 명세

2026-11-06 KST. 새 후진/목표 회전 조합의 부품 PASS를 실제 인수로 확대하지 않는다.

## v35 실제 결과

- L3 dfcd2bc6-d8d1-44f3-b0cc-a0634bbba959: survey와 서쪽 접근 이동 이후 RR_thigh:world:WAITING 금지 접촉으로 engine ERROR. 그 뒤 clock/base/joints/capture 정지에 따른 VISION_EXPIRED는 후속 현상이다. trial 58.446sim/216.592wall초, child 11/12 정상 종료, 잔여 0.
- L2 272870f5-e785-4d52-8b08-e966cf65d738: survey deadline FAIL. engine 정상 종료·child 12개 정상 회수·잔여 0. 엄격 1.5cm 목표의 문제가 전부라고 단정하지 않는다. 저장된 ROS pose에서 survey 목표 최근접 오차도 164.171mm였다.
- L3 서쪽 접근의 최근접 XY 2.479mm일 때 yaw 오차는 1.0106rad였다. 위치와 yaw 오차가 동시에 1.5cm/0.06rad 안인 표본은 없었다. 6cm/0.06rad 조건에 들어온 표본은 있었지만 이를 실제 성공으로 재판정하지 않는다. 이 가상 판정 때문에 운영 허용 오차를 늘리지 않는다.
- 두 사례의 원본·정확한 v35 source archive·원래 판정을 보존한다. 새 10회 기능 gate 미통과다.

## Ruling과 후속 범위

v30~v35의 도달/경로 제어 보완이 실제 통과로 연결되지 않았다. Ruling: 설치 reference가 존재하는 것과 이 Go2의 물리 추종 성공은 다르므로 새 SE2/후진/shim 조합은 기본에서 철회하고 명시적 실험 opt-in으로 남긴다. 기준은 실제 v28의 L2 연속 완료 1회 및 L3 pre-grasp까지 도달한 4회에서 사용한 NavFn/RPP 구성이다. 이 복귀가 물리 성공을 보장한다는 뜻은 아니다.

유지할 최소 수정은 충돌로 원인이 확인된 L3 pre-distance .03, L2 보수적 yaw cap .10, 원본 관측/health 계측과 직렬 기본 순서, native 파지 기반 지도 갱신/소유권/수명 및 모든 실제 물리 판정이다. ROS owner/goal/lease 구조, 원래 XY .015/yaw .06 제어 허용 오차, 3cm/120초/높이20mm 평가 목표는 유지한다. 원래 기준의 goal checker/RPP stateful=true 의미를 복원하되 terminal 뒤 실제 정착 좌표와 fresh 관측을 다시 읽는다. Nav2 SUCCESS를 실제 3cm 도달로 표현하지 않는다.

L2의 새 SE2용 survey(1.6,-.3,.6)는 실제 도달하지 못했다. 기본 대조에서는 (1.9,.3,atan2(.7,1.1))처럼 기존 박스와의 footprint 여유를 확인할 수 있는 관측 지점을 먼저 부품 검증한다. 이전 (1.7,.3,atan2(.7,1.3)) 지점의 보수적 footprint 충돌을 알고 그대로 강제하지 않는다. 실제 Renderer 가시성도 확인한다. L3 survey는 기존 (1.9,.4,atan2(.6,1.1))를 유지한다.

NavFn은 SE2 body orientation 경로가 아니다. 새 filled-footprint SE2 pose 검사는 실험 모드에서만 해당 의미로 사용한다. 기본 모드는 기준의 endpoint footprint·fresh 실제 위치 IK·Nav2 collision projection·native 500Hz 금지 접촉 판정을 유지한다. NavFn quaternion을 실제 body heading으로 오해해 전체 SE2 안전성을 주장하지 않는다. 기존 원고의 실제 성공 증거와 동일한 안전 경계를 대조하며 새로운 물리 접촉은 그대로 FAIL이다.

## 순차 검증

1. 기본과 실험 설정을 분리하는 실제 ROS parser 검사와 survey footprint/Renderer 검사를 먼저 RED로 확인한다.
2. CH13_EXPERIMENTAL_SE2=1일 때만 기존 v35 SE2/후진/shim을 선택한다. 기본 NavFn/RPP와 원래 stateful 구성을 복원하고, 실험 모드의 검사도 유지한다. 기존 legacy/L1에 새 동작을 주입하지 않는다.
3. 관련 검사 → 분리 build/전체 회귀 → 새 v36 이상 freeze/테스트·실행 전수 hash → 사전 UUID 및 보고/커밋 후 단일 engine으로 대조한다. 이전 실패를 재사용/덮어쓰지 않는다.
4. 실제 연속 기능이 확인되면 새 고정 10회로 평가한다. 목표 미달은 원래 strict FAIL로 남긴다. 불필요한 과거 matrix 재실행은 하지 않는다.

## 2026-11-06 구현 전후 부품 검증

기본 구성 검사 2 FAIL/437 deselected(26.22초), 모드가 scenario hash에 들어가는 검사 3 FAIL/439 deselected(26.17초)를 먼저 확인했다. 기본/실험 설정 분리와 새 survey footprint/실제 Renderer를 포함한 관련 검사는 20 PASS/30.68초다. 모드는 scenario.record의 navigation_profile로 동결되며 기본/실험 조건이 같은 source만으로 혼합되지 않도록 한다.

기본 상태는 기존 NavFn/RPP와 stateful=true다. 원래 XY .015/yaw .06 및 엄격 수치 판정은 유지했다. 실험 SE2의 전체 pose 검사는 CH13_EXPERIMENTAL_SE2=1에서만 사용하며 기존 source/실제 실패 증거는 그대로 보존했다. 전역 설정이나 모델·정책·물리 guard를 변경하지 않았다. 다음은 v36 전체 검증과 실제 대조다.

공식 [NavFn 1.3.13 구현](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_navfn_planner/src/navfn_planner.cpp)의 getPlanFromPotential도 확인했다. 중간 pose orientation은 identity로 채우며 이것이 이동 중 로봇의 body heading을 뜻하지 않는다. 따라서 SE2 pose 검사를 기본 NavFn 경로의 회전 안전 보증으로 해석하지 않는다. 기본 endpoint·fresh IK·실시간 collision/물리 guard는 유지한다.

v36 실행 전 확인: 분리 build 5개/16.0초, navigation39/manipulation24/BT6 및 실제 venv child69 module 감사 PASS. 전체442 PASS/69.00초, source384/외부94자산 및 테스트·실행 소스 전수 hash 일치 PASS. manifest f0b4f1bc276109e822db030e2793bea863c1ee1e8558dc560f2ea6a04559c5d2. 두 실제 대조 UUID와 experimental_se2=0을 step4_preflight_v36/case_plan.json에 사전 고정했다. 실제 기능 성공 주장이 아니다.
