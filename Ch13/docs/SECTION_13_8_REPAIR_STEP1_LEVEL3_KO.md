# 단계 1 — Level 3 접근·6D 계획 진단 및 최소 수정

작성:2026-11-05 KST. 기준9a2a00bd, 실행계획eaadea27. 단일작업자. **본평가4건의pre-grasp 실패는위치IK부재가아닌팔link3와base의자기충돌로재현됐다.** 실행후자료와설치된MoveIt서비스만사용했고engine/팔명령은실행하지않았다. 실제새임무검증은단계4에남긴다.

## 공식 패턴

[MoveIt2.12.4 kinematics_service_capability.cpp](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/move_group/src/default_capabilities/kinematics_service_capability.cpp)를읽었다. computeIK의avoid_collisions false/true분리와validity callback을따라같은목표의기구학가능성과충돌가능성을구분했다. 설치[moveit_msgs2.6.0 GetStateValidity](https://github.com/moveit/moveit_msgs/blob/2.6.0/srv/GetStateValidity.srv)의contacts를직접읽었다. timeout.sec만사용하는설치구현에맞춰1초로요청했다. 원래liveMoveIt계획·충돌회피를우회하는해는실행하지않는다.

## 실제 입력과 재현

v28 슬롯2/6/8/10의PRE_GRASP stamp에가장가까운engine qpos와그이전최신원본vision관측을선택했다. base의높이·roll/pitch/yaw와모든관절을유지하고floating world_joint의frame을reuse/odom으로명시했다. 바닥/기존벽/동일식탁·다리/실제관측원통을planning scene에적용했다. 별도ROS domain136·동일공유lock·한owner poll을사용했고shutdown ACK와planner exit0을확인했다. 기존live관측권한을새로만든것은아니다.

- 기존pre-distance.06,두roll대칭,4건의pre/grasp총16목표를충돌제외/포함으로비교했다.
- 4건의pre-grasp는양roll모두기구학IK SUCCESS,충돌포함 NO_IK_SOLUTION(-31). GetStateValidity는reuse/base↔reuse/link3 접촉을반환했다.
- 최종grasp는음의roll에서4건모두충돌포함IK SUCCESS였다. 양의roll은ground↔link6접촉으로거부됐다. 기존양roll계획후유효경로선택을유지한다.
- 거리를.60/.65/.70m로바꾼비교에서.65/.70은최종grasp의기구학IK가불가능했다. 단순히멀리서서해결하지않았다.
- 같은실제정착자세에서pre-distance만.03/.04/.05로비교했다. .03은4/4충돌포함SUCCESS, .04는2/4, .05는0/4였다. .03의최종grasp는기존과동일하다. 이범위시험이연속궤적/접촉파지성공보증은아니다.

도구초기실패도보존했다. 첫호출은PowerShell→WSL경로전달문제로모델을열기전API_SETUP_FAILURE였다. 다음버전의floating joint header누락경고를확인해frame을명시한v3를정식진단근거로썼다. v2결과로성공을추가집계하지않는다.

증거: `../evidence/section_13_8_repair/step1_saved_v3/diagnosis.json`, `step1_distances_v1/diagnosis.json`, `step1_pre_distance_v1/diagnosis.json`. 재현도구/RED·GREEN로그는`step1_tools/`에있다. 도구인자는repo절대경로와새output폴더이며기존출력을거부한다. `bash Ch13/scripts/reuse_13_8/env.sh TOOL.py REPO NEW_OUTPUT`로engine없는상태에서만실행한다.

## v29 발 접촉과 접근 방향

v29의engine오류는RR_foot↔world이며마지막20ms주기저장자세는base(2.768065,.775497,.298850)였다. 동일MuJoCo모델을재구성하면RR_foot에서reuse_table_leg_0까지최소거리5.857mm였다. contact 자체는마지막저장sample에아직없으므로이것만으로최초충돌geom을확정하지않는다. 오류시점과가까운다리의근접근거다. RPP충돌예고와이후큰위치이탈은그대로보존한다.

새Level3의지도관측지점을(1.9,1.0,0)으로정렬했다. 최종접근과같은y/heading으로다리부근추가회전을줄인다. 최종목표는계속fresh관측으로계산하며이관측지점을대상검출좌표로대체하지않는다. 이것은실제도달성확인이필요한경로선택이며충돌guard/footprint/속도/목표허용오차를변경하지않는다.

## 변경·시험

새L3만pre-distance.06→.03 및survey위치/방향을바꿨다. Level1/2/development·pitch30도·파지/접촉힘·속도·3D수명·IK/계획충돌검사는유지했다. 과거scenario/freeze/FAIL은그대로다.

저장된4건의충돌없는공식IK해를고정fixture로보존하고실제MuJoCo TCP 6D/접촉과현재pre목표를비교했다. 먼저4 FAIL/3.24초,방향시험1 FAIL/1.96초를확인했다. 최소변경뒤관련7 PASS/4.01초(새5+기존카메라2). 두새월드의actual Renderer RGB-D fit가관측/접근지점에서유지됐다. 전체회귀·설치·새freeze·실제L3는단계4에서확인한다.

## 남은 gate

충돌없는endpoint는full Cartesian접근/파지/이동성공이아니다. statefulfalse의최종도달·발/다리여유·새경로·원본관측·파지후운반은실제검증이남아있다. 실패하면기준을늘리지않고최초실패자료로돌아간다. 단계2의독립관측수명진단은계속진행한다.