# 13.6 정밀 매니퓰레이션 설계안

2026-11-03 KST. **제안 문서 / 사용자 설계 승인 대기. 구현 결과가 아니다.** 단일 작업자 자체 검토. 근거는 [M0 조사](SECTION_13_6_REUSE_M0_REPORT_KO.md)와 사용자가 제공한 13.6.1~7 원고다.

## 목적과 범위

13.5 접근을 수행한 바로 그 살아 있는 Go2+Piper engine에서 MoveIt 2로 실제 팔을 움직이고 가벼운 동적 물체를 물리적으로 집어 10cm 들어 올리는 교육 실습을 만든다. 관측→관측 시각 TF→계획 장면→계획→실제 실행→실측 판정을 연결한다. 장애물/도달 불가/취소/입력 손실/중복 소유자 거절까지 가이드에 포함한다.

기존 정책·모터 힘 cap·physics 2ms·50simHz policy와 native PD를 유지한다. 새 학습, 새 보행기, torso teleport/fix, 정책 중단, WBC, 하드웨어 드라이버, Gazebo 동등성, SLAM/AMCL 실증, 일반 6D 인식은 범위 밖이다. 물리 실패를 weld/가상 attach/목표 joint_states로 성공 처리하지 않는다. 기존 13.5 결과는 보존한다.

## 접근 방식 비교

| 방식 | 이 프로젝트에서의 영향 | 판단 |
|---|---|---|
| 표준 action 어댑터 + 기존 native PD | controller wire·검증·보간만 추가. 보행 loop/팔 힘 법칙 재사용 | **권고안, 아직 사용자 선택 전** |
| ros2_control hardware interface로 통합 | 생태계 표준 controller 재사용 가능. 기존 loop와 수명·쓰기 소유권 재구성 필요 | 이번 최소 재사용 목표에 비해 변경 큼 |

직접 위치 IK와 가상 부착은 MoveIt 충돌 계획·물리 파지라는 필수 과제를 충족하지 않으므로 대안으로 채택하지 않는다. 위 권고안을 기준으로 아래 설계를 구체화했으며 승인 시 하나의 실행 경로로 고정한다.

## 패키지와 변경 경계

- `ch13_manipulation_reuse`: 상위 mission, live lease, trajectory/gripper action 경계, 상태/실행/비전 과제.
- `ch13_piper_moveit_config`: 통합 모델과 일치하는 URDF/SRDF, TRAC-IK, OMPL RRTConnect, controller/limit/launch 구성. 모델 생성 결과와 근거 hash를 기록하고 외부 mesh는 설치 때 검증해 참조.
- `Ch13/scripts/reuse_13_6`: 별도 build·audit·실행·회수·인수. `CH13_REUSE_BUILD`를 13.6 별도 경로로 요구하고 R5 build 덮어쓰기 거절.
- 13.5 platform의 작은 opt-in extension hook과 scene factory만 공유 수정. 기본 flag가 없으면 기존 행동 유지. 기존 script/bridge/보행 loop 전체 복제 금지.
- 새 인터페이스 패키지는 초기에는 만들지 않는다. actuator action은 표준 메시지, live lease/상태는 엄격 schema의 session 상태로 시작한다. ROS wire에 필요한 출처를 보존할 수 없을 경우 이유를 기록하고 custom msg 한 가지를 추가한다.

## 수명과 작업 권한

상태는 NAVIGATING→SETTLING→MANIPULATION_READY→EXECUTING→POST_SETTLE→COMPLETE, 고장은 FAULT_HOLD, 취소는 CANCEL_HOLD를 거친다. 과거 JSON/READY string은 권한이 아니다.

상위 mission이 engine session UUID, 소유 Nav2 goal UUID, 원본 관측 식별자와 capture/first-receipt 시각, terminal SUCCEEDED, 실제 목표 오차/정착, gate/platform 무고장 zero를 묶어 live lease를 만든다. 13.5 probe는 이 전환 지점을 opt-in callback으로 열고, 기본 경로에서는 기존 즉시 회수·shutdown을 유지한다. 인계 중 Nav2 idle와 fresh zero 발행, RX/physics/renderer를 유지한다. 새 goal·취소·관측 만료·상태 소유자 변경·clock fault는 lease를 회수하고 자동 재활성화하지 않는다.

