# Level 3 파지 전 경로 충돌 — 최대 3회 해결 명세·원장

사용자 지시: 충돌을 해결하되 반복 튜닝은3회로 제한하고 초과가 필요하면 중단한다. 단일 작업자. 교육용 education_v1 기준을 사용하며 충돌·수명·실제 접촉·안전 종료는 유지한다.

## 시도 계산과 중단 규칙

기준 실패는 e475ece0-9f70-4dae-8de9-491ee92c95fc/source_v51이다. 저장 자료를 원래 설정으로 읽거나 재생하는 기준 진단은 튜닝0회다. 대안 설정/구조 한 묶음을 실제 planner 또는 engine에서 검증하기 전에 시도 번호를 부여한다. 확률적 재계획을 통과할 때까지 반복하지 않는다. 실패한 설정을 다른 숫자로 바꾸거나 새 해결 가설로 바꾸면 다음 시도로 계산한다. 같은 설정의 부품→실제 확인은 같은 시도의 검증 단계이지만 engine 재실행으로 실패를 교체하지 않는다. 세 번째 해결 시도 뒤에도 해결이 입증되지 않으면 추가 변경/실행을 중단하고 실패 증거·소유 회수·보고서를 남긴다.

현재 튜닝 사용0/3. 세 설정을 미리 탐색하거나 장시간 matrix를 돌리지 않는다.

## 기준 진단 완료·시도1 등록

원본archive SHA를 확인한뒤 설치MoveIt의GetStateValidity로 후보0의539/540와 후보1의389~391/967/1014~1020 충돌을 재현했다. 침투는약.082~1.234mm이며 양끝점은valid였다. 인접한 valid표본 사이의관절공간거리는각.02338/.02286이다. domain136 planner의shutdown ACK/exit0을확인했다. 원래실패index와같은충돌을확인했지만사후재구성base/관측의정확한계획시각일치는보증하지않는다.

시도1/3: Level3 group의longest_valid_segment_fraction을.005→.0001로좁혀같은끝목표2개를각1회계획한다. 작은팔에서짧은식탁충돌구간을건너뛰는가설에대한검증이며원인확정이아니다. 시간화후ValidateSolution/path_tolerance.001/link3 padding.03/2초계획예산/모델·장면·ACM은그대로다. 검사를느슨하게하지않으며새planner를추가하지않는다. 성공응답도기존실행시간·속도·가속도계약을별도로검사한다. 이설정의숫자를다시바꾸면시도2다. 결과가나오기전추가설정은시험하지않는다.

시도1결과: 두roll모두OMPL 2.0초 TIMED_OUT/외부error99999, 성공경로없음. 엔진/팔미실행, planner shutdown ACK/exit0. 설정은실습소스에적용하지않았다. 사용1/3.

시도2/3등록: 같은.0001분할/2초예산/기존충돌·시간화설정에서 충돌검사포함GetPositionIK로현재6D목표의관절해를먼저얻고, 그관절해에기존joint_goal RRTConnect를요청한다. IK성공만으로통과하지않고endpoint유효성/전체ValidateSolution/기존실행제한을모두요구한다. 과거joint값을새실행권한으로사용하지않는다. 이비교가통과할경우에만fresh원본관측에서동일하게계산하는구현을검토한다. 단순deadline확대나재시도는하지않는다.

시도2결과: 두roll의충돌검사포함IK는-31/NO_IK_SOLUTION으로거절돼joint계획에진입하지못했다. 양끝점valid인원래계획은위치.001/축별방향.01의영역목표이며정확한6D IK와동일문제가아니다. 저장끝점FK의재구성목표오차는각.875/.970mm, 총방향오차.01369/.00884rad였다. 총방향각과축별허용치는같은값이아니며원래제약위반이라고단정하지않는다. planner shutdown ACK/exit0,실습코드변경없음. 사용2/3.

시도3/3등록: 기존pose영역목표로돌아가고 Level3 분할.0005/계획예산5초를한정해각roll1회비교한다. .0001/2초조합의계산비용과좁은구간을동시에고려한마지막설정이다. 관절범위의유클리드extent약10.15에해당하는검사간격은약.0051rad로,저장충돌인접점간.0057~.0078rad보다작다. 연속충돌없음보증은아니므로전체ValidateSolution을유지한다. 목표허용치/시간화/path_tolerance/여유/모델/ACM은그대로다. 5초는MoveIt요청예산이며기존owner의서비스대기8초안이다. 새제어기/수명완화/실제팔명령없이저장장면에서먼저검사한다. 결과가미달이면추가설정·네번째시도없이중단한다.

