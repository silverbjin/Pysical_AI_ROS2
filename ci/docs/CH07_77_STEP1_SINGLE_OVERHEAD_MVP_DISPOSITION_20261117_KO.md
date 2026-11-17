# Ch07 §7.7 — 단일 신규 파지 방향 검증·MVP 출판 범위 확정 (2026-11-17)

**Issue #173/#181, Draft PR #204.** 최초 단일 후보 이외 다른 파지 형태·새 최적화기·새 월드·가짜 결합·속도 sweep은 개발하지 않는다.

## 1. 원래 성공/실패 증거 (재실행 없음)

| 구분 | 독립 실제 증거 | 정확한 인정 범위 |
|---|---|---|
| G04A/E2 | [공개 CI #43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) SUCCESS | 실제 OGRE2 RGB-D→Depth/K/TF→G01→MoveIt 3단계 `plan_only` SUCCESS, arm/gripper **실제 motor Goal 0**. 240mm 높이 시험 rod 기준 |
| G04B 동일 물리 월드 카메라 | [공개 CI #43984345894](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) SUCCESS | 80mm 높이 rod, x=.70m·world-fixed base·bin yaw=.35rad의 실제 RGB-D/G01 **SCOPED PASS**; 관측 `base_link=(.6880574608,.0011689713,1.9436128276)m` at 16.204s, native rod centre `(.70,0,1.94)m`. motor Goal 0. G04B motor 전용 DART 미세 패치를 적용한 L2 물리 환경과는 구별 |
| 실제 G04B 과거 물리 | [C17 #43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279), [C18 #43806722104](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43806722104), [C19 #43807639093](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43807639093) | 50g 물리 원통 양손 접촉·lift·hold·일부 bin ROI 성공 있으나 native 금지 wrist–rod 접촉 **648/620/535건**, C19 최종 XY 초과. **G04B PHYSICAL FAIL** |

[MoveIt 공식 Pick-and-Place](https://moveit.picknik.ai/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html)의 `place→open→retreat` 순서만 참조. 기존 C17에서 실제 수직 배치는 wrist–bin 간섭으로, 측면 배치는 원래 grip/ROI의 5.66mm 부족으로 각각 먼저 REJECT된 상태.

## 2. 이번에 검토한 **단일 신규 후보**

후보 `ONE_VERTICAL_DOWN_TOOL_HORIZONTAL_JAW_OVERHEAD_PICK_PLACE`.

- 새로운 도구 설치/URDF 변경 없이 **기존 5DOF 팔이 원통을 위에서 수직 하향 tool +Z로 잡고**, 두 손가락의 jaw X는 수평으로 유지.
- 원래 finger collision centre는 tool +Z 방향 **0.10m**. 물체 접촉 중심=실제 80mm 원통 중심을 **정확히** 가정(물리 파지 성공 아님).
- 실제 픽업: rod centre `(.70,0,1.94)m` → 수직 다운 tool 손목 원점 `(.70,0,2.04)m`. shoulder `z=.6m`; 링크 길이 `0.5m+1.0m`. 수평 팔 x=.7m.
- 배치: 원래 solid bin centre `(.55,.25,1.63)m`, surface top `1.73m`; 높이 80mm rod 지지 시 centre `(.55,.25,1.77)m`, 손목 원점 `(.55,.25,1.87)m`.
- 원래 5DOF chain `Rz(q1) Ry(q2+q3) Rz(q4) Ry(qwrist)`. **동일한 한 자세**의 양/음 2R elbow 해만 계산하고 `q4=0`, tool-Z 다운 및 jaw-X 수평을 위해 `joint_wrist=π−(q2+q3)`를 요구. `joint_wrist`는 원래 ±1.5708rad 제한. 관절 목표를 clamp하거나 목적 물체를 순간 이동시키지 않음.

## 3. RED: 정확히 어디에서 막혔는가

| 독립 단일 후보 사전 조건 | 원래 source 기반 계산 | 판정 |
|---|---:|---|
| **픽업 손목 원점의 위치 도달** | `sqrt(0.70²+(2.04−0.60)²)=1.6011246m` vs 2R 최대 1.500m | **FAIL +0.101125m** |
| 배치 손목 원점의 *위치만* 도달 | 필요 1.4063783m ≤ 1.500m | 위치만 PASS |
| 배치 동일 자세의 positive elbow `q2/q3` | `−0.06525647 / +0.75554201rad` | 관절2/3 제한 내 |
| 배치 tool-down **손목 목표** (positive elbow) | `q_wrist=+2.45130711rad` vs max +1.5708rad | **FAIL +0.88050711rad** |
| 배치 반대 elbow도 동일 한 자세 | `q_wrist=+2.94382248rad` vs max +1.5708rad | **FAIL +1.37302248rad** |
| 실제 solid Bin vs 원래 `link4` 3D OBB SAT | positive elbow `−0.05324080m` (negative `−0.14646882m`); 원래 0.05×0.05×0.50m link4, bin 0.30×0.30×0.20m/yaw=.35 | **FAIL: 보수적 충돌 상자 분리 없음** |
| 실제 Bin vs 손목 OBB (가상 관절범위 초과 자세) | `+0.080m` | 손목 단독 분리; **link4/관절 한계는 여전히 FAIL** |
| 공식 MoveIt full-body FCL `plan_only` | `NOT_REQUESTED_PRE_FCL_HARD_REJECT` | source 필수조건 실패로 **호출하지 않음** |
| 실제 Gazebo/팔·그리퍼 motor Goal | **0건** | 물리 시험 NOT_RUN |

**해석:** 음수 SAT는 source 충돌 상자들의 **분리축을 찾지 못했다**는 뜻이며, 실제 엔진의 정확한 penetration depth 측정이나 full-body FCL 결과가 아니다. 다만 후보는 **픽업 위치 도달 불가, 배치 손목 관절 초과라는 독립적인 필수조건에서 이미 실패**했으므로 FCL 목표를 새로 실행할 명분이 없다.

**이 결과는 위에서 수직으로 잡는 이 *한 가지* 후보만 반증한다.** 기구학 해상도, 기울어진 top grasp, 다른 TCP, bin 세계 재배치 등 모든 대안이 불가능하다고 일반화하지 않는다. 그러나 사용자 승인 없이 그런 대안을 탐색하거나 새 프레임워크로 확장하지 않는다.

## 4. GREEN — 실패 경계 자동 검출 및 원본

신규 순수 표준 Python `ci/ch07_77_step1_single_overhead_grasp_preflight.py`는 **한 자세에 대한 두 IK 해·원래 wrist/link4 충돌상자·금지 Goal**만 검증한다. 이에 집중 5개 테스트 `ci/tests/test_ch07_77_step1_single_overhead_grasp_preflight.py` 추가. 기존 3분 L0 워크플로만 사용해 새 비용 높은 Gazebo 실행기는 만들지 않음.

- [공개 CI **#43993232265**](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43993232265) **SUCCESS** (집중 시험 5/5 GREEN). Artifact [#14287698406](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43993232265/artifacts/14287698406), **원본 ZIP SHA256 `c5e0cd006dacee7b947f37ec5261f822a47a3a13add99db5ec7bb9283c88034f`**.
- `single_overhead_candidate.json`: `pickup_position_reachable=false`, `supported_place_within_joint_limits=false`, `supported_place_source_collision_clear=false`, `moveit_fcl_plan_only=NOT_REQUESTED_PRE_FCL_HARD_REJECT`, `motor_goals_sent=0`, `candidate_status=REJECTED_PRE_FCL_HARD_GEOMETRY`.
- 성공한 E2 실제 3개 MoveGroup 계획 및 G04B 동일 월드 센서 시험 **재실행하지 않음**. 현재 신규 시험에서 ROS/Gazebo 동작/MoveIt motor Goal **0건**.
- **L0 GREEN != PHYSICAL SUCCESS**. 이 RUN의 성공은 '불가능한 Goal을 무조건 실행하지 않고 사전 차단'했다는 의미.

## 5. MVP 범위·교재 출판 판정 (STOP)

이 한 후보도 필수조건을 만족하지 못했다. **범용 top-grasp 최적화 / 추가 팔축 / URDF 관절 한계 완화 / Bin 축소·위치 변경 / 도구 attach·teleport / Goal 재시도 / 속도 sweep을 금지**하고 3개 작업 통합계획의 STOP 조건을 적용한다.

```text
SINGLE_OVERHEAD_CANDIDATE=REJECTED_PRE_FCL_HARD_GEOMETRY
STEP1_SOURCE_L0=PASS (reject boundary correctly)
G04B_80MM_SAME_WORLD_REAL_RGBD_G01=SCOPED_PASS (prior)
E2_REAL_RGBD_TO_MOVEIT_PLAN_ONLY=SCOPED_PASS (prior)
G04B_PHYSICAL_CLEAN=BLOCKED
CH07_77_PHYSICAL_PICK_AND_PLACE_E2E=BLOCKED
STEP2_MOTOR_E2E=NOT_RUN
STEP3_OWNER_WSL2=NOT_READY
G05=NOT_RUN
Ch10=HOLD
```

**교재용 확정 범위:** 기존 7.2~7.6 독립 기능과 Ch07 §7.7의 **실제 카메라 표적→시간·좌표 정합→G01 인수→MoveIt 계획 전용**까지만 *관측된 범위에서* 실습 가능. 실제 객체의 native grasp/lift/hold/drop·금지 충돌 0은 충족되지 않았으므로 ‘전체 Pick-and-Place 구현 완료’·‘안전 물리 인수 PASS’ 문구 금지. C17~C19와 이번 overhead 실패는 **교육용 실패 분석 사례**로 활용. `main` 병합 및 Owner WSL2 GUI 인수는 전체 물리 성공으로 오인하지 않게 별도 승인될 때만 진행.
