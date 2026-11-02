# 11.7절 실습 가이드 — 자율 매핑·지도 저장 프로젝트

## 1. 이번 절의 목표
통합 월드·준비 확인·시간 제한 탐사·정지 및 지도 저장 구조가 구현되어 있다. Nav2/frontier 기반 완전 탐사가 아니라 bounded reactive 탐사이며 지도 완성 보장은 없다.

실제 연결: mapping_total.launch.py: Gazebo maze_room + EKF + FSM + IMU + stabilizer + SLAM; start_explorer 기본 false. readiness 확인 후 autonomous_explorer가 /scan 및 /scan_stabilized·/map·TF를 감시하며 /cmd_vel 제어. 저장은 종료·운영자 요청·BLOCKED 시 시도되고 PGM/YAML 품질 검토는 별도.

## 2. 사전 준비
- Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, WSL2 기준.
- Conda/venv, Ch07~Ch10 overlay를 해제하고 새 터미널을 열 것.
- 다음 예제의 저장소 위치가 다르면 ~/Pysical_AI_book을 실제 경로로 변경할 것.

~~~bash
cd ~/Pysical_AI_book
source /opt/ros/jazzy/setup.bash
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
~~~

반드시 Ch11 install을 가리켜야 한다. 새 터미널마다 Jazzy 및 Ch11의 install/setup.bash를 source한다. 실험별 ROS_DOMAIN_ID 및 GZ_PARTITION으로 다른 장과 분리한다.

## 3. 실습 순서
~~~bash
# 방법 A: 초기에는 탐사 비활성 상태
ros2 launch my_quadruped_bot mapping_total.launch.py
# 다른 터미널: 센서·SLAM 준비 진단
ros2 lifecycle get /slam_toolbox
ros2 topic info /scan_stabilized -v
ros2 topic info /odom -v
ros2 run tf2_ros tf2_echo map base_footprint
# 준비 완료 후 종료하고 방법 B로 재실행 (동시 실행 금지)
ros2 launch my_quadruped_bot mapping_total.launch.py start_explorer:=true duration:=300.0 output_dir:="$HOME/Pysical_AI_maps"
# 상태 모니터링
ros2 topic echo /exploration/status
# 수동 지도 저장 테스트가 필요한 경우
bash Ch11/scripts/save_slam_map.sh "$HOME/Pysical_AI_maps/section_11_7"
~~~

프로세스는 각기 다른 터미널에서 실행한다. 시뮬레이션·EKF·SLAM을 중복 실행하지 않는다. 움직이는 데모는 정지 명령과 터미널 종료 방법을 미리 확보하고 안전한 시뮬레이션에서만 수행한다.

## 4. 관찰 항목
준비 완료 이전에는 /cmd_vel 탐사 명령이 나오지 않아야 한다. 탐사가 진행되면 전방 장애물에서 회전 및 정지 판단을 하고, 제한 시간이 지났거나 BLOCKED이면 명령이 0으로 돌아가야 한다. 지도는 partial일 수 있고 저장 파일의 실재·내용 검사까지 수행해야 한다.

## 5. 문제 해결
ready 상태가 되지 않으면 /clock, /odom 단독 publisher, map→base_footprint TF, /scan_stabilized 및 초기 기립을 순서대로 확인. 지도 저장 실패 시 nav2_map_server, 대상 폴더 쓰기 권한과 map_saver timeout 확인. 이동 장애는 /exploration/status의 이유를 추적하고 무작정 속도를 올리지 않는다.

## 6. 회귀 테스트
저장소 루트에서 실행한다. 테스트 PASS는 수치 로직/소스 계약에 한정된다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_autonomous_mapping.py -v
~~~

## 7. 응용 과제 및 수용 기준
5분 시뮬레이션 3회에서 BLOCKED 횟수·미지 격자 비율·지도 보존·로봇 위치와 장애물 접촉 여부를 기록한다. 알고리즘의 완전성/미검증 항목을 정직하게 기술한다.

체크: [ ] Ch11 prefix [ ] colcon 빌드 [ ] 타입/QoS/TF [ ] 정상 출력 [ ] 실패 입력 [ ] 로그·그래프·맵 [ ] 알고리즘 한계 설명.

## 8. 기존 구현 문서
[AUTONOMOUS_MAPPING_11_7_GUIDE_KO.md](AUTONOMOUS_MAPPING_11_7_GUIDE_KO.md) · [절별 코드 리뷰](SECTION_11_7_REPORT_KO.md).

**검증 범위 주의:** 이번 문서화 작업에서는 새 WSL2 Gazebo 통합 실행을 수행하지 않았다. 이전 evidence의 단위 테스트 통과와 실물/물리 시뮬레이션의 실측 결과를 구분한다.
