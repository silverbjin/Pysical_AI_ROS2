# 13.8 진행 사항·문제 해결·반복 문제 종합 보고서

작성일: 2026-11-05 KST. 단일 작업자. 구현·실험 내용은 로컬 commit `5f2b877d`까지, 실행 소스는 v24까지를 기준으로 한다. 이번 문서화 요청에서는 기존 증거를 다시 읽어 정리했으며 engine이나 장시간 시험을 새로 실행하지 않았다.

**현재 상태는 개발 진행 중이다.** 개발용 환경의 연속 임무는 실제 1회 성공했다. 원고 Level1 바닥 환경에서는 모든 동작과 정상 종료까지 수행했으나 원래 물리 평가 기준 때문에 최종 FAIL이다. Level2·3 및 고정 설정 10회 평가는 완료하지 않았다. 앞으로 할 일은 [별도 작업 보고서](SECTION_13_8_NEXT_TASKS_REPORT_KO.md)에 정리했다.

## 1. 기준과 개발 범위

| 항목 | 현재 기준 |
|---|---|
| 저장소 | https://github.com/silverbjin/Pysical_AI_ROS2 |
| 개발 브랜치 | `feat/ch13-section-13-8` |
| 로컬 출발점 | 13.7 BT `13ecb58d346f38778ac8015d3c2321d20c9971e0`, source freeze v7 |
| 13.8 구현 | 새 `ch13_system_validation` 패키지와 기존 실행기의 opt-in 연결 |
| 최신 실행 동결 | [v24 manifest](../dependencies/section_13_8_system_v24.json), 소스 362개·외부 자산 94개 |
| v24 manifest SHA256 | `ae5d7f4dbd5da8e6e619360071a580b3857a6669a7112f96497f17ae13cb30fa` |
| 분리 환경 | `/home/jinho/ch13_reuse_13_8_build`, 기존 venv·외부 자산·실제 공유 engine lock 재사용 |
| 원고 목표 | 같은 engine의 파지→운반 귀환→내려놓기, 공통 테이블/Level1·2·3, 계측·bag·10회 평가 |

원본 12축 보행 정책과 2ms physics/50simHz policy, native arm PD, 그리퍼 0.5N cap, 팔 속도 0.05rad/s·가속도 0.1rad/s²를 유지했다. 새로운 학습/WBC/실기 드라이버나 일반 물체 인식은 추가하지 않았다. 알려진 원통을 RGB-D로 추정하며 target freejoint는 종료 후 평가에만 쓴다.

300ms 원본 관측·heartbeat 수명, 촬영 시점 이전 TF 100ms, 단일 ROS owner, 실제 goal terminal/정착/취소·회수 경계를 유지한다. 단, 바닥 내려놓기에 **최대 20wall초의 별도 실측 정착 단계**를 추가한 변경과 13.8의 합의점 기반 검출 계약 변경은 아래에 명시한다. 모든 한계가 전혀 바뀌지 않았다고 표현하지 않는다.

## 2. 구현해 확인한 내용

| 영역 | 구현·확인 내용 | 남은 한계 |
|---|---|---|
| 연속 임무 | 같은 engine에서 파지, 접촉 유지 운반, 귀환, 실제 지지 확인, 개방, 충돌 모델 분리, 팔 후퇴, 유지, 종료 | 개발 환경 성공을 원고 환경 성공으로 옮겨 쓰지 않음 |
| 운반 권한 | 예약한 귀환 goal·새 원본 camera health·양 finger 접촉·고정 팔을 확인. 운반 중 새 팔 계획/개방 금지 | 운반용 health가 과거 3D 좌표의 수명을 연장하지 않음 |
| 정지 조작 | 귀환 terminal과 실제 정착 후 fresh 3D 재획득. LOWER→RELEASE→RETREAT 순서 | 지지 없는 개방은 계속 거부 |
| scene 관리 | MoveIt attached object의 ID-only REMOVE와 GetPlanningScene 사후 확인 | planning attach는 물리 weld가 아님 |
| 원고 Level1 | 바닥 원통 `(2,0,0.04)m`, 별도 receiving 지점·기울어진 접근·camera profile·바닥 접촉 판독 | 최종 물리 높이 기준과 3cm/120초 목표 미달 |
| 계측·bag | sim/wall 시간, 위치 오차, tilt, CPU, 실제 토픽 선별 기록·닫기·분석 | 선별 reception replay이며 전체 RGB-D/Nav2 알고리즘 재생 검증은 아님 |
| 보존·격리 | source/asset hash, native 실행 사본, UUID별 raw archive·기존 판정 보존 | 사후 보존·복원은 새로운 실제 실행 증거가 아님 |
| 정밀도 | Level1 Nav2 허용 반경을 1.5cm로 실제 전달. 짐 없는 전진 이동 1회 11.82mm | 적재 귀환 π회전과 반복 정밀도 미검증 |