이동 admission에는 기존 팔 포함 정착 조건을 요구한다. 실행 중에는 arm 정지 조건 대신 base 지지/변위·tilt/관절 한계/힘 cap/관측 수명/실제 tracking을 검사한다. 실행 후에는 새 목표를 기준으로 팔까지 정착한 뒤 종료한다. 조작 중 정상 팔 이동을 기존 stationary_ready=false만으로 즉시 고장 처리하지 않는다. base 지지 기준은 기존 edu_stop_v2의 base 조건을 유지하고, 조작 시작 anchor에 대한 drift도 제한한다. 구체적 tracking/부품 한계는 M2 계약 파일에서 실험 전에 동결한다.

취소 ACK는 실제 action terminal이나 정지가 아니다. 현재 유효 궤적에서 제한된 감속을 생성해 검증 가능한 hold로 전환한다. torque0/무조건 수납하지 않는다. 물체를 잡은 상태의 fault에서는 gripper를 임의 개방하지 않는다. base 불안정/관절 비유한 등 hold 자체가 불가능하면 물리 실패로 기록하고 검증된 수명 회수 경로를 따른다. 정상 정착 불가 종료를 정상 정지 PASS로 세지 않는다. 최종 worker/renderer/RX join·engine/부모 exit·잔여 PID/lock 확인을 포함한다.

## 제어 인터페이스와 단일 적용자

권고 namespace는 기존 `/ch13/reuse` 아래 `manipulation`이다. 이름은 신규이며 현재 존재하지 않는다.

| 인터페이스 | 계약 |
|---|---|
| `manipulation/arm_controller/follow_joint_trajectory` | FollowJointTrajectory, joint1~6 전체 순서 정규화, 유한 position/velocity/acceleration, 단조 time_from_start, 한계·시간·초기 연속성 검증 |
| `manipulation/gripper_controller/gripper_cmd` | GripperCommand, joint7 m 위치와 ≤0.5N effort cap; joint8=-joint7 관측만 사용 |
| `manipulation/status` | session/goal/lease/phase/원본 시각/fault/실측 tracking/hold 상태 |

action server가 admission과 궤적 검증을 하고, engine 내 단일 command slot에서 sim-time 보간한 6축 목표만 native PD 적용 지점으로 전달한다. joint1 시험 parameter와 새 slot은 상호 배타적이다. gripper는 원본 desired_joint_pos_gripper를 통해 기존 PD가 적용한다. 실제 q/qd와 actuator_force로 feedback/도달을 판단하고 명령값을 관측으로 발행하지 않는다.

새 trajectory는 5Hz 목표 갱신 topic으로 스트리밍하지 않고 완전한 시간 궤적 하나를 검증·수락한다. physics 보간/관측/mission heartbeat 주기를 분리한다. 기존 5Hz 시험 parameter 계약은 유지한다. 엔진 로컬 watchdog이 mission/lease 소실을 감지하며 action server 생존을 무기한 명령 권한으로 사용하지 않는다. 취소·중복 goal·소유자 교체·deadline·실행 종료 tolerance의 정확한 wire와 판정은 M2에서 테스트로 고정한다. 보안 인증된 DDS client identity를 표준 action이 자동 제공한다고 주장하지 않는다. 실제 GID 검증 가능한 heartbeat/native ingress와 배타 goal 소유권을 조합하고 중복 엔드포인트를 거절한다.

## planning model과 TF

통합 go2_piper_l.xml의 body pose·joint 축·offset·한계·collision 형상을 기준으로 URDF를 만든다. 독립 팔 모델의 unlimited 설정이나 과거 13.3 로봇 설정을 가져오지 않는다. 전체 다리 상태와 trunk/센서 collision을 포함하되 planning group은 arm 6축, gripper는 mimic 관계를 반영한다. 원본 capsule을 URDF에서 근사하면 보수적인 cylinder+sphere 합집합으로 표현하고 근사 오차를 기록한다. visual mesh는 외부 검증 자산에서 참조한다.

