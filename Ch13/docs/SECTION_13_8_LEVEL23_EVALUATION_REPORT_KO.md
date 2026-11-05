# 13.8 Level 2·3 고정 10회 평가 보고

작성: 2026-11-05 KST. 작업 명세와 계획을 먼저 작성하고 단일 작업자로 실행했다. **v28의 총 10회(각 Level 5회) 실제 평가를 완료했으며 엄격한 임무 성공은 0/10이다.** 목표 미달을 구현 완료나 물리 성공으로 표현하지 않는다. 초기 개발 실패와 이후 수정 검증은 이 10회의 분모와 구분한다.

## 범위와 동결

명세: [LEVEL23_EVALUATION_SPEC](SECTION_13_8_LEVEL23_EVALUATION_SPEC_KO.md), 계획: [LEVEL23_EVALUATION_PLAN](SECTION_13_8_LEVEL23_EVALUATION_PLAN_KO.md).

Level 2는 (3,1)의 높이 0.5m 테이블, 박스, 5도 오르내림 경사와 실제 접촉을 포함한다. Level 3는 식탁 아래 바닥 원통과 폭 1.1m 문 통과를 포함한다. 치수는 명세에 공개한 교재용 선택이다. 기존 정책·모델·팔 속도·원본 관측 수명·운반 높이 하락 20mm 기준을 유지했다. 지도의 관측 지점 이동 후 새 RGB-D 관측으로 최종 접근한다. freejoint의 실제 위치는 실행 후 평가에만 쓴다.

평가 폴더: `../evidence/section_13_8_system/batch_level23_20261105_c148d796/`.

- 소스 동결 v28: 372개 파일, 외부 자산 94개.
- manifest SHA256: `7522c22eb7d6a7715837cb8cc2d278b67606b8b647738bf89d724d12bf998c99`.
- 계획 10UUID와 source/scenario hash를 commit `ab21bce0`에 실행 전에 보존했다.
- Level 2/3 교대 각 5회, 슬롯당 기동 1회. 중간 소스·조건 변경이나 실패 교체가 없다.
- 기존 결정적 초기 설정을 유지했다. OS/ROS 스케줄링까지 결정적이라고 주장하지 않는다.

## 결과

|슬롯|Level|UUID 앞 8자리|경과 sim초|경과 wall초|실패 또는 최종 상태|
|---|---|---|---:|---:|---|
|1|2|610482f4|79.928|201.291|PRE_GRASP 중 OBSERVATION_EXPIRED|
|2|3|ddd74629|48.240|108.572|pre-grasp 6D 목표 자세 계획 실패|
|3|2|dee84795|211.022|479.293|Pick PASS 후 귀환 TRANSPORT_PLATFORM_UNSAFE|
|4|3|aee04f73|10.258|30.991|startup/Nav2 readiness deadline|
|5|2|abfa9990|229.220|545.814|Pick PASS 후 귀환 CAPTURE_HEALTH_EXPIRED|
|6|3|d382c578|47.480|111.281|pre-grasp 6D 목표 자세 계획 실패|
|7|2|621d134d|259.912|630.094|BT SUCCESS, 운반 높이·3cm·120초 목표 미달|
|8|3|4b413caf|47.960|107.431|pre-grasp 6D 목표 자세 계획 실패|
|9|2|dc937a83|64.240|134.277|PRE_GRASP 중 OBSERVATION_EXPIRED|
|10|3|29b1f378|47.378|101.478|pre-grasp 6D 목표 자세 계획 실패|

정확한 기계 판정과 수치는 원본 `trial.json`, batch `evaluation.json`, `trials.csv`, `failure_analysis_v28.json`을 우선한다. 위 wall값은 표시용 반올림이다.

Level별 성공은 각각 0/5다. 경사 접촉/문 통과와 fresh find의 world witness는 9/10 PASS이며 시작 실패 슬롯 4는 FAIL이다. Pick 물리 판정은 슬롯 3·5·7에서 PASS였다. 슬롯 7은 동일 engine에서 파지→약 3.918m 운반→지지·개방·detach·후퇴·Finish를 실행했지만 전체 성공으로 집계하지 않는다.

슬롯 7의 실제 최소 lift는 101.245mm, hold 2.22sim초, 양 finger 접촉 100%였다. 운반 중 세계 높이 하락 23.360mm가 기존 20mm 상한을 넘었다. TCP 높이도 해당 시점 21.203mm 낮아졌으며 최대 TCP 상대 slip은 11.673mm였다. 전체 운반 contact fraction은 1.0이다. 정착 오차 55.231mm, 경과 259.912sim초로 3cm·120초 목표도 미달했다. 접촉 유지와 BT SUCCESS를 높이/정밀도/시간 성공으로 확대하지 않는다.