현재 실제 scenario registry는 `development`, `level1_floor` 두 개다. 공통 `(3,1)` 테이블·Level2·3 구현 완료로 해석하면 안 된다.

## 3. 발생한 문제와 해결 내용

### 3.1 실행 환경·설치·시험 구성

Windows mount에서 multiprocessing child가 시험 module/namespace를 import하는 비용 때문에 시작 예산을 넘기거나 import에 실패했다. 두 번의 작은 수정 뒤에도 같은 계열이 남아 실행 경계를 검토했다. 같은 hash의 소스를 WSL native 경로로 옮겨 시험·실행하고, 외부 자산과 lock은 원래 실제 파일로 연결했다. startup 예산을 늘려 통과시키지 않았다.

native 사본에 기존 `moveit_probe.json` fixture를 빠뜨린 실패, 생성자를 건너뛴 시험 객체의 초기값 누락, 첫 합성 비전 probe의 map→odom TF 누락도 있었다. 원본 의존성/fixture 구성을 보완했고 실패 로그는 보존했다. 이들은 실제 물리 실패와 분리했다. 현재 설치 감사는 63개 Python 모듈 바이트·외부 94자산·실제 venv child의 NumPy 우선순위를 확인한다.

### 3.2 원통 가림·검출 문제

반복해서 `OBSERVATION_EXPIRED`가 나왔지만 원인은 하나가 아니었다.

| 원인 | 조치 | 확인 범위 |
|---|---|---|
| 운반 중 그리퍼가 원통을 가림 | 운반은 새 camera health+실제 접촉의 별도 권한으로 처리하고 정지 조작에는 fresh 3D 재요구 | 이후 실제 운반·PLACE 진입 확인 |
| 경계 깊이 오염·소수 표면 이상점 | PCL의 모델→합의점→재계산 패턴과 기존 robust 추정 적용 | 13.8에 한해 95% 합의율·2mm 범위·합의점 RMS1.5mm 등을 명시. 원래 전체점 RMS와 같은 의미라고 쓰지 않음 |
| 팔 끝의 붉은 보조 site가 카메라에 섞임 | MuJoCo sensor용 `sitegroup` 표시를 끔. 물리 geom/외부 XML 유지 | v16 실제 실패 자세 재현 후 v17 관측 6,134회 수락·거부0 |
| 위/아래 가림 조각 중 작은 조각이 너무 일찍 폐기됨 | 큰 anchor와 같은 엄격한 원통 모델에 맞는 작은 조각만 결합까지 보존 | 실제 245+13pixel 자료와 두 접근 궤적 234자세, 단독 작은 조각·잡음 음성 시험 |

높이 가시성 75~105%, 원본 시각/TF·GID/hash와 알려진 원통의 기하 조건은 계속 검사한다. 모든 가림/조명/일반 물체를 해결했다는 의미는 아니다. 근거는 [바닥 비전 조사](SECTION_13_8_FLOOR_VISION_DIAGNOSIS_KO.md)와 [지연 조사](SECTION_13_8_LATENCY_DIAGNOSIS_KO.md)에 있다.

### 3.3 ROS 연결·자세·충돌 모델

- **혼합 health 전달 지연:** 새 health가 만들어졌어도 navigation의 혼합 FIFO 반영이 늦었다. 13.8에 독립 latest-only 경로를 연결했다. 모든 DDS 지연을 제거한 것은 아니다.
- **귀환 quaternion 오류:** goal의 z만 설정하고 기본 w가 남아 실제 yaw가 잘못됐다. 네 성분을 명시하고 정규화해 이후 정상 귀환 방향/PLACE 진입을 확인했다.
- **MoveIt 분리 실패:** ADD와 REMOVE의 parent가 달라 바깥 서비스가 성공해도 attached 형상이 남았다. 설치 2.12.4의 ID-only REMOVE와 scene 재조회로 보완했고 이후 v15/v22에서 실제 후퇴·종료까지 확인했다.

