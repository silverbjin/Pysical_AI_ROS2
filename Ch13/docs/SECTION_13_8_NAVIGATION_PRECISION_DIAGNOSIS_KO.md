# 13.8 도착 정밀도와 설정 전달 조사

2026-11-05 KST. 단일 작업자. 실제 임무 전체의 성공 보고가 아니다.

## 확인한 문제

v22 바닥 연속 동작은 BT SUCCESS로 종료했지만 귀환 오차44.449mm로 원고3cm 목표를 놓쳤다. 기존 controller_server의 xy_goal_tolerance는0.06m다. [Nav2 1.3.13 SimpleGoalChecker 원본](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_controller/plugins/simple_goal_checker.cpp)을 GitHub connector로 다시 읽었다. XY 제곱 거리 비교와 stateful=true일 때 최초 반경 진입 뒤 XY 검사를 중단하는 구현을 확인했다. 단순 action SUCCEEDED와 최종 정착3cm를 같은 결과로 취급하지 않는다.

원고 Level1에 한해0.015m를 선택해 정착 여유를 두며, 공식 권장 수치라고 주장하지 않는다. yaw0.06/statefultrue·RPP속도0.15·정책·물리·정착 경계는 유지한다. development와 기존13.6/13.7 경로의 기본0.06m도 유지한다.

## v23: 첫 설정 방법은 실제 적용 실패

첫 후보는 Node(parameters=[원래 YAML, 추가 dict])였다. 설치 감사와 소스/설치 시작 파일 SHA256은 일치했지만 실제 controller_server GetParameters는0.06을 반환했다. UUID93bcce10-caa5-4535-a31c-6c5e4a6ee0ee는 이동 전에 assertion으로 종료했다. 자식10개 정상 exit/잔여0/lock free다. 이 기록은 navigation 물리 도달 실패와 구분한 PARAMETER_ADMISSION_FAILURE다.

후속 formal navigation verifier는 terminal_status가 없는 시작 전 실패 자료를 읽어 KeyError가 났다. verifier가 이 사례를 정상 이동 FAIL로 완전 판정했다고 쓰지 않는다. 다음 probe는 시작 실패일 때 그 verifier를 호출하지 않도록 분기한다. 원래 실패 출력은 보존한다.

엔진 없는 실제 ROS parser 재현에서 원래 node-specific YAML 뒤에 /** override YAML을 추가해도0.06이 읽혔다. launch에서 구성한 dict에는0.015가 있었으며 실제 package share 경로와 설치 시작 파일도13.8이었다. 따라서 이 사례는 오래된 설치 파일이나 환경 소실이 아니라 설정 범위의 우선순위 문제다. 재현 원본은 preparation/inspect_launch_v23.py와 log다. 모든 ROS 버전/배치에 동일하다고 일반화하지 않는다.

## 공식 구현 패턴 적용

[Nav2 1.3.13 navigation_launch.py](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_bringup/launch/navigation_launch.py)의 ParameterFile(RewrittenYaml(...,convert_types=True),allow_substs=True) 패턴을 채택했다. 설치된 nav2_common/launch/rewritten_yaml.py를 읽어 전체 경로 param_rewrites도 지원하는 것을 확인했다. controller_server.ros__parameters.goal_checker.xy_goal_tolerance 한 항목을 임시 YAML에서 재작성한다. 원본 YAML을 바꾸거나 광역 wildcard로 덮지 않는다. nav2_common은 이미 설치된1.3.13 의존성이며 package.xml에 직접 사용을 명시했다.

실제 시작 파일을 평가해 생성된 YAML을 별도 rclpy Context/Node의 ROS parser에 넣는 회귀를 먼저 작성했다. 최초1 FAIL/2 PASS(3.49초)로 Level1만0.06이 남는 문제를 확인했다. 재작성 후 새 파서3개와 기존 navigation/launch/blocked 경계를 포함해13 PASS/5.40초(347 deselected)였다. default/development의0.06, yaw/stateful/RPP속도 보존도 확인한다. 전체360개를 다시 수행한 것은 아니며 기존 전체357개 이력과 구분한다.

## 실제 확인 범위

새 동결에서 실제 GetParameters와 원래 navigation 정식 판정을 사용하는 unloaded forward goal 한 번으로 확인한다. 이 시험에는 팔/적재·귀환π회전·경사/문이 없다. 최종 정착 오차, 실제 terminal, engine/자식 회수와 source freeze를 함께 기록한다. 작은 사례의 통과만으로 전체 원고3cm나10회 강건성을 주장하지 않는다. 실행 결과는 PROGRESS와 사례의 precision_verification.json을 확인한다.

### 실제 결과(각1회, 고정10회 평가 아님)

v24 첫 UUID6916dedd-6e65-403c-b8ba-180850a35b38는시작전FUTURE_SOURCE:base로이동허가를받지못했다. source수신당시clock대비미래입력/50ms순서대기경계의실패이며,원고정밀도나새YAML방법의물리도달실패로바꾸어쓰지않는다. 자식10개정상회수/lockfree다. 원래실패source/summary/archive를보존했다.

같은362개제어source에기존CH13_REUSE_STARTUP_TRACE계측만켜고새UUID로1회더확인했다. 실제controller_server는xy0.015/yaw0.06/statefultrue를반환했고(0.65,0,0)로이동후정착오차11.822090mm/yaw0.000997rad였다. precision_verification PASS와원래navigation_verification PASS,정지window0.710sim초/356개고유sample,engine정상종료·자식10개정상회수·잔여0·lockfree다. startup성공은재현됐지만앞선시작실패원인해결이나cold-start강건성보장은아니다. gateway추적의INPUT_OR_CLOCK_TIMEOUT은시계발행종료후회수구간에도기록될수있으므로그문자열만으로이동중fault라고판정하지않는다.

정확한통과UUID는9e86b6f2-91e6-4a89-a6d9-a28b550ae40d,source freeze는section_13_8_system_v24.json(362개/94자산,SHA256ae5d7f4dbd5da8e6e619360071a580b3857a6669a7112f96497f17ae13cb30fa)다. trial형식의전체임무사례가아닌unloaded navigation regression이다. Level1적재귀환π회전·common table·Level2/3·10회평가는미완료다.
