# R2 진입·최소 ROS2 연결 보고

2026-11-02 한국 시각. 단일 작업자, `superpowers:executing-plans`. 개정 gate `section_13_5_edu_stop_v2`와 검증된 corrected A profile을 적용했다.

**R2에 진입하여 최소 ROS2 연결과 첫 실제 엔진 검증을 통과했다. R2 전체 fault matrix는 아직 완료하지 않았다. R3/Nav2는 미착수다.**

## 구현

- `ch13_navigation_reuse`: 순수 안전 코어, 실제 상태/평면 frame 변환, command gateway, 원본 실행 루프를 감싼 platform adapter, launch/config.
- `ch13_reuse_wire`: 설치된 Jazzy rclpy에 없는 actual sample GID를 rclcpp MessageInfo에서 수집한다. 원래 ROS CDR·GID·Ch13 최초 callback의 CLOCK_MONOTONIC receipt·RMW source timestamp를 유계 패킷으로 보존한다. 물리/정책 코드는 없다.
- 원본 `PlayMujoco.run`과 `LocomotionPolicyWrapper`, 검증한3개 보완(팔 목표 복사/native arm PD/보행 모드 게인 유지)을 재사용했다. 모델·가중치·mass·접촉·physics2ms를 수정하지 않았다.

upstream 분리형 ROS2 실행 파일은 상태 timestamp를 채우지 않고 import 시 renice/autogroup 쓰기를 시도하므로 기본 실행기로 쓰지 않았다. 이미 재현한 단일 원본 루프에 필요한 ROS 입출력만 추가했다. 전체 물리 bridge나 보행기를 새로 만들지 않았다.

실제 설치본은 `/home/jinho/ch13_reuse_r2_build/install`, 추론 Python은 기존 전용 venv다. 새 두 패키지만 빌드했다. 외부 checkout/ROS underlay/기존 Ch13 패키지/Ch01–12는 변경하거나 빌드하지 않았다.

## 고정 경계

| 항목 | R2 값/의미 |
|---|---|
| 명령 | `/ch13/reuse/cmd_vel_raw` TwistStamped → gateway → `/ch13/reuse/cmd_vel_safe` → platform |
| 단위/축 | frame `reuse/nav_base`, vx m/s±0.20·wz rad/s±0.20. vy와 나머지축은 아직 미검증이므로0만 허용 |
| 정상 가속도 | 각 wall초마다 속도명령 변화≤0.30m/s·yaw속도명령 변화≤0.50rad/s. platform에서도 같은 상한을 보수적으로 적용 |
| 만료 | wall0.30초/source0.30sim초. 20ms 제어tick/전달여유를 포함한 관측 가능한zero결정 상한0.35wall초를 실행 전 동결 |
| future slack | 별도 DDS 토픽 도착순서 차이0.025sim초만 허용. 초과는 latch |
| 활성화 | platform/gateway 각각 명시 arm. FAULT 뒤에는 reset→새 관측/0명령→arm 필요. 자동 재개 없음 |
| 소유권 | 실제 GID pin, graph의중복publisher 검사. 중복stamp는최초receipt를갱신하지않음 |
| 상태 | engine의 실제 qpos/qvel와원본step 종료시각. 목표를odometry로발행하거나root를이동시키지않음 |
| localization | engine ground truth 교육 profile. AMCL/SLAM 실증 아님 |
| 팔 | 원본home hold, 작은joint1 offset±0.05rad만 정지상태에서 허용. 정책 다리12축과 팔 PD 소유권 분리 |

현재 slew limiter는 steady-wall 시간 기준이며 실제 몸체 가속도나 sim초 기준 가속도 검증을 뜻하지 않는다. R2 완료 전 운전 명세의 시간축을 정리하고 R3 smoother와 맞춘다.

정착/팔 변경/종료 서비스는 최신 actual capture0.30wall초 이내만 허용한다. source pause 이후에는 정착 창을 다시 쌓는다. 정지 사전 승인은 보수적 순간속도·실제 변위/자세 검사이고, 최종 보존 원본은 개정 gate의 시간 가중 RMS로 독립 확인한다. 검증된 전체 수납 envelope나 READY_FOR_MANIPULATION을 의미하지 않는다.

## 실제 연결 결과

대표 성공 UUID: `ad20c823-7bf3-4ea1-87da-cb5b96cd929e`.

| 검사 | 실제 결과 |
|---|---:|
| 실제 ROS2 속도 경로의 첫 전진 | 0.433457m |
| 계획0명령→실측정착확인 | 1.947500wall초(1초정착대기 포함) |
| 팔 독립성 | joint1 목표0.02rad를 별도로 주고 실제0.011296rad 관측,0목표로원복 확인. 정확한 위치추종/MoveIt 성공 주장은 아님 |
| raw 입력 손실→zero 결정 | 마지막 최초receipt부터0.314408wall초, 사전0.35초 이내 |
| 입력 복귀 | gateway와 platform FAULT 유지, 자동 재개 없음 |
| 실제 물리 | 10.060sim초/24.678wall초·5,030physics step, 실제힘/원래cap 최대비1.0 |
| 실제 ROS 상태 | 503개 engine 상태표본 수신 |
| 회수 | RX join·upstream 생성 thread join 성공, ingress/gateway/platform exit0·부모wait 완료 |

