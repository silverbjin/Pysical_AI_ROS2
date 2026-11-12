# 13.8 조정된 교재 범위 마무리 검증 보고

사용자 확정 범위는 기본실습(이동·관측·상태확인·안전종료·실패판독),Level2과거운반·놓기기록해설,향후연속임무/Level3파지과제다. 전체미션완주인수와구분한다. [학생시작가이드](START_HERE_13_8_KO.md),[확장시연](DEMO_13_8_LEVEL2_ARCHIVE_KO.md),[향후과제](FUTURE_13_8_TASKS_KO.md)를최신안내로사용한다.

## 구현·부품·자체검토

기본명령은run_mission.py의명시적`--exercise basic`이다. BT는navigate/find/finish만요청하고원래단일ROS owner/작업snapshot/취소·종료를재사용한다. 13.7 worker와13.5 probe의opt-in observation_only hook으로MoveIt서버·파지handoff를생략하며원래full기본경로는그대로다. native hold·보행정책·관측수명·충돌검사·물리수치는변경하지않는다.

공식py_trees2.6.0의 [composites.py](https://github.com/splintered-reality/py_trees/blob/2.6.0/py_trees/composites.py)의remove_child/Sequence순차처리패턴을확인했다. callback에blocking대기나새executor를넣지않았다. basic결과는basic_result.json에쓰고전체평가trial.json과분리한다. inspect_case.py는원래판정을읽기만하며BT SUCCESS를전체PASS로바꾸지않는다.

RED: 신규basic/reader모듈부재2FAIL/3.80초. GREEN: 기본BT의비조작진행·failurelatch·종료검사·과거판정불변등16PASS/3.44초. REFACTOR: 기존full트리확장을공통configure_tasks로옮기고사용하지않는import를제거했다. 최종전체537PASS/69.74초/native snapshota8b4f145250a4554928d479cbd6e6220. 전체검사는실제ROS/py_trees환경이며공개CI의휴대형부분시험과구분한다.

자체REVIEW에서기본명령의pick/return/place미요청,worker의무조작handoff,MoveIt비기동,full/batch호환,원본관측·실제정착·thread/process회수의검사보존을확인했다. 독립리뷰어검증은아니다. 실제새모드의종료검증은아래에별도로기록하며부품PASS만으로물리성공을주장하지않는다.

## 실제 기본실습 확인

v53의build/설치/동결·시험소스일치와공개CI확인뒤Level2·Level3각최대1회실행한다. 이것은관측후종료하는새기본모드검증이며충돌해결의네번째튜닝시도가아니다. 제어·경로·안전수치를바꾸거나실패를교체재실행하지않는다. 실제결과는후속항목에추가한다. 현재이문단은실행완료증거가아니다.

### 후속 실제 결과 — 두 기본 모드 PASS

구현commit e16e6886의공개CI run43131816598/job130897523357/runner1000006347 모든step success를확인했다. 설치75모듈/외부94자산감사PASS, v53 동결407소스의SHA는a9f2e440237a6c2d7fa2169f70853ecf45db644a158854b69c351f4decb8d7f6이다. 전체537PASS의native snapshot과manifest/runtime모든소스hash가일치했다. 실행profile은basic/15Hz/overlap1/SE2=0/추가callback계측0이다.

|기본 실습|UUID|결과|sim초|wall초|접근 정착 오차|
|---|---|---|---:|---:|---:|
|Level2|0831b1ae-8328-4a4d-be22-219778dea20d|PASS|55.430|172.921|10.701mm|
|Level3|426650e5-0aca-4d5b-a5b7-1660ba776602|PASS|42.200|96.307|32.645mm|

두사례모두navigate/find/finish만요청·완료했고basic검사10항목이true였다. Level2는실제경사접촉·fresh find, Level3는실제문통과·식탁아래대상fresh find를확인했다. MoveIt서버로그/arm_probe.json/pick_mission.json/full trial.json은없다. nativehold는유지하되팔/gripper동작명령을발행하지않았다. 각각11개자식정상회수/잔여[]/lockfree,worker·수신/정책thread회수·bagclose를확인했다. basic_result의full_mission_success는false다.

각Level선택1회이며반복강건성/80%성공률/전체파지·귀환·놓기인수가아니다. 과거Level3충돌의3회중단설정을다시시험하거나숫자를튜닝하지않았다. 새OS/원격clone부터의전과정설치를이번검증에서반복한것도아니다.

실제설치된inspect_case.py로두basic PASS와과거v28시연을읽었다. 과거BT SUCCESS/trial FAIL은그대로표시됐고기본PASS를전체성공으로바꾸지않았다. 새학생문서4개의로컬링크도확인했다. 상세결과는evidence/section_13_8_policy/book_closeout_v53_20261112.json에있다.

### 보존과 디스크 관리

두실행의정확한407source를모델제외archive로보존했다. source archive공통SHA는e30ff1f3959730b9f063b42f4afc5e383cd6816454d9a84400e0e2b11b57e9e4다. raw archive는Level2 16,493,243bytes/SHAd8f8465add420eae1e74f957ecd6140899962aacbca5493d493d90f5ea7c3e4a,Level3 12,787,631bytes/SHA7e297857bf1898ab94e2eb0d72eba402bd8b272c28a50a0179f3a20c675087da다. 압축전원본·멤버hash를확인하고필수압축본/작은판정/정확한source를유지했다. 해시가같은대형비추적중복18파일120,277,395bytes만정리했다. receipt는retention_book_basic_v53_20261112.json이다.

교재기본실습·시연해설·향후과제분리의개발검증을마쳤다. 제공범위는사용자가확정한새목표이며검토자료를갖춘상태다. 최종Owner인수는사용자검토사항으로남기고전체미션의원래실패판정을대신승인/변경하지않는다.

## 인수 범위

기본PASS는이동·관측·실제정착·무조작·정상회수의검사다. 동작실패시도원인/중단/회수판독실습자료로제시하되동작PASS와구분한다. Level2과거전체순서1회는v28기록시연이고최신코드재현성은향후과제다. Level3집기이후는미검증이고3회튜닝중단을유지한다. 원래0/10과FAIL/freeze는변경하지않는다. 이번패키지범위결정은사용자가확정했으나전체미션성공/실기검증/Owner최종인수를대신선언하지않는다.
