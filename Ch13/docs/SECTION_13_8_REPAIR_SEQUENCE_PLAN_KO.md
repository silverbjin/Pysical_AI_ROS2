# 13.8 반복 실패 수정·재검증 실행 계획

> 단일 작업자로 superpowers:executing-plans를 적용한다. 사용자의 질문 없는 연속 진행 지시를 따른다.

기준: 9a2a00bd, feat/ch13-section-13-8. 기존 v28 총10회0/10과v29 접촉오류를 보존한다. 목표는 원인을 분리하고 필요한 최소 수정을 실제 검증하는 것이다. 자료만으로 인과를 확정하지 않으며, 새 평가를 기존 결과와 섞지 않는다.

## 공통 제약

sources/·외부94자산·Ch01~12·과거FAIL/freeze는 읽기 전용. 기존 단일ROS owner/원본300ms수명/zero-base lease/실제접촉/취소drain/한engine/공유lock을 유지한다. OS·모델·정책·WBC·effort·안전 임계값을 바꿔 통과시키지 않는다. engine 중 build/pytest/큰 분석을 하지 않는다. 현재 격리 worktree/build를 재사용하며 전역 설치를 하지 않는다.

## 1. Level3 접근·6D계획

- [x] 공식 MoveIt2.12.4/msgs2.6.0의 IK·state validity·collision contact 분리 패턴을 조사한다.
- [x] 저장된4건의 실제 정착qpos와fresh관측으로 pre-grasp/grasp 양 roll의 IK를 충돌 무시/포함으로 비교하고 실제 반환상태를 기록한다. nominal 위치IK와 실제6D의 차이를 분리한다.
- [x] v29의최초금지접촉geom/좌표/heading과지도 footprint·경로를 재구성한다.
- [x] 원인이 확인되면 관련 음성시험 RED→최소구현→GREEN, 필요한 작은 계획 검증을 수행한다.
- [x] 보고서 SECTION_13_8_REPAIR_STEP1_LEVEL3_KO.md와 증거를 커밋한다.

## 2. Level2 관측·health 수명

- [x] 1/9번관측만료와5번health만료의최초위반을촬영/TF/수신/추론/소유poll연계로추적한다.
- [x] 공식 ROS2/rclpy·현재프로세스경계와정상실패비교를근거로원인을분리하고최소수정/회귀를검증한다. 시간제한확대/now치환금지.
- [x] 보고서 SECTION_13_8_REPAIR_STEP2_OBSERVATION_KO.md와 증거를 커밋한다.

## 3. 운반 안전·세계 높이

- [x] 3번안전중단의첫tilt/vxy/wz위반과7번높이하락을몸체/TCP/물체상대운동으로분리한다.
- [x] 모델/제어안전범위안에서원인이확인된최소연결수정을검증한다. 높이20mm판정은유지한다.
- [x] 보고서 SECTION_13_8_REPAIR_STEP3_TRANSPORT_KO.md와 증거를 커밋한다.

## 4. 실제 검증·새 고정 평가

- [x] build/실제venvchild/외부94자산/전체필요회귀·source동일hash/실제소유잔여를확인한다.
- [ ] 각수정기능의가장불확실한실제사례를단일engine으로순차확인한다. 실패시자료를보존하고원인으로돌아간다.
- [ ] 필수기능이통과하면새source/scenario/10UUID를실행전에고정하고새총10회를수행한다. 실패/시작실패도분모유지.
- [ ] 기능이통과하지못하면새10회로원인을덮지않고미충족gate와재현원인을명시한다. 다른독립진단단계는계속완료한다.
- [ ] 보고서 SECTION_13_8_REPAIR_STEP4_VALIDATION_KO.md·가이드·진행기록·자체검토/원본archive를남기고커밋한다.

## 산출물·판단기록

각단계는 공식ref/파일·가설·재현명령·결과/시간·변경/미변경범위·실제/오프라인한계·다음gate를 보고한다. 두 최소수정뒤같은실패가남으면구조경계를재검토한다. 자료가없는원인은추정으로표시한다. 독립리뷰가아닌단일작업자자체검토다. 원격main병합은포함하지않으며현재요청의단계별커밋을우선한다.