10건 모두 종료 자료는 완성됐지만 귀환 오차는 1건만 존재한다. 기존 엄격한 집계기는 누락된 9건 때문에 `finite_nonnegative_metrics=false`로 전체 FAIL과 공식 평균 null을 반환한다. 별도 `available_metrics`의 sim 평균 104.564초·wall 평균 245.052초는 **실패/조기 중단을 포함한 경과 평균**이며 정상 Start~Finish 120초 달성 증거가 아니다. CPU 보조 평균은 10건 43.311%다. 10건 중 관측된 최대 roll/pitch는 0.067441rad로 0.1rad 미만이지만 조기 중단 사례를 완전 임무 안정성으로 확대하지 않는다. 귀환 오차 보조 평균 55.231mm는 1건만의 값이다.

## 반복 문제와 조치

1. **검출 부재와 센서 고장의 혼동**: 사전 v25는 최초 시야 밖 원통 부재가 영구 fault가 됐고, v26의 최초 검출 전 예외만으로는 v27의 회전 중 시야 이탈을 처리하지 못했다. 두 최소 수정 뒤 같은 계열이 재발해 구조 경계를 재검토했다. 새 L2/L3에서 검출 없음과 카메라/TF/시계 고장을 분리했다. 검출 실패는 관측 좌표나 시각을 발행·갱신하지 않는다. 기존 300ms 신선도와 legacy 부재 fault는 보존한다. v28 본 평가에서 이 영구 부재 fault는 재발하지 않았지만 관측 수명/health 만료는 별개로 남았다.
2. **접근 후보 탐색 범위**: v26의 기존 direct±0.15rad 후보 3개는 식탁 다리 footprint 검사에서 모두 거부됐다. 저장한 실제 qpos/관측으로 재구성해 cardinal 4개 중 3개의 footprint+위치 IK 통과를 확인했다. 새 월드만 절대 4방향 후보를 사용하고 실제 Nav2 경로 비용·충돌 검사를 유지했다. 이는 완전한 6D 팔 계획 보증이 아니다.
3. **Level 3의 6D 목표 상태 부적합**: 본 평가 4건에서 OMPL이 goal tree의 유효 상태를 샘플하지 못했다. 위치 IK 통과와 자세/충돌을 포함한 실제 MoveIt 계획의 차이다. 원인을 warmup이나 상판 충돌로 단정하지 않는다. 실제 정착 자세에서 pre-grasp와 grasp의 6D IK·충돌 원인을 분리하는 저장 자료 검증이 남아 있다.
4. **Level 2 관측 수명 만료 2건**: native action이 `lease:OBSERVATION_EXPIRED`로 실제 ABORTED했다. 마지막 원본 관측과 capture/TF/추론 지연을 연결해 분석해야 한다. now로 치환하거나 수명을 늘려 통과시키지 않는다.
5. **적재 귀환 안전/health 중단**: 각각 TRANSPORT_PLATFORM_UNSAFE와 CAPTURE_HEALTH_EXPIRED 1건이다. 전자는 moving support의 기울기/선속도/각속도 조건이며 단순 floor contact 개수 문제가 아니다. 어떤 항이 처음 위반됐는지 아직 분리하지 않았다. 후자는 검출 부재 정책과 다른 실제 health 수명 경계다.
6. **Nav2 XY latch**: 도달한 9건 모두 이동 중 목표 1.5cm 이내를 통과했으나 실제 terminal 시점 3.308~6.854cm, 정착 후 약 3.064~6.585cm였다. 공식 구현의 `stateful=true`가 최초 XY 통과 후 XY를 재검사하지 않는 동작과 일치한다. 본 10회 판정은 그대로 두고, 새 L2/L3에서만 `stateful=false`인 v29를 별도 검증한다. 이것이 Level 3 6D 계획 실패까지 해결한다고 아직 주장하지 않는다.
7. **시작/회수 문제**: 슬롯 4의 readiness deadline 1건은 확정 원인을 더 분리해야 한다. 해당 lifecycle_manager는 소유 launch의 SIGINT/SIGTERM 유예 후 SIGKILL로 종료됐다. 이를 정상 자식 종료라고 쓰지 않는다.

## 공식 패턴과 검증 근거

