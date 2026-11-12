# 13.8 조정된 교재 범위 마무리 검증 보고

사용자 확정 범위는 기본실습(이동·관측·상태확인·안전종료·실패판독),Level2과거운반·놓기기록해설,향후연속임무/Level3파지과제다. 전체미션완주인수와구분한다. [학생시작가이드](START_HERE_13_8_KO.md),[확장시연](DEMO_13_8_LEVEL2_ARCHIVE_KO.md),[향후과제](FUTURE_13_8_TASKS_KO.md)를최신안내로사용한다.

## 구현·부품·자체검토

기본명령은run_mission.py의명시적`--exercise basic`이다. BT는navigate/find/finish만요청하고원래단일ROS owner/작업snapshot/취소·종료를재사용한다. 13.7 worker와13.5 probe의opt-in observation_only hook으로MoveIt서버·파지handoff를생략하며원래full기본경로는그대로다. native hold·보행정책·관측수명·충돌검사·물리수치는변경하지않는다.

공식py_trees2.6.0의 [composites.py](https://github.com/splintered-reality/py_trees/blob/2.6.0/py_trees/composites.py)의remove_child/Sequence순차처리패턴을확인했다. callback에blocking대기나새executor를넣지않았다. basic결과는basic_result.json에쓰고전체평가trial.json과분리한다. inspect_case.py는원래판정을읽기만하며BT SUCCESS를전체PASS로바꾸지않는다.

RED: 신규basic/reader모듈부재2FAIL/3.80초. GREEN: 기본BT의비조작진행·failurelatch·종료검사·과거판정불변등16PASS/3.44초. REFACTOR: 기존full트리확장을공통configure_tasks로옮기고사용하지않는import를제거했다. 최종전체537PASS/69.74초/native snapshota8b4f145250a4554928d479cbd6e6220. 전체검사는실제ROS/py_trees환경이며공개CI의휴대형부분시험과구분한다.

자체REVIEW에서기본명령의pick/return/place미요청,worker의무조작handoff,MoveIt비기동,full/batch호환,원본관측·실제정착·thread/process회수의검사보존을확인했다. 독립리뷰어검증은아니다. 실제새모드의종료검증은아래에별도로기록하며부품PASS만으로물리성공을주장하지않는다.

## 실제 기본실습 확인

v53의build/설치/동결·시험소스일치와공개CI확인뒤Level2·Level3각최대1회실행한다. 이것은관측후종료하는새기본모드검증이며충돌해결의네번째튜닝시도가아니다. 제어·경로·안전수치를바꾸거나실패를교체재실행하지않는다. 실제결과는후속항목에추가한다. 현재이문단은실행완료증거가아니다.

## 인수 범위

기본PASS는이동·관측·실제정착·무조작·정상회수의검사다. 동작실패시도원인/중단/회수판독실습자료로제시하되동작PASS와구분한다. Level2과거전체순서1회는v28기록시연이고최신코드재현성은향후과제다. Level3집기이후는미검증이고3회튜닝중단을유지한다. 원래0/10과FAIL/freeze는변경하지않는다. 이번패키지범위결정은사용자가확정했으나전체미션성공/실기검증/Owner최종인수를대신선언하지않는다.
