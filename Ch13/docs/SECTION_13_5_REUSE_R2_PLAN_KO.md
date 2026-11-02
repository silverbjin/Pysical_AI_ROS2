> **게시 완료:** 사용자 목적지 승인 후 단계별 push와 원격 SHA 대조를 완료했다. [최신 게시 보고서](SECTION_13_5_REUSE_R2_STAGE_4_PUBLICATION_KO.md). 아래 대기 문구는 작성 당시 기록이다.

> 2026-11-02 후속 지시로 단계별 보고서·commit/push로 게시 규칙을 변경했다. [최신 완료 보고서](SECTION_13_5_REUSE_R2_STAGE_3_KO.md). 기술 작업 완료, push는 목적지 승인 대기.

# R2 최소 ROS2 연결 실행 계획

> 단일 작업자. superpowers:executing-plans 적용.

**Goal:** 검증한 corrected A profile을 ROS2 Jazzy에서 단일 속도 소유자·실제 상태·시각/TF와 연결한다.
**Architecture:** 원본 PlayMujoco.run/LocomotionPolicyWrapper를 그대로 실행 경계로 사용하고 검증한3개 보완을 적용한다. ROS2 껍데기만 추가한다. upstream 분리형ROS2 파일은 timestamp 미발행·import시 우선순위 변경·별도 시뮬레이터/팔 hold 동작 차이 때문에 이 단계의 기본 실행기로 쓰지 않는다.
**Tech Stack:** 고정A commit/MuJoCo3.13/torch2.9cpu/Jazzy, 표준ROS메시지, 독립ament_python 패키지.
**Spec:** HANDOFF_SECTION_13_5_REUSE_REVISION_2026_11_02_KO.md R2 + SECTION_13_5_REUSE_EDUCATIONAL_GATES_KO.md + 사용자 R2 시작 지시.

## 고정 계약

- namespace /ch13/reuse; localhost-only/domain135(프로세스별), 기존환경변경 없음.
- raw TwistStamped→command_gateway→safe TwistStamped→platform. Nav2/smoother는R3; R2는직접시험publisher.
- cmd frame reuse/nav_base, vx m/s±0.20·wz rad/s±0.20, vy는아직미검증이므로0만. 나머지축0만. 정상 가속도0.30m/s²/0.50rad/s². 고장zero는즉시 출력.
- raw/state/safe/clock wall expiry0.30s, source age0.30sim초. DDS토픽 간 전달순서 차이에 미래여유0.025sim초만 허용. 그 이상 미래 RED.
- 최초receipt/GID/stamp 보존; 중복동일stamp로age갱신금지; publisher추가/교체·시계역행·pause/만료·비유한값 latch. reset 후 새0명령/관측과 arm 서비스 필요. 자동재개금지.
- 실제 engine stamp/pose/q/qd 발행. Odometry raw child reuse/base는3D실측. nav odometry/TF는 명시된 xy/yaw projection; nav_base→base에서원본z/roll/pitch를 보존. engine body TF는실측kinematics. 센서/map/Nav2 없음.
- 팔은원본home target hold±0.10rad screening. 수납envelope/IK최종승인아님. 정책은다리12축만소유. 작은 joint1 hold offset≤0.05rad를 정지상태에서만 시험.
- edu_stop_v2그대로사용. 최초 live fault-stop 검증은zero결정≤0.35wall후(0.30만료+20ms제어tick/전달여유), 실제정착최대5sim초/8wall초로사전고정. 속도/힘 cap, 고장latch, 정상종료는유지.

## Task 1: 계약과순수안전코어

Files: ch13_navigation_reuse/{safety.py,state_adapter.py}, config/platform.yaml, test/test_safety.py,test_state.py.
- [x] RED: 최초receipt·중복stamp·만료·미래·비유한값·중복/교체GID·clock rollback/pause·명시재무장·지원축/제한·실측quaternion/frame변환.
- [x] GREEN: 독립코어/실제단위·관절순서설정구현. python unittest로해당계약통과.

## Task 2: ROS2경계와설치

Files: package.xml/setup.py/resource, command_gateway.py, platform_adapter.py, launch/platform.launch.py.
ConsumesTask1. 실제DDScallback의MessageInfo GID와steady timer로코어연결. platform은원본루프observer만추가하고`/clock`, raw/nav odom, joint states, TF발행. 소유engine lock과RX join.
- [x] RED→GREEN: 실제DDS raw→safe 경로의arm/명령/만료·중복publisher·시각조건.
- [x] 새패키지만colcon build/install; 외부checkout/underlay원본수정금지.

## Task 3: 짧은실제연결과기록

Files: scripts/reuse_13_5/run_r2_probe.py, docs/SECTION_13_5_REUSE_R2_REPORT_KO.md, 새UUID evidence.
- [x] 설치본/정책hash 감사후엔진단독실행. 명시arm→짧은전진→zero→실제정착→팔독립hold→입력손실latch→정상회수/잔여검사.
- [x] clock pause/rollback·publisher교체는작은DDS검사로먼저판별. 엔진중build/test/분석병행금지.
- [x] 실측수명/미검증을분리해보고. R3로자동확장하지않음. commit/push는전체계획R5규칙유지.

## 검토초점

clock토픽과state도착순서·freshness위장·body진동을평면TF로삭제하는오인·원본루프실행수명·안전zero와정책종료혼동을확인한다. 사용자지정단일작업자이므로자체검토.