### 3.4 owner 정지·원본 수명 만료

동기 planner 설명 초기화, 최초 action/service 타입 준비가 live lease 중 owner polling을 막는 문제를 확인했다. 대기 중 polling을 유지하고 일회 타입 지원 준비를 lease 이전으로 옮겼다. 새 client/goal의 실제 소유권은 기존 ROS owner에 둔다.

그러나 이후에도 드문 지연이 다른 경계에서 발생했다.

- v20: 기존 관측이 fault 시점에 328.839ms 나이였다. capture→render 시작 164.967ms와 render 계산 25.257ms를 분리했다. engine의 capture 관련 단계는 172.623ms였으며 당시 engine GC 사건은 없었다. pre-offer와 queue 구간을 계측했지만 작은 재현에서는 큰 지연이 재현되지 않았다.
- v21: heartbeat 발행 자체가 364.214ms 끊겼다. 직전 발행은 즉시 native 수신됐으므로 단순 DDS 전달 지연으로 해석하지 않았다.
- v22: 과거 status를 중첩 dict 대신 원문 문자열로 보관하고 같은 owner의 GC를 계측했다. 작은 사후 실험에서 RSS 약109MiB와 추적 객체 부담이 줄었다. 실제 발행 9,012회 중 250/300ms 초과 공백은0회, 최대235.980ms였다. 실제 gen2 GC는63~65ms였지만 최대 공백과 겹치지 않았다.

**v21의 364ms 공백 원인은 아직 확정되지 않았다.** v22 1회 통과만으로 반복 강건성을 주장하지 않는다. GC disable/freeze, 새 heartbeat 스레드로 stale 입력 재발행, now로 원본 시각 치환, watchdog 연장은 적용하지 않았다.

### 3.5 표시 파일 잠금의 제어 전파

v14에서 `live_status.json` 교체의 PermissionError가 BT executor로 전파돼 임무가 취소됐다. Windows의 delete-sharing 규칙에 따라 실제 reader 잠금으로 재현했다. v15는 표시 파일 쓰기를 한 개의 owned writer로 분리하고 pending 하나·오류/대체 수·실제 join을 기록했다. 3.115초 reader 잠금/기록 오류3회를 주입해도 실제 임무가 정상 종료했다. 이는 표시 I/O 오류의 격리 확인이며 제어 로그 누락을 정상으로 인정한 것이 아니다.

### 3.6 팔 시간화·지지 정착·운반 높이

| 문제 | 조치·결과 | 현재 판정 |
|---|---|---|
| LOWER action 성공 뒤 지지 접촉이 아직 없음 | 관절 tolerance와 물체 지지를 구분. 바닥에 별도 최대20wall초 정착 gate를 추가하고 저속·fresh 관측·실제 지지힘을 연속 확인 | v21/v22 실제 지지·개방까지 진행. 지지 전 개방 금지 유지 |
| 사전 파지 궤적이240wall초 초과 | 기존25% 단위 배율의 불필요한 여유를 확인. floor만 같은 feasible 구간에서12회 탐색+1% 여유, 동일 연속 궤적 검증 | 저장751점 시험과 v22 실제 사전 접근 완료. 속도/가속도/action 한계 유지 |
| 운반 높이 하강20mm 기준 초과 | v21/v22에서 반복. world 높이와 TCP 상대 이동을 별도 분석 | **미해결/원래 FAIL 유지.** v22는20.094mm 하강, 같은때 TCP18.406mm 하강, 전체 상대 이동 최대5.30mm |

별도 정착 gate 추가는 명시적 단계 예산 변경이며 300ms 원본 수명을 늘린 것이 아니다. 운반 높이의 좌표계 의미는 향후 검토 대상이고, 결과를 맞추려고 기준을 바꾸거나 과거 FAIL을 덮지 않았다.

### 3.7 도착 정밀도와 설정 우선순위

