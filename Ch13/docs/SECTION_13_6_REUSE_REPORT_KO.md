# 13.6 Go2+Piper 정밀 조작 최종 인수 보고서

갱신: 2026-11-04 KST. **기능 인수16개 확인 완료: 기존 판정15 PASS, 입력 손실1개는 원판정 FAIL을 보존한 별도 검토 PASS.** 게시본 다운로드 검증은 별도 게시 보고서로 확정한다. 원판정16개가 모두 PASS였다고 주장하지 않는다.

## 실행과 판정 기준

- branch `feat/ch13-section-13-6-manipulation`, runtime commit `255b65fb`.
- runtime 동결 `section_13_6_reuse_acceptance_v13.json`: 소스248개·외부94자산, SHA256 `67da28691991d81152526919e5a4c65fec91ba3d75e1d84a5fc2681901d39101`.
- 16개 모두 같은 실행 소스·별도 build `/home/jinho/ch13_reuse_13_6_build`를 사용했다. 기존 R2/R5 install과 원본 자산을 보존했다.
- Ubuntu24.04/WSL2, ROS2 Jazzy, MoveIt2.12.4·moveit_msgs2.6.0·TRAC-IK2.0.2, Python3.12.3·MuJoCo3.13.0, CPU Torch2.9.0·ONNX Runtime1.31.1의 기존 설치 환경이다. 이번에 apt/pip·드라이버·전역 설정은 변경하지 않았다.
- 기존13.5 v3의114파일 동결과 같다고 주장하지 않는다. 각 실행의 freeze/install/model/ELF 감사와 실제 compiled model·정책 hash는 증거에 기록했다.
- 별도 오프라인 판정기 `Ch13/verification/reuse_13_6/`는 실행 동결에 속하지 않는다. 판정기·반례 시험·실제 축약 fixture의 hash는 [인수 집계](../evidence/section_13_6_reuse/ACCEPTANCE_V13.json)의 `grading_files_sha256`에 별도 고정했다. 실행 소스나 과거13.5 판정기를 바꾸지 않고 저장 결과를 재검토했다.

## 사례

| 사례 | 실제 UUID | 결과 |
|---|---|---|
| held_cancel | `4448d833-3500-4108-8b00-2464f67aba00` | PASS |
| pick | `20662d06-ec82-4232-8a8a-6426d347557e` | PASS |
| moveit | `70837980-da92-49a0-b542-563a5f07f2c2` | PASS |
| arm_normal | `38925c2b-85d0-4c09-81db-31151bb35bbc` | PASS |
| arm_cancel | `790f235e-ff61-41c1-a5cc-703d31cf72ad` | PASS |
| arm_loss | `bce14d0a-c5d6-439c-9743-86d4cb452d7a` | PASS |
| observation_loss | `16a605ae-e298-4454-9d10-d657b35bcdca` | PASS |
| duplicate_action | `41690c45-5257-4e68-9178-3d96b9698ca0` | PASS |
| hold | `eab6c5ef-1959-427c-92c2-c669a04fb02c` | PASS |
| expire | `e3a1322f-a6a2-48f8-a19f-da2cc1564f60` | PASS |
| old_session | `7f4d5024-0602-4a89-b38e-7f2ba65c04dd` | PASS |
| duplicate | `12453ff2-5f90-4cde-8680-0a217e75a347` | PASS |
| nav_free | `b2bc70cf-b60e-49d8-b387-71ff4bb078f5` | PASS |
| nav_cancel | `b69137ad-162b-4a34-bc8f-41fdafcb3303` | PASS |
| nav_raw_loss | `a854efd7-67fc-4964-aced-0fd36b59f7bf` | 원판정 FAIL / 별도 검토 PASS |
| nav_vision | `44e4c3f4-190b-4f71-b3d0-886b30b6fe47` | PASS |

모든 사례에서 owned 자식 정상 종료·잔여 PID 없음·post/matrix residual PASS를 확인했다. 자식 수는 MoveIt/pick12개, 일반 조작/인계11개, 비전 없는 navigation10개로 실행 구성에 따라 다르다. 힘 cap 비율은 모두1.0 이하이다. 선언한 각 시나리오1회이며 반복 강건성 인수가 아니다.

대표 측정:

- 정상 pick: 최소100.399579mm/최대103.089093mm 상승, HOLD2.18sim초, 상대 변화0.027299mm, 양 finger 접촉100%, 자식12개 정상 회수. 원본 RGB-D로 저장 중심을 재계산했다.
- 파지 후 취소: 실제 CANCELED 뒤2.22sim초 유지, 낙하0mm, 상대 변화0.034446mm, 양 finger 접촉100%, 자식12개 정상 회수. 정상 lift 완료와 별도 시험이다.
- MoveIt: joint/pose/Cartesian 실제 위치 오차4.389893/3.981888/2.989201mm, joint/pose 회전 오차10.400892/11.611407mrad. fraction1, 불가·충돌 거절과 실제 취소를 확인했다.
- 16개 engine 실행 구간 합계1073.25wall초. 부품 시험199 PASS66.17초, build6개18.7초, 오프라인 판정 시험12 PASS0.23초는 별도 작업 시간이다. 전체 대화·설치 준비·판독 시간을 engine 시간과 혼합하지 않는다.

## 과도한 조건의 제거와 판정 보완

