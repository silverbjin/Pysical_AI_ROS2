# 15.6 읽기 전용 미션 시각화 (G06 T15 scoped PASS)
WSL2 Ubuntu 24.04 / ROS 2 Jazzy. source /opt/ros/jazzy/setup.bash 및 Ch15 install/setup.bash. 다른 실험과 ROS domain 분리.
```bash
ros2 launch ch15_visualization visualization.launch.xml mode:=mock gui:=true view:=presentation
# 같은 domain에서 기존 Mock 실행기를 별도로 사용; 시각화 자체는 미션을 시작하지 않는다.
ros2 topic info -v /ch15/visualization/target
ros2 topic echo /ch15/visualization/status
```
debug/presentation은 설치 share에 있다. debug 선택 시 실제 producer 확인 후 TF/RobotModel/Scan/Path/Costmap을 선택 활성화. 제어 도구와 MoveIt interactive marker 없음.
- Target은 map, 원본 stamp, mission/epoch/source/pose_kind/finite 검증, sphere id0+text id2, 각각 lifetime 1s, invalid/stale/context 전환 시 DELETE 두 개. Status text id1은 별도 토픽의 표시 앵커이며 실제 pose가 아니다.
- physical mode: 실제 T11 cube detector의 RGBD_COLOR POSITION_ONLY 및 cube_lab epoch0 전용. G04의 물리 전체 미션 상태를 만들어내지 않는다. use_sim_time:=true는 해당 producer와 동일 clock 사용 시에만. replay mode: G05의 두 observation playback topics 범위에서 상태만 표시하며, 기록되지 않은 Target/Safety는 표시하지 않는다. REPLAY는 원본 MOCK source와 별도로 표시.
- Clock rewind는 fail-closed; 새 replay 세션에서 노드를 재기동한다. 실제 DDS fixture T15 및 시간 역행 삭제 PASS. 실제 GUI 시각 검수와 Foxglove는 아직 미검수/선택 범위.
```bash
ros2 launch ch15_visualization visualization.launch.xml mode:=replay gui:=true use_sim_time:=true
```
별도 replay domain 내에서 시작 후 관측 전용 playback을 사용한다. G05 엄격 graph 전용 probe와 동시 실행하지 말고 별도 시연으로 수행한다. G05 기록/격리 검수는 그대로 재사용.

검수 근거: [G06 최종 인수 보고서](reports/G06_FINAL_ACCEPTANCE_KO.md). PHYSICAL 표시는 실제 T11 타입과 계약을 사용하는 fixture로 검증한 것이며, 새 Gazebo 물리 실행 성공을 의미하지 않습니다.

## G09 공통 실행 경로
Ch15 루트, `CH15_SOURCE_SHA`를 실제 고정 HEAD로 설정하고 `bash scripts/run_lab.sh 15.6 --bag /absolute/mission_bag` 실행. 상세 선행 환경과 evidence archive는 [15.9](LAB_15_9_GUIDE_KO.md) 참조. 문서 조회와 실제 실행을 구분한다.
GUI는 별도 WSLg 설치 overlay에서 위 수동 명령으로 사용. 공통 headless marker 검수와 G05 replay 검수는 분리; --gui는 자동 인수 경로에서 BLOCKED.