기존 Nav26cm 허용 반경은 원고3cm 목표보다 컸다. Level1에1.5cm를 전달하려던 첫 v23 dict override는 실제 서버에서 여전히6cm로 읽혔다. 소스/설치 hash는 같았으며, 실제 ROS parser에서 node-specific YAML과 wildcard override의 범위 차이를 재현했다.

Nav2 1.3.13 공식 `ParameterFile(RewrittenYaml(...))`로 원래 controller 항목의 전체 경로를 재작성했다. 파서 회귀1 FAIL/2 PASS→관련13 PASS 후, v24 실제 서버에서1.5cm를 읽고 짐 없는 전진 이동의11.82mm 정착을 확인했다. 초기 v24는 `FUTURE_SOURCE:base`로 이동 허가 전에 실패했고, 동일 제어 동결의 다음1회는 통과했다. 두 결과를 모두 보존했다. [정밀도 조사](SECTION_13_8_NAVIGATION_PRECISION_DIAGNOSIS_KO.md)에 상세 근거가 있다.

## 4. 반복적으로 발생한 문제와 현재 판단

| 반복 계열 | 반복 양상 | 해결 여부 |
|---|---|---|
| 관측 만료 | 가림, 검출 거부, 보조 site, 전달 지연, 생산 단계 정지 등 서로 다른 원인이 같은 fault로 나타남 | 개별 확인 원인은 수정. 전체 부하의 드문 deadline 초과와 반복 강건성은 미확인 |
| heartbeat 만료 | 초기 동기 준비와 v21 발행 공백 | 준비 경계 보완·기록 부담 감소·GC 계측 완료. v21 원인은 미확정 |
| 시작 순서·미래 입력 | 합성 wire 시험 및 실제 v24 cold-start에서 재발 | 합성 발행자는 DDS 매칭 후 시각 진행으로 보완. **실제 cold-start 문제는 해결 완료 아님** |
| 원통 부분 가림 | 운반/접근 중 다른 자세에서 재발 | 운반 권한 분리와 합의점·조각 결합으로 보완. 임의 환경 인식 보장 아님 |
| 목표 정밀도 미달 | v15/v17/v21/v22 귀환 오차가3cm 초과 | 설정 전달 결함 수정, unloaded 전진1회만3cm 이내. 적재 귀환은 미검증 |
| 운반 높이 기준 미달 | v21/v22 carry_height FAIL | 물체와 TCP 이동을 분리 분석. 판정 변경 없이 미완료로 유지 |
| 환경/시험 구성 오류 | mount import, 누락 fixture/TF, 생성자 초기값 등 | 각 원인별 회귀 보완. 시험 PASS와 물리 PASS는 분리 |

같은 fault 이름이 반복됐다는 사실을 숨기지 않으며, 원인이 달랐다는 이유로 전체 문제를 해결했다고 표현하지 않는다. 작은 수정 뒤 같은 계열이 남으면 구현/의존성/실행 경계를 다시 검토했다. 그 결과 native 실행 격리, 권한 경계 분리, 모델 합의점 검출, I/O 분리, 실제 설정 읽기처럼 구조를 보완한 경우가 있었다.

## 5. 대표 실제 실행과 수치

아래는 개발 버전별 선택 사례이며 고정 설정10회 실험의 표본이 아니다. sim 시간과 wall 시간을 섞어 평균내지 않았다.

