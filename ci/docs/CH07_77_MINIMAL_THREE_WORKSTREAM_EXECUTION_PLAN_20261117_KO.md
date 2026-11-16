# Ch07 §7.7 — 출판용 최소 통합 인수: 3개 작업 단일 실행계획 (2026-11-17)

> **PLAN FIRST / GATE-BASED.** 본 문서가 먼저 확정된 다음 ①→②→③ 순차 진행한다. **이미 성공한 E2/G04A와 과거 G04B G00~G04A를 다시 인수하지 않는다.** 실제 물리 인수를 완료하기 전 `CH07_77_E2E=BLOCKED`; Ch10 HOLD; Owner WSL2 NOT_READY. 교재 목표는 *동적 빨간 원통 1개를 실제 카메라로 찾아 실제 Gazebo 로봇이 1회 집고 bin에 놓는 것*으로 제한한다.

## 기준선 및 증거 (이번 계획 작성 시 원격 대조)

- 코드 본선 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`.
- E2 통합 Draft [#204](https://github.com/silverbjin/Pysical_AI_ROS2/pull/204), HEAD `a69e1656537b406a1d51654e6710899785a37f8e`, base main. 기존 센서 기반 MoveIt `plan_only` 공개 CI [#43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) **SUCCESS**, Artifact `14249512043`; 모터 Goal 0.
- 실제 물리 Draft [#202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202), HEAD `96d4f4d4b586687b1bc1243cc0e5a9d7901007ef`. **base는 main이 아닌** 진단 계열이므로 #202 **전체 merge/cherry-pick 금지**. 필요한 함수·증거만 별도 표시하여 재사용.
- 기존 물리 C17/18/19 [종결 보고](https://github.com/silverbjin/Pysical_AI_ROS2/blob/96d4f4d4b586687b1bc1243cc0e5a9d7901007ef/ci/docs/BOOK_CODE_REVIEW_G04B_FINAL_20261117_KO.md): native wrist–rod 충돌 648/620/535건; C17 배치 XY 0.04244m지만 무충돌 FAIL, C19 최종 XY 0.13708m로 FAIL. **C17을 안전 PASS로 전환 금지**.

## 작업 ① — 좌표·물리 해제 기하학 정합 (차단 작업: 코드 확장보다 원본 분석)

**목표:** 실제 G04A RGB-D source XYZ→rod center→2-finger jaw contact/손목 frame을 **동일 world/base/model**로 정합하고, 해제 순간 손목이 낙하 원통의 swept volume 밖에 있도록 기존 native 증거를 기반으로 **단일 후보**를 작성한다.

**필요 작업(최소):**
1. 기존 `ci/ch07_77_g04a_graspable_fixture.py`와 #202의 `ci/ch07_77_g04b_physics_fixture.py`, world-fixed base SDF, bin yaw, 원본 5DOF URDF·sensor extrinsics를 *읽기 전용*으로 비교. G04A rod x≈0.8 vs G04B C17 rod x≈0.7, robot spawn z≈+0.05 vs world-anchored z=0, bin yaw 차이를 소스/원본으로 명시.
2. 손목/손가락 native collision shape, rod radius/height, bin ROI, C17 release 전후 native world pose·collision timeline을 같은 프레임·시각으로 대조. 하나의 **물리 합당한 release clearance 후보**만 도출. 속도 sweep·새 접촉 계측기·world teleport·충돌 임계치 완화 금지.
3. 변경 후보를 기존 `mission_geometry`의 **fixture 전용 파라미터/검사**에 반영한다. pure-Python L0(좌표계/센서 의존성/기하 collision clearance)와 현존 MoveIt plan-only/FCL 중 필요한 부분만 확인. 센서 Goal을 Gazebo ground-truth로 대체하지 않는다.

**종료 판정:** `STEP1_READY_FOR_L2`는 (a) 단일 fixture manifest/world-base-rod-bin transform 명시, (b) 관측 표면→rod→jaw/TCP 변환의 근거, (c) release candidate가 기존 금지 접촉을 피한다는 계산 및 충돌 없는 MoveIt 계획 후보(정적 근거)가 모두 있을 때만. **증거 부족이면 `STEP1_BLOCKED`**; 새로운 물리시험 금지. 이 단계의 L0 GREEN은 물리 인수 PASS가 아니다.

## 작업 ② — 기존 코드로 한 물체 실제 인식→물리 집기·배치 단일 통합

**선행조건:** 작업①의 **STEP1_READY_FOR_L2**. 미충족 시 새 물리 Goal 실행 금지.

**최소 구현:** E2 `target_ready`의 실제 stamp/xyz를 기존 #202에서 확인된 **MoveGroup plan/actual arm execution + 2-finger FJT + native Gazebo contact/rod pose witness**에 연결하는 얇은 1회 executor. 새 범용 FSM·Task Constructor·YOLO·다중 물체·추가 기구학 라이브러리 금지. 해제 자세/withdraw 궤적은 작업①의 후보 한 가지로 고정하고, G04B 1,270행 witness를 새 코드에 통째로 복제하지 않는다.

**실제 CI 인수 1회(승인형):** 같은 ROS2 Jazzy/Gazebo Harmonic digest·같은 SDF/URDF/robot base·같은 timestamp 세션에서 image→pixel→Depth/K/TF→G01→MoveIt real plan/execute→actual 5-arm/2-finger controller feedback→rod bilateral native contacts/lift/hold/high/lower/release→settled bin ROI를 독립 원본으로 연결. **motor Goal은 CI 소유 simulation에만**. 이전 성공 run을 합산하거나 테스트 입력으로 native rod ground truth를 Goal에 주입하면 무조건 FAIL.

**필수 인수 기준(기존 보존):** real dynamic 50g rod/static=false; 두 손가락 native contact; 실제 상승≥0.05m; hold≥1s; 배치 XY≤0.09m, 높이오차≤0.055m; **손목–rod/금지 wrist–support collision 0**; 실제 Action UUID/Result + joint feedback + native world pose + 정상 종료 + raw Artifact/SHA. 사전 승인 없는 ROS motor Goal 금지. **하나라도 불충족이면 `STEP2_BLOCKED` / `E2E=BLOCKED`**. 실패 후 최초 원인·단일 재현 가설이 확정되지 않으면 L2 반복 금지; 가설 1개 확인 시에만 변경 1건·추가 1회 조건부 검토.

## 작업 ③ — 교재·출고 판정 및 Owner WSL2 1회

**선행조건:** 작업② 동일 세션 물리 인수 GREEN일 때만 정식 최종 GUI 인수로 진입. 실패 시 실패·미검증 상태를 교재에 그대로 명시.

- `Ch07/docs/LAB_7_7_GUIDE_KO.md`의 G01 엔트리·subscription 부재라는 **과거 오류 서술 수정**; 기존 `LAB_7_7_E2_REAL_SENSOR_MOVEIT_PLAN_ONLY_KO.md`와 일관되게 상태별 강사/학생 실행 구분.
- 동일 CI/Owner WSL2용 단일 실행 진입점, 원본 source SHA, container image digest, fixture manifest, raw receipt/ZIP SHA256, 실제 Gazebo·RViz GUI 표시와 정상 종료 절차를 안내.
- 실제 인수 성공 후에만 강사 WSL2 GUI **1회**로 최종 accept; CI scoped success와 현장 Owner acceptance는 구분. 본선 PR에는 **증거가 입증된 변경만** 병합한다. Ch10 HOLD와 101개 총괄 실습 판정은 확장하지 않는다.

**최소 산출물:** 이미 있는 [E2 개발 보고서](CH07_77_E1_E2_REAL_RGBD_MOVEIT_DEVELOPMENT_DEBUG_REPORT_20261117_KO.md) 재사용 + ① fixture/collision 원인·단일 후보 기록 + ② 필요시 CI source/receipt + ③ 기존 가이드 수정·최종 인수 기록. 새 디자인 문서/대형 E2E 프레임워크를 양산하지 않는다.

## 일정·비용 제약 및 STOP 규칙

- **작업은 의존 순서 ①→②→③**, 각 단계는 이전 Gate 충족 시만 진행. **최대 새 기능**: 하나의 교정 후보, 하나의 얇은 actual simulation executor, 하나의 통합 원샷, 기존 문서 1종 수정. 파일 개수나 코드 줄 수가 목적이 아님.
- 소스와 수치 근거 없는 속도/허용차/목표 반복 튜닝 금지. 이미 성공한 G04A/E2의 실제 CI 재호출 금지. 단위 수학·정적 계약 검사는 L0만; 신규 실제 물리 L2는 유효한 새로운 반증 가설에서만 최대 최초 1회.
- 계획/오프라인 검증이 물리 무충돌 경로를 증명하지 못하면 **한계가 드러난 상태로 작업① BLOCKED에 정지**. 실패를 숨기고 가짜 안전 PASS를 쓰지 않는다.
- `main` 자동 병합, Owner WSL2 실행, Ch10 작업은 범위 외. `G04B_PHYSICAL_CLEAN=BLOCKED`, `CH07_77_E2E=BLOCKED`를 실제 적격 raw로 반증하기 전까지 유지.