frame 이름은 실제 `reuse/base`, `reuse/link1`~8 체인과 맞춘다. 실제 base pose를 world virtual joint/TF로 읽고 engine만 robot TF/joint_states를 발행한다. robot_state_publisher나 fake joint publisher를 중복 실행하지 않는다. 파지 TCP는 양 finger 접촉면 사이로 정의해 link6에 고정한 뒤 MuJoCo↔MoveIt FK를 다양한 관절 자세에서 비교한다. 표면점용 link7/8 origin 중점을 그대로 TCP로 쓰지 않는다.

타겟은 원본 capture stamp에서 camera→world와 arm frame 변환을 계산한다. ‘최신 TF’ 또는 stamp=now 치환 금지. 원본 age 300ms·과거 TF 100ms·first receipt/GID·clock 역행 계약을 유지한다. 계획 후 실행 전 새 실제 상태와 관측에 대해 stale plan 검증을 한다. 실행 중 base/TCP 또는 대상 변화가 허용치를 넘으면 hold→새 관측→재계획하며 움직이는 base를 고정 world TF로 덮지 않는다.

계획 장면에는 바닥, 받침, 벽/장애물, 인식 대상 cylinder와 로봇 자체 형상을 넣는다. 손가락-대상 ACM만 파지 단계에 한정해서 허용하고 나머지 자기/몸체/팔/바닥/받침 충돌은 유지한다. 전역 padding 0이나 전체 finger 충돌 해제를 기본 해법으로 쓰지 않는다. engine 물리 접촉 검사도 같은 지정 finger-target pair만 예외로 둔다. target-support 접촉은 정상 환경 접촉으로 구분한다.

## 실제 MoveIt 실행

설치된 MoveItPy 2.12.4의 `PlanningComponent.plan()` 결과 trajectory를 `MoveItPy.execute()`로 보낸다. pre-grasp는 TRAC-IK+OMPL RRTConnect pose 계획이다. gripper open/close는 표준 gripper action으로 실행한다.

MoveItPy PlanningComponent에는 원고의 compute_cartesian_path/execute가 없다. 작은 Python wrapper가 같은 robot model/scene을 가진 move_group의 GetCartesianPath 서비스로 직선 진입/lift를 요청하고 실행은 동일 trajectory controller로 보낸다. scene revision 동기화·현재 state·충돌 검사·jump 검사·시간 파라미터화를 검증한다. scene monitor를 둘 운용하면 revision/ACM/대상 상태 일치를 먼저 검사하고 어긋나면 실행 거절한다.

부분 경로 fraction>0.9를 그대로 실행하지 않는다. 전체 경로 fraction≈1과 최종 pose tolerance를 모두 요구한다. 속도/가속도 scale은 ≤0.1. Cartesian max_step 초기안 0.005m, joint jump는 비활성화하지 않으며 M3에서 수치 동결한다. 시간 없는 궤적은 실행 거절하고 retime된 궤적의 실제 제한을 다시 확인한다.

## 물리 picking profile 제안

기존 vision box는 정적이므로 별도 opt-in `pick` 장면에서만 동적 freejoint cylinder+받침을 만든다. 초기 제안은 반지름0.02m/높이0.08m/질량0.02kg, sliding friction 0.8이다. 새 물체의 명시적 교육 profile이며 기존 로봇/팔 cap·질량·마찰은 바꾸지 않는다. 물체·받침 위치는 FK/가시성 조사로 결정해 첫 동역학 시험 전에 lock에 기록한다. 이 수치로 파지 가능함을 아직 주장하지 않는다.

비전은 upright cylinder라는 공개 과제 사전정보와 알려진 크기를 사용한다. 붉은 mask의 실제 RGB-D 점군에 cylinder 표면을 맞춰 중심/축과 residual을 추정한다. 회전 대칭 yaw는 감지된 6D pose라고 부르지 않고, base 방향/충돌 검사를 이용해 파지 방향을 선택한다. 원본 depth/과거 TF·fit 오차를 증거에 남긴다. 물체 world qpos는 독립 평가 도구만 읽고 제어 목표/비전 입력에 사용하지 않는다. 가림·점 부족·fit 실패는 실패로 처리한다.