[실행 요약](../evidence/section_13_5_reuse/ad20c823-7bf3-4ea1-87da-cb5b96cd929e/probe_summary.json), [엔진 요약](../evidence/section_13_5_reuse/ad20c823-7bf3-4ea1-87da-cb5b96cd929e/engine.json), [설치 감사](../evidence/section_13_5_reuse/ad20c823-7bf3-4ea1-87da-cb5b96cd929e/install_audit.json), [독립 정착 판별](../evidence/section_13_5_reuse/ad20c823-7bf3-4ea1-87da-cb5b96cd929e/edu_stop_verification.json).

최종 보존 정지 창은1.339801wall초/0.500sim초·251고유표본이었다. 평면변위0.007508m·yaw변화0.005725rad·평면속도RMS0.017637m/s·yaw속도RMS0.034959rad/s로 개정조건을통과했다.

개정 gate의 `1wall초`와 `0.5sim초`는 모두 최소 지속시간이다. simulation이 느리면 둘을 만족하도록 wall 대기를 늘린다. 실행 속도 자체를 정착 실패로 오인하지 않는다. 숫자·시나리오는 실행 전에 고정했으며, 원본/중간 FAIL을 PASS로 바꾸지 않았다.

## TF와 시각

`/engine_state`는 실제3D몸체 상태다. `/odometry`는 실제xy/yaw에서 도출한 명시적평면 profile이다. `reuse/odom→reuse/nav_base→reuse/base`의 두변환을 합치면 원본3D몸체pose가 복원된다. `nav_base→base`에 z/roll/pitch를 남겨 body진동을 숨기지 않는다. 팔/다리 body chain은 실제post-step kinematics로발행한다. camera/map/scan은이번에생성하지않았다.

실제 DDS TF 부품 검사에서 공통2초 source stamp·child중복없음·전체rootpose합성·팔체인연결을 확인했다. 이 검사는 고정 engine snapshot의 ROS 출력 검사이며, 첫 실제 이동 시험과 구분한다.

## 검증과 발견한 경계 문제

- 안전/상태/서비스/DDS/종료27개 검사와 TF 부품1개가 통과했다(총28, 기존R1의9개와합산하지않음).
- 최초receipt·source만료·future·비유한값·unsupported axis·frame·중복/교체GID·clockrollback/pause·명시재무장을 순수코어에서 검사했다.
- 실제 DDS에서는 명시arm, raw손실, 두번째rawpublisher, clockrollback을 확인했다.
- 시작clock 전 stamp0 출력은내보내지않도록RED→GREEN. 오래된정착캐시의팔/종료승인도RED→GREEN. 정상SIGTERM의ExternalShutdownException을처리해exit1→0을확인했다.
- Jazzy callback에는GID가없고RMW_GID_STORAGE_SIZE는16bytes임을실제API/설치헤더에서확인했다. 패킷혼합depth1이clock을덮어쓰는문제는유계depth16으로수정했다. 만료값을늘려감추지않았다.
- Python/data 설치byte와보완코드hash, 원본94개hash를대조했다. C++ ELF는install시RPATH가달라지므로전체hash를각각보존하고`.text`/`.rodata`동일성을검증했다.
- 실제엔진실행은모든빌드/검사/설치감사뒤1회만수행했고, 실행중빌드나분석을병행하지않았다. 전체실행공수는별도정확히계측하지않아보고하지않는다.

## 남은 R2와 다음 경계

이번 지시의 R2 진입·최소 연결은 달성했다. 다음은 실제 DDS의publisher교체·clockpause·state관측손실/future packet 사례를 확장하고, 설치launch경로 및graph정리의추가검증을마친뒤R2전체완료를판정한다. 해당조건의순수코어성공을실제DDS/엔진전수성공으로전이하지않는다. 원본home초기조건과제한된팔hold를사용했으며down→stand·전체수납envelope·센서/카메라/IK도아직최종검증되지않았다.

R3의Nav2/smoother/map/scan과R4비전접근은미착수다. 현재입력토픽은R2수동시험용raw경로이며, R3에서는Nav2 raw→smoother→gateway로명시연결하고동일우회/소유권시험을한다. R2의단일`/tf`publisher검사는R3에서합법적다중broadcaster를허용하되edge별단일소유권으로확장해야한다.

사용자지정단일작업자로자체검토했다. main/PR/commit/push는수행하지않았다. 기존Task8실패와사용자파일은그대로보존했다. [실행 가이드](LAB_13_5_REUSE_R2_GUIDE_KO.md)의현재PC절차로재현할수있다.
