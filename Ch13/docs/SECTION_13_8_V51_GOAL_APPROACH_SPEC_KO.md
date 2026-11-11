# v51 기존 RPP 목표 접근 보간 검증 명세

작성일 2026-11-12 KST. 정상 완주 기준 유지, Owner 인수 보류. 새 제어기·정책·WBC·인식기는 추가하지 않는다.

## 중단 지점과 v50 결과

ce6045ae 공개 CI run43040197736/job130589612531/runner1000006007의 모든 step이 성공했다. portable 11건이며 실제 ROS/MuJoCo 부품 497 PASS/158.14초와 구분한다. source399/assets94 동결 v50 SHA256은 1681bee36515c4f8a3f926ccf6c5a2bc93d2c907c538892af4e4f014d5af5141이다.

실제 UUID990fa443-b46e-4790-9dce-a2f9515a8dec는 survey 후 최종 NavigateToPose 240wall초 기한으로 FAIL했다. trial73.93sim/450.356wall초, CPU55.214%/8개 코어 기준이다. 이번에는 입력/관측 수명 초과가 기록되지 않았다. engine COMPLETED/normal shutdown true/12child 정상 회수/잔여 없음/lockfree다. batch Scan이 실제 선택됐고 마지막256 생산 기록 중 Scan37건 최대18.365ms였다. 전체 실행의 최대치나 반복 강건성을 보증하지 않는다.

저장 표본에서 최소 XY오차2.085mm일 때 yaw .355077rad, 최소 yaw .088746rad일 때 XY25.633mm였다. XY≤15mm와 yaw≤.06rad를 함께 만족한 저장 표본은0개다. 연속 시간 전체의 부재 증명은 아니다. 회전 중 XY 이탈과 stateless 재접근이 확인 대상이다. raw28,229,541bytes/SHA4a900561f29223c750435cc6470fb8620e7ac96ffa64b2f8acb24684364639fb 및 source_v50 정확399파일을 보존했다. v28 정식0/10을 대체하지 않는다.

## 공식 패턴과 작은 부품 조사

실제 설치 nav2-regulated-pure-pursuit-controller 1.3.13을 기준으로 다음 공식 원본/테스트를 확인했다.

- [RPP 구현](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/regulated_pure_pursuit_controller.cpp): getLookAheadPoint의 끝점 이후 가상 carrot과 fixed-curvature 분기. 일반 carrot은 그대로 목표 회전·충돌 검사에 사용한다.
- [파라미터 처리](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/parameter_handler.cpp): interpolate_curvature_after_goal은 use_fixed_curvature_lookahead가 참이어야 활성화된다.
- [경로 처리](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/path_handler.cpp): 해당 모드에서는 마지막 두 점을 보존하고 단일 점 경로를 거절한다.
- [공식 부품 시험](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/test/test_regulated_pp.cpp): 경로 보간과 끝점 연장 기대값을 확인했다.

설치 라이브러리의 getLookAheadPoint를 직접 호출하는 독립 C++ 도구로 v50 저장 자세9개를 비교했다. 동일 시각의 live plan 연결이 보존된 것은 아니므로 저장 경로의 최근접 점을 잘라 재구성한 기하 비교에 한정한다. 기존 끝점 carrot은 거리 제곱 .001 아래에서 공식 곡률 함수가0을 반환하는 구간이 있다. .25m fixed carrot+끝점 연장은 그 이전부터 경로 끝 접선 방향의 유한 곡률을 유지한다. 예를 들어 sim53 재구성에서 기존 -15.407/m, 연장 -3.725/m이고 sim54에서는0 대 -3.305/m이다. 이것이 실제 정상 도달을 보증하지 않는다. 첫 도구 빌드는 자유 함수를 멤버로 오해해 실패했으며 실패 로그를 보존하고 순수 기하 계산만 바로잡았다. 실습 소스 실패가 아니다.

velocity_smoother의 scale_velocities는 절대 속도 clipping 이후 가속도 비율을 조정하므로 각속도 포화의 직접 해결책으로 채택하지 않는다. 기존 stateless=false 변경이나 허용 오차 확대도 하지 않는다.

## 순차 작업과 통과 조건

1. RED: 실제 launch를 해석한 ROS 노드에서 Level2 기본 전진 RPP만 fixed-curvature/끝점 보간이 적용되고 다른 Level/실험 SE2 경로는 그대로임을 검사한다. 목표 XY15mm/yaw.06rad, stateless 검사, 전진만 허용, 충돌 검사·현재 속도/가속도 한도도 함께 유지한다.
2. GREEN: Level2 기본 carry_v1에만 YAML overlay를 추가한다. use_fixed_curvature_lookahead=true, curvature_lookahead_dist=.25, interpolate_curvature_after_goal=true. .25m는 기존 min_lookahead_dist를 재사용하며 일반 lookahead .45m와 목표 회전 분기는 유지한다. 새로운 탐색 조합이나 제어 알고리즘을 추가하지 않는다.
3. REFACTOR/REVIEW/관련 ROS 파라미터·전체 부품 회귀를 확인하고 COMMIT→공개 CI의 실제 runner/steps를 확인한다. 설치 파라미터/동결/시험/실행 소스 일치를 확인한다.
4. 동일15Hz/overlap1/SE2=0/계측1의 새 UUID 단일 engine으로 최종 위치·방향·정착·원본 관측·취소·회수를 판정한다. 실패하면 최초 원인과 기하를 보존한다. 안전 기준이나 정상 timeout을 완화하지 않는다.
5. 정상 연속 완료가 입증된 뒤에만 정식10회 평가 및 Owner 인수 자료를 갱신한다. PRE_GRASP 67.234sim초 후보의 전체120sim초 부담은 별도 미해결 항목이며 이 접근 변경에 팔 속도/경로 변경을 묶지 않는다.

교재 제공 범위의 기존 Nav2 설정 한 묶음에 한정한 검증이다. 300ms/TF100ms/최종3cm·120sim초·높이20mm/실제 접촉·단일 ROS owner·원래 정책·native caps·종료 기준을 유지한다.
