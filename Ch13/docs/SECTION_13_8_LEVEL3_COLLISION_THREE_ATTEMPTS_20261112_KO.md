# Level 3 파지 전 경로 충돌 — 최대 3회 해결 명세·원장

사용자 지시: 충돌을 해결하되 반복 튜닝은3회로 제한하고 초과가 필요하면 중단한다. 단일 작업자. 교육용 education_v1 기준을 사용하며 충돌·수명·실제 접촉·안전 종료는 유지한다.

## 시도 계산과 중단 규칙

기준 실패는 e475ece0-9f70-4dae-8de9-491ee92c95fc/source_v51이다. 저장 자료를 원래 설정으로 읽거나 재생하는 기준 진단은 튜닝0회다. 대안 설정/구조 한 묶음을 실제 planner 또는 engine에서 검증하기 전에 시도 번호를 부여한다. 확률적 재계획을 통과할 때까지 반복하지 않는다. 실패한 설정을 다른 숫자로 바꾸거나 새 해결 가설로 바꾸면 다음 시도로 계산한다. 같은 설정의 부품→실제 확인은 같은 시도의 검증 단계이지만 engine 재실행으로 실패를 교체하지 않는다. 세 번째 해결 시도 뒤에도 해결이 입증되지 않으면 추가 변경/실행을 중단하고 실패 증거·소유 회수·보고서를 남긴다.

현재 튜닝 사용0/3. 세 설정을 미리 탐색하거나 장시간 matrix를 돌리지 않는다.

## 기준 진단 완료·시도1 등록

원본archive SHA를 확인한뒤 설치MoveIt의GetStateValidity로 후보0의539/540와 후보1의389~391/967/1014~1020 충돌을 재현했다. 침투는약.082~1.234mm이며 양끝점은valid였다. 인접한 valid표본 사이의관절공간거리는각.02338/.02286이다. domain136 planner의shutdown ACK/exit0을확인했다. 원래실패index와같은충돌을확인했지만사후재구성base/관측의정확한계획시각일치는보증하지않는다.

시도1/3: Level3 group의longest_valid_segment_fraction을.005→.0001로좁혀같은끝목표2개를각1회계획한다. 작은팔에서짧은식탁충돌구간을건너뛰는가설에대한검증이며원인확정이아니다. 시간화후ValidateSolution/path_tolerance.001/link3 padding.03/2초계획예산/모델·장면·ACM은그대로다. 검사를느슨하게하지않으며새planner를추가하지않는다. 성공응답도기존실행시간·속도·가속도계약을별도로검사한다. 이설정의숫자를다시바꾸면시도2다. 결과가나오기전추가설정은시험하지않는다.

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