**2ms 경로점 간격 조건 제거.** 물리 주기와 연속 곡선의 매듭 간격을 혼동한 조건이었다. 기존 raw52.200599초 경로의 마지막0.598696ms 때문에 전구간을 늘려120sim초를 넘겼다. v13은 정규화 시간에서 quintic을 구성하고 전체 곡선의 관절·속도·가속도 한계를 검사한다. 모든 경로점과2ms 물리 샘플링을 유지한다. 실제 가속도를 만족하는 배율2에서104.401197초로 유효하며 다른98.639757초 후보가 더 빨라 그것을 선택한다. 제한120초·힘·질량·마찰·관측 수명을 늘리지 않았다.

저장 원본35개 파일의74개 계획 출력이 오프라인 timing 검사를 통과했다. 과거 Cartesian 원본이 저장되지 않은 구간과 임의의 새 경로를 모두 검증했다는 뜻은 아니다. 새 Cartesian 원본 저장을 추가했고, 실제 v13 held_cancel과 pick 모두 완료했다. 독립 SciPy Hermite 보간과 위치/도함수·2ms 샘플 변화량을 대조했으며 실제 과속·가속도 초과·시간 비증가는 계속 거절한다.

**raw_loss 판정의 의미 수정.** 기존13.5 판정기는 모든 시나리오에서 엔진 fault가 비어야 한다고 요구했다. 이번 의도한 입력 손실에서는 마지막 raw 최초 receipt 뒤309.224ms에 gateway timeout,315.683ms에 첫 engine FAULT/zero를 기록했다. 이후 zero latch·재활성화 없음, 실제 운동 후 정지 수치·정상 회수는 통과했다. 두 감시기의 같은300ms 수명과 다른 검사 주기(physics2ms/gateway20ms) 때문에 상위 fault 때까지 하위가 항상 무fault라고 요구할 수 없다. 정확히 어떤 platform freshness 항목이 먼저 만료했는지는 당시 기록하지 않아 확정하지 않는다.

원래 `navigation_verification.json`의 FAIL과 원본 matrix 실패 행을 유지했다. 별도 `injected_loss_review_v1.json`은 **raw_loss의 owned publisher pause·해당 timeout·기존350ms 예산·주입 전 실제 운동/무fault·이후 zero/FAULT 유지·기존 나머지 검사 전부 PASS·잔여 없음**에만 적용한다. 일반 실행이나 다른 fault, 주입 전 오류, 정지 후 움직임, 중복 소유자, 불완전 증거는 허용하지 않는다. 실제 fixture와11개 반례 시험으로 검증했다. 이 보완을 이유로 통과한14개 engine을 다시 돌리거나 runtime 버전을 올리지 않았다. 미실행 상태였던 마지막 nav_vision만 이어서 검증했다.

상세 기준과 학생용 축소 절차는 [게이트 검토](SECTION_13_6_REUSE_GATE_REVIEW_KO.md), 명령은 [실습 가이드](LAB_13_6_REUSE_GUIDE_KO.md)를 따른다. 핵심 재현은 pick→verify_pick 한 번이며, 분리 시험·전체 unit·실패 주입·13.5 회귀는 선택 학습 또는 개발 인수다.

## 이전 실패 보존과 구현 범위

v10 첫 배치는 MoveIt PASS 후 pick의 시작 future-clock 오류로 중단했다. 별도 추적 pick PASS를 그 실패의 대체로 사용하지 않는다. v11은 pending 동안 admission을 닫고 원본300ms 안에서 native clock 증거를 기다리도록 수정했다. v10 실패는 trace가 없어 같은 내부 원인으로 소급 확정하지 않는다. v11 두 사례 PASS 뒤 held_cancel pre-grasp 시간 초과, v12의 held_cancel Cartesian 시간 초과도 보존했다. v13의 실제 통과가 이들을 삭제하지 않는다.

시작 callback 순서·renderer typed 준비/실패·OS 자원 회수·중복 NTFS 모듈 검색 경로 비용은 [동기화 조사](SECTION_13_6_REUSE_STARTUP_SYNC_REVIEW_KO.md), [준비 결함 수정](SECTION_13_6_REUSE_PREPARATION_FIX_KO.md), [import 조사](SECTION_13_6_REUSE_IMPORT_STARTUP_REVIEW_KO.md)에 기록했다. 시작 제한15초와 원본 수명300ms/과거TF100ms를 유지했다. [v1~v4 감사](SECTION_13_6_REUSE_V1_V4_REVIEW_KO.md)도 보존한다.

원고의 MoveItPy 개념 API 대신 설치 API의 GetMotionPlan/GetCartesianPath와 실제 native FollowJointTrajectory 어댑터를 사용한다. TRAC-IK·OMPL·단일 planning scene·실제 base TF/joint_states·ground/받침/대상을 연결한다. 물리 대상은 반경2cm·높이8cm·20g·마찰0.8 동적 원통, 그리퍼 cap0.5N이다. 실제 양 finger 접촉 뒤 scene geometry만 attach하며 물리 weld/teleport는 없다. 원본 Kp/Kd와 힘 cap을 유지한 명시적 model-bias v2를 사용한다.

한계: 알려진 upright 원통·실제320×240 RGB-D 표면 fit·ground-truth localization의 교육용 시뮬레이션이다. 일반6D 인식·SLAM/AMCL·실기 하중/드라이버·별도 Crawl/Stand 모드·CoM shift/WBC·새 보행 학습·placing·Gazebo 동등 구현은 검증하지 않았다. 단일 작업자 자체 검토는 독립 검토자보다 약하다. 과거 실패·사용자 문서·외부 원본을 보존하고 main merge/PR은 하지 않는다.