순서는 OPEN→PRE_GRASP(0.10~0.15m 앞)→CARTESIAN_APPROACH→CLOSE→CONTACT_CHECK→CARTESIAN_LIFT(0.10m)→HOLD→POST_SETTLE다. finger 접촉은 양쪽 모두 실제 측정하고, collision scene attach는 물리 파지를 확인한 뒤 계획상 표현만 바꾼다. 물리 weld/teleport는 사용하지 않는다.

성공 지표 초기안: 물체 중심 실제 상승 ≥0.09m, 2sim초 유지, 물체-TCP 상대위치 변화 ≤0.02m, 양 finger 접촉 증거, 낙하/받침 잔류/로봇 금지 접촉 없음. 단순 gripper action SUCCEEDED 또는 scene attach는 성공 지표가 아니다. 수치는 인수 전 freeze하고 미달 실패를 보존한다. 동일 실패 계열이 두 번의 최소 수정에도 남으면 구조/가시성/모델 적합성을 재검토하고 cap·마찰·질량 탐색을 무한 반복하지 않는다.

## 단계별 검증과 완료 조건

| 단계 | 구현과 최소 검증 | 완료 증거 |
|---|---|---|
| M1 | live session lease, 정착 전/과거 session/새 goal/만료/취소 거절, 같은 engine 인계와 회수 | 살아 있는 engine 상태·lease events·정상 join |
| M2 | 실제 작은 6축 궤적, gripper 개폐/연동, 한계·소유자·입력 손실·취소/hold | 실제 q/qd/force·terminal·정착. 파지 결과와 분리 |
| M3 | URDF FK/TCP/축/한계·collision 대조, MoveIt pose/Cartesian 계획과 실행 | 도달 가능/불가·충돌 거절·취소·실측 도달 |
| M4 | 동적 cylinder, RGB-D fit, 실제 접근/파지/lift | 접촉·물체 상승/유지·관측 출처. 실패 포함 |
| M5 | source/install/model/policy/수치 freeze 후 필수 각1회 인수 | 정상·불가/충돌·취소·손실·중복·종료·공유 변경 영향의13.5 접근/취소/정지 회귀 |

엔진은 순차 실행하며 실행 중 build/pytest/대량 분석을 병행하지 않는다. 단위 시험으로 입력/수명 계약을 먼저 확인한 뒤 실제 engine으로 구분 검증한다. 문서 변경만 있는 M0에서는 기존 전체 동역학 matrix를 재실행하지 않는다. source/install audit는 새13.6 freeze로 수행하며 변경본을 기존114파일과 일치한다고 주장하지 않는다.

각 단계 보고서, UUID evidence/manifest와 실습 가이드를 남긴다. 가이드는 원고 소절별 설명·명령·기대 결과·실패/종료 판독을 제공한다. 선택 파일만 commit하고 승인된 저장소/13.6 branch에 non-force push 후 실제 SHA를 대조한다. main 병합/PR은 수행하지 않는다.

## 설계 자체 검토와 승인 경계

단일 작업자 지시에 따라 별도 agent를 사용하지 않았다. 원고와 인계의 READY 수명, joint1 덮어쓰기, gripper 연동, 정적 target, 충돌 차단, 실제 API 차이를 대조했다. 아직 미결인 수치는 TCP/FK 실측, 궤적 tracking/감속·watchdog 주기, 물체 pose/fit 오차·접촉 가능성이다. 이는 부품 시험 전에 계약으로 고정할 구현 판단이며 파지 성공을 미리 보장하지 않는다.

사용자 확인 대상은 **표준 action 어댑터+native PD 경로와, 가벼운 upright cylinder를 실제 파지·10cm lift하는 위 교육 profile을 기준으로 구현하는 설계**다. 승인 후 상세 실행 계획을 작성하고 요청한 superpowers:executing-plans로 M1~M5를 진행한다. 신규 설치가 필요해지면 실제 패키지와 영향을 먼저 밝힌다.
