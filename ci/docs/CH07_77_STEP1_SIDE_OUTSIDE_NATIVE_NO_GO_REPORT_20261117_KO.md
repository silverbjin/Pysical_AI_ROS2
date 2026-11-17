# Ch07 §7.7 작업① — C17 원본 파지의 측면 배치 기하학 NO-GO (교육용 개발·분석·디버깅 보고)

_2026-11-17 | Draft PR #204 | Issue #173, #181 | NO NEW ACTUAL GOALS_

## 0. 중단 지점과 실제 판정

이번 재개는 새로운 G04A 센서 시험이나 G04B 과거 물리시험을 반복하는 작업이 아니다. 앞서 확보한 다음 **서로 다른 범위의 원본 성공·실패**를 보존한다.

- 동일 G04B 80mm 물리 원통·world-fixed base·bin yaw=.35rad에서 **실제 OGRE2 RGB/Depth/CameraInfo/TF → G01** [CI #43984345894](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) **SCOPED_PASS**. raw target stamp 16.204s, `base_link=(0.6880574608,0.0011689713,1.9436128276)m`, native rod center `(0.7,0,1.94)m`; 실제 motor Goals 0. 기존 E2의 240mm 물체와 혼동하지 않는다. **센서 시험은 G04B DART motor-specific 1mm patch를 적용한 물리 구동 인수가 아니다.**
- G04B C17 [CI #43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279) native 실제 양손 force/lift/hold/bin 배치 성공 일부. 그러나 **원래 wrist–rod 접촉 648건 / ≈17.13N**, G04B physical clean **FAIL**.
- [공식 MoveIt 단계별 Place→UnGrasp→Retreat 기준선](CH07_77_STEP1_PHYSICAL_SUCCESS_BASELINE_RESEARCH_20261117_KO.md)을 채택했으나, [직전 supported-place 검증](CH07_77_STEP1_REAL_SHORT_RGBD_AND_SUPPORTED_RELEASE_BASELINE_REPORT_20261117_KO.md)은 C17 동일 손목 자세에서 수직 하강 시 실제 지지 Bin에 먼저 충돌: rod bottom-to-bin gap **0.143252m**, wrist–bin collision before **0.0658m**. **수직 하강 후보 REJECT**.

다음 단일 구조 후보였던 **`SIDE_OFFSET_WRIST_OUTSIDE_BIN_THEN_LOWER_TO_SUPPORT_OPEN_THEN_RETREAT`**의 *필수 수평 기하학 조건*을 검증한다. 새 물리 Goal을 보내기 전에 구조적 반증을 얻는 것이 목적이다.

## 1. RED — 실제 C17 원본에서 외측 손목 이동 거리 상한 측정

- source native 원통 중심: `(0.503606, 0.238149, 1.91499)m`, sim≈69.542s.
- source 실제 5DOF 팔 관절 `[0.509164,-0.331197,1.049568,1.569168,-0.346061]rad`.
- 기존 `ci/ch07_77_step1_offline_geometry.py` (원본 URDF chain `Rz(q1) Ry(q2+q3) Rz(q4) Ry(qw)`)로 **손목 OBB 중심** `(0.4538768271,0.2417278948,1.8469640255)m`. 한 번만 +0.03m tool-local-Z 적용; 센터 이동 중복 금지.
- 실제 C17 **원통 중심 ↔ 손목 충돌 상자 중심 거리** `d=0.084340573466m`. 동일 양손 파지를 미끄럼 없이 유지할 때 회전은 이 3D 거리 `d`를 늘리지 않는다.
- 기존 변경 불가 배치 한계: 원통 중심은 bin center `(0.55,0.25)`의 **XY 반지름 0.09m 이내**.
- Bin은 실제 0.30×0.30m yaw=0.35rad solid support, 반폭 0.15m. 손목 원본 collision OBB는 0.08×0.06×0.06m, 세 반폭 `(.04,.03,.03)m`.

## 2. 원인 판정 — 어떤 방향으로도 수평 완전 분리에 최소 5.66mm 부족

손목이 bin의 **수평 투영 밖으로 완전히 이동**하려면 어떤 수평 분리축 `n`에서 적어도

```text
bin support projection halfwidth(n) >= 0.150m
wrist OBB projection halfwidth(n) >= min(.04,.03,.03)=0.030m
necessary centre separation in n >= 0.180m
```

이어야 한다. Box 회전 yaw=.35rad와 wrist 3D 회전 여부에 관계없이 두 투영 반폭 하한은 유효하다. 반면 동일 C17 파지 변환(원통–손목 center 3D거리 `d` 보존), 원래 bin 배치 ROI 안의 모든 목표에서는 삼각부등식에 의해

```text
distance_xy(wrist centre, bin centre)
<= distance_xy(rod centre, bin centre) + distance_3D(rod, wrist)
<= 0.090000 + 0.084340573466
= 0.174340573466m
needed >= 0.180000m
shortfall >= 0.005659426534m (5.66mm)
```

따라서 **실제 지지 Bin 옆으로 손목 상자 전체를 빼고 원통 중심은 기존 ROI에 유지하는 방식은 C17의 고정 파지 기하에서는 불가능**하다. 단일 후보의 구조적 반증이지 **모든 5DOF 물리 배치가 불가능하다는 주장 아님**. 손목을 Bin **위쪽으로** 분리하는 새 파지 자세, 다른 gripper-to-object 변환, 변형 물리환경은 이번 수평 NO-GO 범위에 포함되지 않는다.

실제 C17의 측면 해제 후속으로 이미 실시한 C18/C19는 서로 다른 `q3` 후퇴 속도를 사용했으나 native wrist–rod 충돌 620/535건과 C19 ROI 실패가 관측되어, **속도 sweep 재개 금지**.

## 3. GREEN — 실제 검증한 것은 안전한 중단 조건

새 코드:
- `ci/ch07_77_step1_side_outside_no_go.py`: **순수 Python**, source FK/원본 C17 native rod/wrist·Bin 실제 크기·기존 ROI의 **필요조건 NO-GO 증명**.
- `ci/tests/test_ch07_77_step1_side_outside_no_go.py`: 4개의 source 수치/충돌 분리/범위 과장 방지/NaN·Inf·가짜 관절 rejection 시험.
- 기존 `.github/workflows/book-ch07-77-step1-offline.yml`의 **3분 집중 L0에 추가**. 새 Gazebo runner/새 Docker 이미지/추가 L2 승인 흐름 생성 없음.

공개 CI [Run **#43990332971**](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43990332971) **SUCCESS**, [Artifact #14288215470](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43990332971/artifacts/14288215470), raw ZIP SHA256 `304d2e7f2c523b3ef88044251de22f1404f22afc5d3c41681f415376f1abb817`. `side_outside_no_go.json` 실제 판정:

```text
native_rod_to_wrist_box_center_distance_m=0.08434057346593132
max_wrist_center_distance_from_bin_m=0.17434057346593132
necessary_wrist_footprint_separation_distance_m=0.18
minimum_unachievable_horizontal_separation_m=0.005659426534068673
fixed_native_grip_outside_xy_feasible=false
candidate_status=REJECT_FIXED_C17_GRIP_WRIST_OUTSIDE_BIN_XY
physical_goal_authorized=false
status=STEP1_BLOCKED
step2_motor_e2e=NOT_RUN
owner_wsl2=NOT_READY
```

**CI 성공은 기하학 실패를 올바로 탐지했다는 의미**다. 실제 Gazebo 물리 파지/해제 성공을 의미하지 않는다. 이미 성공한 실제 동일 월드 RGB-D 시험을 다시 실행하지 않았고, 새로운 팔·그리퍼 Goal 0건이다.

## 4. REFACTOR/REVIEW — MVP 확장 차단 및 선택지

1. **기존 입출력은 유지:** G04B 80mm 동일 카메라 목표 + surface→rod→wrist 실측 보정은 재사용. 새 6DOF grasp optimizer/YOLO/MTC FSM/DART 재개발은 **불필요**.
2. **기존 C17 고정 양손 파지 + 원래 solid Bin ROI + 손목 완전 측면 분리** 조합은 이번 필요조건에서 명확히 REJECT. 추가 관절 목표 탐색, 후퇴 시간 0.8→0.25→... sweep, 가짜 native collision 제외는 수행하지 않는다.
3. 다른 구조 후보는 **실제 원통을 지지한 채 손목이 Bin 위에 남을 수 있는 alternate grasp/tool orientation**이다. 이는 기존 C17 손목–원통 상대변환을 바꾸는 새 파지이며, 실제 80mm 물체의 초기 위치 `x=.70,z=1.94`에서 5DOF reach/2-finger native 접촉/Full-body MoveIt FCL을 먼저 증명해야 한다. **현재 검증 안 됨**.
4. 만약 그 후보를 1개의 source-bounded reach/pose/FCL 확인으로 입증할 수 없다면, **교재용 축소 프로파일**을 명시해 `RGBD→G01→MoveIt_PLAN_ONLY=ACCEPTED` 및 `PHYSICAL_PLACE=BLOCKED`로 출판하는 것이 기존 합격 결과를 지키고 과도개발을 막는 대안이다. 다만 이것을 전체 물리 Pick-and-Place 성공으로 부르지 않는다.

## 5. 상태·인수

```text
G04B_80MM_SAME_WORLD_REAL_RGBD_G01=SCOPED_PASS
C17_SAME_GRIP_WRIST_SIDE_OUTSIDE_BIN=REJECTED_STATIC_PROOF
C17_VERTICAL_SUPPORTED_PLACE=REJECTED_STATIC_AND_NATIVE_BOUNDARY
STEP1_READY_FOR_PHYSICAL_MOTOR_L2=NO
G04B_PHYSICAL_CLEAN=BLOCKED
CH07_77_E2E=BLOCKED
STEP2_MOTOR_GOALS=0 / NOT_RUN
STEP3_OWNER_WSL2=NOT_READY
Ch10=HOLD
```

**검증 범위 주의:** 수평 2D 완전 분리의 필요조건 증명은 실제 3D 손목–rod/bin 충돌 전체를 평가한 것은 아니다. 특히 손목 전체가 bin 위에 위치하는 새로운 파지 형상은 반증하지 않았다. 실제 full-body FCL/native zero forbidden contacts는 여전히 물리 수락의 필수 조건이다.
