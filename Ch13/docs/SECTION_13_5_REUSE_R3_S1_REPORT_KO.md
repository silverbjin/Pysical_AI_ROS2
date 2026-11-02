# R3 S1 — 실제 센서·명령 경계와 Nav2 연결 중간 보고

작성일: 2026-11-02 KST. **R3 진행 중**, 완료/PASS 선언이 아니다. R4–R5는 후속이다.

## 고정 구성과 부품 검증

설치된 Nav2 1.3.13의 RegulatedPurePursuit/Navfn/velocity_smoother/bt_navigator를 standalone으로 연결했다. 전체 TwistStamped와 controller→smoother→navigation boundary→기존gateway→정책 경로다. 설치된 nav2_util의 twist_publisher/subscriber header에서Stamped옵션을확인했다. Spin/BackUp recovery는없다.

평지·벽·장애물은원본world의rough static기하만교체하는opt-in장면이다. body_mass/관절범위/actuator cap의원본대조와실제mj_ray장애물hit검사2개가통과했다. 정책/질량/관절/모터와기존보완3개는유지한다. scan은body-fixed환경group5 ray이며자기몸체/floor필터를명시한다. map은장면prior로실제scan과구분한다. 이장면의낮은장애물을scan높이로등반가능하다고하지않는다.

기존실제R2관절관측70개에서collision AABB를heading좌표로투영하고0.04m여유를더했다. footprint xy범위는x[-0.463469,0.394488],y[-0.288552,0.266062]m다. 임의팔동작envelope로전이하지않는다.

원본Navstamp/최초receipt·실제GID, controller손실을smoother로갱신하지않음, scan손실latch, TF동일edge2번째소유자거절을실제DDS와순수코어에서확인했다. 모든기존회귀와장면/경합검사를포함해 **57/57 PASS,18.848초**. [로그](../evidence/section_13_5_reuse/r3_preflight/tests_57.log).

## 실제 통합 실패와 제한 진단

- `3d4656a4`: 이동전arm이거절됐다. Gateway준비와Actionendpoint발견만으로Platform의safe발견이완료됐다고간주한probe문제다. 시작조건에Platform소유자/실측정착과Nav2 lifecycle ACTIVE를명시했다. 엔진·10자식정상회수.
- `0552b293`: 실제root가x0.5775m근처로이동했지만sim8.44→8.46사이wall4.5888초관측공백이생겨원래watchdog이latch했다. Nav2terminal은ABORTED였고성공으로바꾸지않는다. 모든실패/상태원본을보존했다.
- 경합검사에서Platform.monitor의외부DDS graph조회가physics상태RLock을잡고있어명령처리를막는것을RED재현했다. graph조회/publish/log를상태잠금밖으로분리했고GREEN이다. 이것만으로실제4.6초공백의유일원인을확정하지않는다. source/physics/sensor/publish/lock각구간의wall·threadCPU계측을추가해다음짧은실행에서원인을분리한다.

허용age0.30wall초,source0.30sim초,도착0.10m/0.10rad,edu_stop_v2를늘리지않았다. 같은실패계열의수정2회뒤반복되면전체시험반복을멈추고구조진단한다. R3최종Nav2실제PASS뒤R4로진행한다.

[실행 계획](SECTION_13_5_REUSE_R3_R5_PLAN_KO.md). 이전R2는당시고정본결과로보존하며이새source의실제Nav2성공을대신하지않는다.