| 사례 | 결과 | 주요 관측 |
|---|---|---|
| [v15 개발 fixture](../evidence/section_13_8_system/fcf0dbe0-de70-4ca1-a86e-66133a62d2f8/trial.json) | trial/물리 PASS 1회 | 같은 engine의 전체 연속 임무, 운반2.548m.210.484sim/492.119wall초,오차50.165mm,tilt0.039465rad,CPU46.978%.3cm/120초 미달 |
| [v17 Level1](../evidence/section_13_8_system/65199d33-38ee-4073-a561-bb8b22b5e79c/trial.json) | 최종 FAIL | 바닥 파지·귀환 후 지지 확인 deadline.관측6,134수락/0거부 |
| [v21 Level1](../evidence/section_13_8_system/e0b2d5b0-0678-41e0-87c6-c48793781402/trial.json) | 최종 FAIL | 지지·실제 개방/detach 후 RETREAT 중 임무 만료.190.252sim/457.378wall초,오차36.336mm.높이 기준도 FAIL |
| [v22 Level1](../evidence/section_13_8_system/ab482f62-ea28-462d-a176-235c58573edb/trial.json) | BT SUCCESS, trial FAIL | 파지→2.566m운반→내려놓기→후퇴→유지→정상종료.199.538sim/490.768wall초,오차44.449mm,tilt0.044629rad,CPU45.950%.carry_height만false |
| [v23 설정 시험](../evidence/section_13_8_system/93bcce10-caa5-4535-a31c-6c5e4a6ee0ee/actual_controller_parameters.json) | 이동 전 FAIL | 실제xy허용반경0.06.미완료 자료를 formal verifier가 읽은 KeyError도 보존 |
| [v24 첫 시작 시험](../evidence/section_13_8_system/6916dedd-6e65-403c-b8ba-180850a35b38/navigation_summary.json) | 이동 전 FAIL | FUTURE_SOURCE:base,ready_for_arm=false.자식10개 회수 |
| [v24 전진 이동](../evidence/section_13_8_system/9e86b6f2-91e6-4a89-a6d9-a28b550ae40d/precision_verification.json) | 정식 navigation/precision PASS | 실제xy0.015,목표(0.65,0,0),정착11.822mm.자식10개 회수.팔/적재/귀환π회전 없음 |

v22 실제 pick은 최소104.458mm 상승/2.2sim초 유지/양 접촉100%로 PASS다. 운반·놓기8개 판정 중7개는 true지만 높이 기준이 false이므로 전체 PASS로 바꾸지 않았다. `complete=true`는 자료 생성 완료이며 `success=true`와 다르다.

## 6. 시험·자료 보존의 현재 범위

- v22 전체 부품 시험: **357 PASS/61.30초**. [기록](../evidence/section_13_8_system/preflight_v22/components_v22.log).
- v24 변경 영향 시험: **13 PASS/5.40초,347 deselected**. [기록](../evidence/section_13_8_system/preflight_v24/navigation_params_green_v24.log). 전체360개를 다시 실행한 것은 아니며357+13을 새로운 전체370개 통과로 합산하지 않는다.
- 선택한 시험의 native 소스와 해당 실행 동결을 전수 hash 비교했다. v24는362개 일치. [확인 자료](../evidence/section_13_8_system/preflight_v24/test_source_match_v24.json).
- 사례별 source_manifest, 정확한 실행 source archive, 모델 제외 raw archive/manifest와 원래 verdict를 보존했다. raw 원본은 삭제하지 않았다. 추가 사후 분석은 기존 archive를 덮지 않고 별도 파일로 남겼다.
- 마지막 보존 작업 시점의 [잔여 확인](../evidence/section_13_8_system/preflight_v24/FINAL_AFTER_V24.json)은 소유 프로세스0/공유 lock free였다. 이는 해당 조회 시점의 증거이며 다음 실행 전 다시 확인한다.

## 7. 공식 자료를 어떻게 활용했는가