- [Nav2 1.3.13 SimpleGoalChecker](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_controller/plugins/simple_goal_checker.cpp): XY latch 동작을 설치 버전 원본으로 확인했다. v29는 L2/L3의 stateful만 false로 바꾸며 플러그인/속도/yaw/legacy를 변경하지 않는다.
- [Nav2 1.3.13 navigation_launch.py](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_bringup/launch/navigation_launch.py): node-specific YAML에 실제 적용되는 ParameterFile/RewrittenYaml 패턴을 재사용했다.
- [MoveIt Task Constructor GenerateGraspPose](https://github.com/moveit/moveit_task_constructor/blob/ros2/core/src/stages/generate_grasp_pose.cpp): 각도 표본 생성 패턴을 참고했다. MTC stage나 의존성을 도입한 것은 아니다.
- [vision_msgs Detection3DArray](https://github.com/ros-perception/vision_msgs/blob/ros2/vision_msgs/msg/Detection3DArray.msg): 검출 목록과 센서 고장을 구분하는 비교 근거다. 해당 메시지로 API를 교체하지 않았다.
- [MuJoCo 3.13.0 mjmodel.h](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mjmodel.h): 기존 geom pose/group 경계를 재사용했다.

공식 예제의 존재를 이 로봇의 성공 증거로 표현하지 않는다. v28 전체 부품은 387 PASS/57.07초, 실제 실행 372소스와 시험 snapshot 전수 hash 일치, 실제 venv child 설치 67모듈/외부94자산 감사 PASS였다. v29 stateful 변경은 먼저 2 FAIL/3 PASS를 재현한 뒤 5 PASS/6.36초를 확인했다. 문서·집계·archive 보완만으로 장시간 engine matrix를 반복하지 않는다.

## 종료·보존과 한계

10건 모두 worker complete, engine 정상 종료 요청/owned thread join을 확인했다. 9건은 자식 12개 정상 회수, 슬롯 4는 11개 정상+위 lifecycle_manager 강제 종료였다. 10회 전후 잔여 검사와 마지막 잔여 검사는 모두 PASS/소유 process 0/공유 lock free다. 이 검사는 과거 검사 시점의 증거이며 현재 상태를 영구 보증하지 않는다.

원래 trial/verdict/FAIL, raw 자료, 동결 v25~v28은 수정하지 않는다. 실행 후 추가한 분석 JSON은 새 파일이다. v28 실제 source와 모델 제외 raw archive/hash를 사례별로 보존 완료했다. 공통 source archive SHA256은 `1fdf3bb5169bb7cbd58488fe6b00bd2dcd5102f19bf2148bdf7c9fc5946add03`이며 raw archive별 hash는 각 `raw_manifest.json`에 있다. 원본은 삭제하지 않는다.

이 평가는 알려진 원통·교육용 ground-truth localization·시뮬레이션의 각 Level 5회다. 일반 인식·실기·학습·새 WBC·다른 시뮬레이터의 검증이 아니다. 목표 성공률·시간·정밀도는 미달했으며 수치 기준을 완화하지 않았다.
## v29 별도 후속 1회: 실제 도달 검증 실패

본10회와분리한UUID `b2feddf0-745f-4728-92dd-5aed5fab4d3b`는Level3,source372/assets94 manifest SHA256 `b930403ea7ee9b00b210fed06d0760924cd922c55d1d45a462d1e86de2d903a7`로실행했다. 전체389 PASS/62.25초와동일372소스hash일치·설치67모듈/94자산감사를확인한뒤실행했다.

결과는FAIL,82.622sim/178.196wall초다. 문통과와원통관측·후보선택뒤실제최종접근을진행했으나RPP의collision ahead경고가반복됐고,`pick forbidden contact:RR_foot:world:WAITING`으로engine이ERROR종료됐다. 뒤따른NAV_INPUT_TIMEOUT/INPUT_OR_CLOCK_TIMEOUT은engine중단후발생했으므로이를최초원인으로바꾸지않는다. goalterminal은실제CANCELED(5),대기중인goal0,workercomplete,bagclosed다. engine정상종료요청은false이며정상물리종료로표현하지않는다. engine의수신/상류/camera threadjoin은확인됐고자식12개중11개clean/engine1개exit1,최종잔여0/lockfree였다. cleanup_error의owned launch exited:0도원본에남겼다.

따라서`stateful=false`는ROS설정시험과최초XY통과뒤재검사라는코드의미까지만검증됐다. 이로봇의Level3도달/충돌회피/6D계획성공은검증되지않았다. 임계값완화·충돌guard제거·즉시재시도로통과시키지않고저장실패의접근경로·실제foot접촉geom·Nav2footprint/heading여유를다음진단과제로남긴다. v29를학생용성공profile로권장하지않는다. 이1회를기존10회에교체투입하거나새10회평가라고부르지않는다.

10본사례+후속1사례의raw/source archive해시감사는 `batch_level23_20261105_c148d796/archive_audit_v28_v29.json`에별도기록했다. 이는보존검증PASS이며임무FAIL을변경하지않는다.