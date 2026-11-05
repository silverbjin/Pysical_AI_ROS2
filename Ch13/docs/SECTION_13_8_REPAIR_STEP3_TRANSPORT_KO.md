# 단계 3 — 운반 안전·세계 높이의 원인 분리

2026-11-05 KST. 단계2 a843ce85 이후. **안전중단의첫위반은실측yaw각속도였고,높이FAIL의주요기여는몸체자세변화였다.** 기존판정/한계/정책을그대로유지하며새실제검증은단계4에서수행한다.

## 안전중단의 정확한 표본

v28 slot3(dee84795)의engine phase전환event와마지막500Hz원본을맞췄다. 최초fault stamp212.538sim초와원본표본차이는0.3ns미만이다. 그때mode는ARMED,기울기0.042214rad<0.20,선속도0.120324m/s<0.30,**yaw각속도0.361169rad/s>0.35**였다. 직전표본의각속도증가와fault뒤실제감속을확인했다. 명령은vx0.1338m/s,wz0.173rad/s로원본정책이실측운동을정확히일치시킨다는가정은성립하지않는다. base위치는(0.479392,1.182970,.301154)이며경사끝부근이다. 접촉개수나기울기만의문제로바꾸지않는다.

## 기존 높이 판정과 분해

v28 slot7(621d134d)의원래판정기와같은CARRY3210표본만사용했다. 첫분석v1은CARRY_ARMED/PLACE_WAIT도포함했으므로공식비교는v2/v3만쓴다. 원본FAIL을수정하지않았다.

- 첫CARRY의물체z .643926443m→최소.620566779m:23.359663mm하락,기준20mm초과.
- 같은때TCP는21.202939mm하락,물체↔TCP의세계z상대변화는2.156724mm였다. 최대회전포함TCP상대변화는전체구간11.673208mm다.
- base는같은때7.720995mm상승했다. 가장가까운원본orientation표본(각각2ms이전)으로분해하면TCP z변화는base수직이동+7.721mm,base회전기여-27.330mm,팔의base상대기여-1.594mm다. 방향표본의2ms오차를명시하며정밀동역학동정으로주장하지않는다.
- 양finger접촉분율1.0,환경지지최소0N,물체바닥여유최소.580567m다. 여유와접촉유지를20mm기준통과로바꾸지않는다.

이는물체가23mm모두미끄러졌다는설명이나base높이가낮아져서만발생했다는설명을반박한다. 세계높이를확실히보장하려면자세여유/짧은팔운반자세등추가검증이필요하다. 새WBC·팔실시간보상·물리weld·임계값완화는도입하지않았다.

## 공식 패턴과 최소 수정

[Nav21.3.13 velocity_smoother.cpp](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_velocity_smoother/src/velocity_smoother.cpp)의max_velocity/min_velocity명령포락선과가속도한계를읽었다. [동일ref RewrittenYaml](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_common/nav2_common/launch/rewritten_yaml.py)의배열변환경계도비교했다. YAML배열을문자열스칼라로치환하지않고작은node-specific보완YAML을원본뒤에전달한다. 실제ROSparser로배열형식과적용값을검사한다.

새Level2 carry_v1에서만smoother yaw명령상한을±.20→±.10rad/s로줄였다. 선속도상한.20·RPP목표선속도.15·가감속·원본정책·실측안전한계.35·팔/손가락제어는유지한다. 명령.173일때실측.361이라는실제과도응답을근거로여유를늘리는작업자선택이며공식추천값이나실측안전보장은아니다. Level3/development/기존13.6/13.7설정은보존한다. 시간목표에불리할수있고높이해결도아직미확인이다.

먼저실제ROS파라미터시험1 FAIL/2 PASS(4.51초),최소변경뒤navigation/transport관련37 PASS/22.15초를확인했다. 이전원본YAML을직접편집하지않았다. 새YAML은기존package의config data설치glob으로포함되며단계4설치감사에서별도확인한다.

## 증거·남은 gate

`../evidence/section_13_8_repair/step3_transport_v2.json`, `step3_transport_v3.json`과`step3_tools/`의재현도구/RED·GREEN로그를참조한다. tool은저장소절대경로와새출력경로를받으며engine없는상태에서실행한다.

앞선WSL진단1회는자동승인검토서비스사용량한도로실행되지않았다. 검토가제시한재시도가능시각이지난뒤사용자의재개지시에서동일행동을다시승인받아실행했다. 우회나OS권한변경은없다. 이후WSL의기존설정키경고는원본로그에보존했으며/etc/wsl.conf를수정하지않았다.

이단계는최초안전위반과높이기여를분리했고보수적명령변경을부품검증했다. 실제반복안전/20mm높이/시간·정밀도달성은아직아니다. 다음은전체부품·설치·소스동결후단일engine실제사례검증이다. 통과하지못한기능을새10회로덮지않는다.
## 경로 구조 보완에서 유지한 안전 경계

v33부터 새 L2/L3의 velocity smoother에 `scale_velocities=true`를 적용한다. 어느 한 축이 제한될 때 명령의 곡률 관계를 유지하는 기존 Nav2 방식이다. L2 yaw cap 0.10, L3 0.20rad/s, 가속도 및 실제 native 운반 안전 한계는 유지한다. 실제 ROS parser와 전체 회귀로 설정을 확인했다. 높이 하락 23.360mm 문제를 이 설정으로 해결했다고 주장하지 않는다. 높이·시간·물리 접촉의 실제 판정은 별도 사례가 필요하다.
