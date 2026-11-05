# 단계 4 — 수정 소스의 실제 검증과 새 평가 gate

2026-11-05 KST. 이파일은실제사례의종료후최종갱신한다. 이전단계의부품PASS를물리성공으로표현하지않는다.

## 실행 전 동결

- 단계별커밋:계획eaadea27,Level3 d4c9a1d3,촬영a843ce85,운반명령f045a111,실행전동결c50727b8.
- v30 source376/assets94,manifest SHA256 `816e0d8cfa2385d9080bc4c2082bb2ce2f4032227d28fa3d683ab13ef6522298`.
- 분리build20.5초,실제venvchild설치67모듈/기존94자산감사PASS. navigation설치자료35개(새YAML포함),manipulation24,BT6감사PASS.
- 전체399 PASS/70.33초. 동일376소스hash전수일치. Level2추가YAML source/install SHA256 `0a4ab3c88c20dcbd4521f0d9857a1e252b53110582bb5d36d270d0983e7ee41f`.
- 관측/물리/취소·회수threshold는유지했다. Level2 yaw명령상한만낮췄으며시간목표에유리한튜닝은아니다.
- 현재WSL boot `c5eba66c-cb54-4639-852b-ad9fc2d2aa5b`;실행전소유잔여0/공유lockfree. 과거boot의잔여PASS를현재증거로대체하지않았다.

실행전증거는`../evidence/section_13_8_repair/step4_preflight/`에있다. 두후속UUID/source를실행전에보존했고Level3→Level2순서로한engine씩실행한다. 기존v28 총10회와이후v29실패는보존한다.

## 실제 사례

|시나리오|UUID|상태|
|---|---|---|
|Level3 v30|673e9986-5f34-430d-b695-973feb6da98d|FAIL: survey120wall초,최종접근/팔미시작|
|Level2 v30 계획|97fad3a0-9660-432b-94ae-a300c0363ef4|미기동:대조소스v31로분리예정;본10회아님|

## 새 총10회 gate

두기능의실제접근·fresh관측·파지·연속운반·놓기·종료가통과한뒤새동결/source/scenario/10UUID를고정한다. 실패/시작실패도분모10에남긴다. 필수기능이남으면같은실패를10번반복해통계로덮지않고미충족gate와저장재현과제를명시한다. 기존0/10을지우거나다른조건의사례로교체하지않는다.
## v30 실제 실패와 촬영 제출 대조 조건

L3 v30은trial elapsed6.446sim/133.757835wall초,successfalse/complete true였다. 지도관측이동의기존120wall초deadline에서중단돼최종접근·새pre-grasp까지도달하지못했다. 새기하학수정의실제성공을주장할수없다. engine은ownedlaunch회수중KeyboardInterrupt로ERROR,정상종료요청false,자식11/12clean·engine1exit1·잔여0/공유lockfree였다. 이실패를정상종료로바꾸지않는다.

실행당시8CPU/메모리여유/스왑0을읽기전용으로확인했다. 마지막256capture의statepublish평균41.367ms/최대146.958ms,pre-offer평균7.693ms였다. 조기제출은직렬대기는줄였지만현재실행의전체성능성공을입증하지못했다. 같은설치함수의offline100회/no-opDDS profile은.59146wall/.59139CPU초였다. 이대조는liveDDS/부하가없어실제지연상한이나overlap인과증명이아니다. SciPy1.18.1/NumPy2.5.4/Torch2.9.0+cpu이며과거보고와같은SciPy버전이므로업그레이드탓으로단정하지않는다.

Ruling: v30의미통과상태에서조기제출을기본추천하지않는다. 원래직렬순서로되돌리고carry_v1+CH13_CAPTURE_OVERLAP=1에서만실험적으로사용하게한다. 수명/TF/상태발행빈도/속도/OS설정을바꾸지않는다. 이대조의새freeze v31로한번더확인하고,성능실패가반복되면계층경계를재검토하며동일실패를새10회로덮지않는다. v30의모델제외raw/source archive와hash를보존했다.