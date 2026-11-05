# 13.8 Level2·Level3 및 총10회 평가 작업 명세

2026-11-05 KST. 기준3447c9e8/v24. 단일 작업자. 사용자는 명세 작성 후 실행을 지시했으며 앞선 '질문 없이 진행' 지시는 유지한다. 구체 치수·평가 배치는 아래 작업자의 선택이며 사용자에게 치수별 승인을 받았다고 표현하지 않는다.

## 목적·방법 선택

원고13.8.2의 박스/5도 경사,좁은 문/식탁 아래 대상을 실제 MuJoCo·Nav2·기존 BT에 연결하고,동일 소스의 사전 고정된10회 실제 실행을 평가한다. 정상 목표 미달·시작 실패·관측/접촉 실패를 그대로 기록한다.

기존2m 바닥 과제에 장애물만 추가하는 방법은 월드 부품 비교에는 싸지만 공통(3,1) 과제를 연결하지 못한다. 모든 것을 새 탐색/전신 제어로 교체하는 방법은 승인 범위를 넘는다. **기존 제어를 유지하고 알려진 지도상의 관측 지점까지 먼저 이동한 다음 fresh RGB-D로 최종 접근하는 방법**을 선택한다. 대상 정답 freejoint를 제어에 쓰지 않는다. Level2는(3,1)의 테이블 위 원통,Level3는 같은XY의 식탁 아래 원통이다.

새 학습/WBC/CoM 이동/정책 중지/teleport/물리 weld/effort·마찰 증가·OS 우선순위 변경은 추가하지 않는다. 알려진 원통 반경2cm/높이8cm/20g/마찰0.8,원본 정책·PD·0.5N·팔0.05rad/s 및0.1rad/s²,관측/heartbeat300ms·과거TF100ms·기존취소/FAULT latch를 유지한다.

## 월드·시나리오

좌표는m,box size는반치수다. 방의 기존외벽/원본 floor는유지하고아래 기하는새opt-in profile에만추가한다. 모든선택값은scenario.json에포함해hash로동결한다.

| 항목 | level2_obstacles | level3_house |
|---|---|---|
| 원통 중심 | (3,1,0.54) | (3,1,0.04) |
| 수령 지점 | (-0.8,0,0.54),기존0.5m지지대 | (-0.6,0,0.04),원래floor |
| 관측 이동 goal | (1.7,0.3,atan2(0.7,1.3)) | (1.9,0.4,atan2(0.6,1.1)) |
| 파지 | 기존development의수평접근/0.12m,stand-off0.8m | 기존floor의아래30도/0.06m,stand-off0.6m |
| 카메라 | 기존development profile | 기존level1_floor profile |
| 테이블 | 중심XY(3,1),상판0.50×0.60m/높이0.50m,다리4개 | 중심XY(3,1),상판0.90×1.00m/높이0.90m,다리4개 |
| 장애물 | box 중심(1.05,0.45,0.35),size(0.14,0.20,0.35) | 문 평면x=1.1,opening y[-0.35,0.75],폭1.10m,높이있는벽2개 |
| 경사 | x[0.45,0.95],폭3m,상승/하강각각5도,정점높이0.25tan(5°) | 없음 |

상승/하강 ramp는회전 box의상면으로만든다. floor처럼보행가능한물리접촉을가지고2D지도에서치명장애물로표시하지않는다. 두면의회전/끝점/정점은수치시험으로검증한다. 팔과지면/경사의금지접촉검사는유지한다.

상판은실제3D충돌과MoveIt scene에남기되2D지도에서상판전체를막힌벽으로투영하지않는다. 다리·문벽·박스는map에포함한다. LiDAR는실제ray결과를유지한다. 초기/관측지점/접근자세의실제RGB-D가시성을부품에서확인한다. 가림 때문에대상이보이지않으면실패이며과거좌표를새관측으로대체하지않는다.

## 제어·소유권 연결