## 최종 결과 — 사용3/3, 해결 미입증으로 중단

시도3은 첫pose 후보의OMPL 탐색이약3.186초뒤시간화로넘어갔지만 AddTimeOptimalParameterization 처리가약17.283초소요됐다. 요청의5초는전체서비스기한이아니며이시간화단계까지보증하지않았다. 진단서비스대기12초를넘어AssertionError가났고,예외회수의SIGINT후8초wait도초과했다. 이후planner로그의ValidateSolution 진입/PLANNER_JOINED와실제소유프로세스없음/공유lockfree를확인했다. 결과JSON은finally의두번째예외로작성되지않았으며그실패를FAILED.json과원본로그로보존했다. 뒤늦은응답내용/전체경로유효성/실행시간계약은확인하지못했다. 두번째roll계획은발행하지않았다.

따라서세번째시도를성공으로표시하지않고추가서비스기한확대/재실행/네번째설정없이중단했다. **실습실행소스는v52 그대로이며세진단설정중어느것도제품코드에적용하지않았다. 엔진/팔궤적은한번도실행하지않았다.** 전체미션성공/충돌해결/실기안전/Owner인수를주장하지않는다. 문서·진단도구·실패와회수증거만커밋·게시한다.

추가연구가필요하다면시간화비용과경로검사이산화를함께검토해야하지만이번승인한도에서실행하지않는다. 사용자가별도지시하기전자동재개하지않는다. 전체부품521PASS는변경없는v52의과거검증이며이번실패진단의GREEN으로표현하지않는다.

## 현재 근거와 공식 패턴

실제 MoveIt ValidateSolution은 후보0의539/540(1102점)에서 table_top/link3, 후보1의389~391/967/1014~1020(1595점)에서 table_leg_0/link7 충돌을 기록했다. 두응답은error99999이며 팔 궤적은 미실행이다. Level3의 link3 padding.03m와 TOTG path_tolerance.001은 이미 적용돼 있다. 과거 padding/TOTG 수정이 이번 충돌을 해결했다고 취급하지 않는다.

- [MoveIt2.12.4 ValidateSolution](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/planning/planning_response_adapter_plugins/src/validate_path.cpp): 전체 반환경로의상태검증과실패index를유지한다.
- [동일버전 OMPL planning context](https://github.com/moveit/moveit2/blob/2.12.4/moveit_planners/ompl/ompl_interface/src/model_based_planning_context.cpp): longest_valid_segment_fraction/절대최대간격중보수적인분할을사용한다.
- [MoveIt 공식 OMPL 설명](https://github.com/moveit/moveit2_tutorials/blob/main/doc/examples/ompl_interface/ompl_interface_tutorial.rst): 충돌검사의이산화와비용/신뢰도의관계다. 최신설명을설치API보다우선하지않는다.

현재 group longest_valid_segment_fraction=.005다. 짧은 충돌구간이OMPL이산화 또는 TOTG변형으로 생겼는지는 아직분리전이다. 최종점IK성공으로전체경로성공을대체하지않는다.

## 순차 작업

1. 원본archive해시를검증하고원래qpos/관측/실패index를읽는다. domain136/공유lock/설치MoveIt의GetStateValidity로같은충돌을재현한다. actuator/engine을실행하지않는다. 재구성시각과원래계획시각의한계를기록한다.
2. 재현결과와공식구현을근거로첫해결가설을정하고시도1을기록한다. 설정변경은한정하고검사/형상/접촉규칙은제거하지않는다. 작은부품부터확인하며RED→GREEN→REFACTOR→REVIEW→COMMIT→공개CI→필요한실제검증순으로진행한다.
3. 같은설정의실제검증에서충돌없는PRE_GRASP실행/완료를구분해기록한다. 다른원인으로그전에중단되면해결미입증으로남긴다. 파지전충돌해결과전체미션완료를혼동하지않는다.
4. 필요한경우에만시도2/3을각각명시하고검증한다. 최대3회뒤중단한다. 기준/실패/원래freeze를바꾸지않고각단계보고서와커밋을보존한다.