| 공식 원본/ref | 채택한 패턴 | 채택하지 않은 확대 해석 |
|---|---|---|
| [MoveIt2.12.4 scene 구현](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/planning_scene/src/planning_scene.cpp) | ID-only detach와 scene 사후 확인 | 물리 부착/해제의 성공 증거로 대체하지 않음 |
| [MuJoCo3.13.0 표시 옵션](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mjvisualize.h) | 센서 영상에서 보조 site 제외 | 외부 모델·물리 geom 변경 없음 |
| [PCL1.15.1 원통 예제](https://github.com/PointCloudLibrary/pcl/blob/pcl-1.15.1/doc/tutorials/content/sources/cylinder_segmentation/cylinder_segmentation.cpp) | 모델→합의점→재계산 | PCL 자유축 RANSAC나 예제의 임계값을 그대로 사용하지 않음 |
| [rclpy7.1.12 ActionClient](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/action/client.py) | 비동기 goal/cancel/result,타입 준비와 live 실행 분리 | 여러 thread가 같은 node를 spin하지 않음 |
| [control_msgs5.10.0 action](https://github.com/ros-controls/control_msgs/blob/5.10.0/control_msgs/action/FollowJointTrajectory.action) | 관절 terminal과 실제 지지 조건의 구분 | action 성공이 물체 지지를 뜻하지 않음 |
| [MoveIt2.12.4 TOTG](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/trajectory_processing/src/time_optimal_trajectory_generation.cpp) | 제한을 지키는 시간화와 연속 검증 | 기존 native controller를 교체하지 않음 |
| [CPython3.12.3 gc](https://github.com/python/cpython/blob/v3.12.3/Doc/library/gc.rst),[rosbag2 0.26.11 recorder](https://github.com/ros2/rosbag2/blob/0.26.11/rosbag2_transport/src/rosbag2_transport/recorder.cpp) | 원문 journal/현재 상태 분리와 process-local GC 계측 | 작은 GC 실험만으로 실제364ms 원인 확정 안 함 |
| [Nav2 1.3.13 launch](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_bringup/launch/navigation_launch.py) | RewrittenYaml로 node-specific 항목 변경 | 설정값이나 전진1회가 전체 정밀도 보장은 아님 |
| [Windows CreateFile 공유 규칙](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) | reader-lock 재현과 표시 writer 격리 | OS권한/다른 프로세스 변경 없음 |

문서/예제 존재는 이 로봇의 물리 성공 증거가 아니다. 공식 ref·채택 차이·시험 결과는 각 조사 문서에 연결했다. 이 종합 보고서에서는 새 외부 조사보다 기존 기록과 실제 저장 자료의 대조에 집중했다.

## 8. 게시 범위와 이어받기

이번 사용자 지시로 **현재 개발 브랜치의 원격 게시가 승인됐다.** 게시 전 조회에서 원격main은 `956919aef2a9732cc7be4c311fa2789f17a43945`,원격13.7/13.8 branch ref는 없었다. 따라서 로컬13.7 기반 이력과13.8 구현·증거·이 보고서를 함께 `feat/ch13-section-13-8`에 게시한다. 별도13.7 branch 생성이나 main 병합/PR 생성은 수행 대상으로 삼지 않는다.

기존 untracked 원본·과거 FAIL·외부 자산을 임의 추가/삭제하지 않는다. 보고서2개와 지정한 문서 변경만 새 commit으로 만들고, 게시 완료는 push 성공과 원격 branch HEAD=로컬 HEAD 일치로 확인한다. 원격 게시 자체를13.8의 기능 인수나 목표 성능 달성으로 해석하면 안 된다.

상세 과거 일지는 [PROGRESS](SECTION_13_8_PROGRESS_KO.md),실행 계획은 [PLAN](SECTION_13_8_PLAN_KO.md),학생 가이드는 [LAB](LAB_13_8_SYSTEM_VALIDATION_GUIDE_KO.md)를 참고한다. 과거 문서의 '다음 실행/아직 미확인' 문장은 당시 시점 기록일 수 있으므로 이 종합 보고서의 최신 판정과 구분한다.

## 2026-11-05 Level 2·3 실제 평가 갱신

이전 문단의 미래 작업 상태보다 [Level 2·3 평가 보고](SECTION_13_8_LEVEL23_EVALUATION_REPORT_KO.md)를 우선한다. 명세 작성 후 실제 월드/관측 이동/고정10slot 도구를 구현하고 v28 총10회(각 Level 5회)를 완료했다. 엄격한 성공은0/10이며 목표 달성은 남아 있다. 도구가 없는 상태와 목표가 미달한 상태를 구분한다.

다음 과제는 (1) Level3 실제 정착자세의pre-grasp/grasp6D IK·collision 분리, (2) Level2의최초관측/health만료와capture·TF·추론latency 연계, (3) 적재귀환 TRANSPORT_PLATFORM_UNSAFE의최초위반항목 분리, (4) 세계높이하락23.360mm와TCP/물체상대운동 분리, (5) 시작deadline의ready지연/자식회수 원인이다. 위치XY latch는공식Nav21.3.13코드를근거로별도v29수정·시험한다. 기존수명/물리기준을늘려성공시키지않는다. 저장된실패자료→작은부품/계획서비스재현→새동결의필요한실제사례순서다. 이후새고정10회를수행하면새batch/UUID/조건을명시하며v28의0/10을삭제하거나교체하지않는다.