1. /start_mission 수신과기존startup/zero-command준비뒤관측이동을수행한다. 팔lease는아직없다.
2. 같은ROS owner의비동기NavigateToPose를사용하고send/result/cancel ACK와client회수를추적한다. 실제SUCCEEDED와실측정착을확인한다.
3. 같은engine의다음최종접근goal로이어간다. 이미ARMED이면fresh zero/실제정착/소유상태를확인해재arm없이진행한다. legacy실행의기존arm계약은유지한다. reset으로FAULT를해제하지않는다.
4. 관측지점이후목표의fresh3D를기존select_goal에전달한다. 최종팔접근좌표는관측으로계산하고지도상의대상좌표를대신넣지않는다.
5. 기존pick→예약return→freshPLACE→지지→실제개방/detach→후퇴→유지→Finish를재사용한다. 총engine600sim/runner1200wall·개별action120sim/240wall을유지한다.

## 판정·환경을실제로거쳤는지

기존pick/transport의독립사후물리판정을유지한다. 기존world높이20mm기준을이번결과에맞춰바꾸지않고상대slip도보조수치로보고한다. 최종success에는BT SUCCESS·실제물리·bagclose·worker/client/child회수와world witness가모두필요하다.

- Level2: 실제base가경사앞/뒤를통과하고ramp와실제보행접촉이있어야한다. 목표테이블의실제fresh관측을획득해야한다.
- Level3: 실제base가문opening안에서문평면을통과하고,물체가실제상판아래에있으며fresh관측/find를완료해야한다.
- witness는평가전용로그다. control/lease권한으로사용하지않는다. obstacle/table불법접촉은기존물리guard로실패한다.
- world를실제로거치지않았거나자료가없으면witness FAIL이다. 계획경로나정적모델존재만으로PASS하지않는다.

## 총10회평가

**한batch에총10회,Level2/Level3를교대로각5회**실행한다. Level별10회나고정단일월드10회반복과동일한통계로해석하지않는다. 전체와Level별표를모두제공한다. 사전batch plan에10개UUID·순서·source/asset manifest hash·scenario hash·동일seed정책을적고실행전에동결한다. 사전개발/부품실행은10회에포함하지않는다.

각slot은한번만기동한다. 실패를성공할때까지재시도/교체하지않는다. 시작실패와미완료도전체분모10에남긴다. 다음case전실제lock/소유잔여를검사한다. 이전case가미회수면다음engine을시작하지않고남은slot은미실행으로표시한다. 강제kill로정상회수처럼기록하지않는다.

성공률≥90%,평균Start~Finish sim시간≤120초(별도wall평균),각도착오차<0.03m,최대roll/pitch<0.1rad,평균CPU<70%를원고목표로평가한다. 현재metrics의정의와원고표현의차이는보고한다. 실패/중단시간·누락·NaN은0으로채우지않으며전체평균을정의할수없으면unavailable/FAIL로둔다. 관측된부분집합의평균은유효개수와함께보조수치로만제시한다.

## 공식패턴·검증순서·산출물

Nav21.3.13 static_layer.cpp/공식navigation_launch.py의지도와node-specific RewrittenYaml패턴,MuJoCo3.13.0 mjmodel.h의geom pose/group,기존rclpy비동기goal/단일owner를우선비교한다. static occupancy와실제3D충돌을구분한다. 공식예제는이로봇의물리성공증거가아니다.

명세→실행계획→실패시험→최소구현→부품/설치/source감사→필요한사전실제사례→새동결의10회순차실행→집계/보존/자체검토순서로진행한다. engine중build/pytest/대용량분석을병행하지않는다. 같은계열두수정후에도실패하면구조/의존성/경계를검토한다. 실패때기준을늘리지않는다.

산출물: worlds/survey/batch평가코드,기하·guard·집계음성시험,새source freeze,batch plan/10slot실제자료,JSON/CSV/한국어결과보고,가이드/진행기록갱신. 원고Level1/기존FAIL·외부자산·sources/는변경하지않는다. 자체검토는단일작업자의독립성한계를표시한다.
