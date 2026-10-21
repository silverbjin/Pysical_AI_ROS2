# 11.5절 실습 가이드 — SLAM Toolbox 2D 지도 생성

## 1. 이번 절의 목표
단일 TF 소유자, SLAM lifecycle 실행 파일 포함, 센서 정합성을 고려한 스캔 필터 경로가 존재한다. 실제 지도 생성·저장과 loop closure 품질은 새 실험에서 미확인.

실제 연결: 시뮬레이션+단일 EKF → /odom, odom→base_footprint 및 /scan. slam_scan_filter → /scan/slam → slam_toolbox (lifecycle activated) → /map + map→odom TF. 지도 저장은 nav2_map_server map_saver_cli 경로.

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
# 터미널 A: 시뮬레이션+EKF (추가 localization 실행 금지)
ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false
# 터미널 B: SLAM+지도 RViz (단일 인스턴스)
ros2 launch my_quadruped_bot slam.launch.py
# 터미널 C: lifecycle/토픽/TF
ros2 lifecycle get /slam_toolbox
ros2 topic info /scan/slam -v
ros2 topic echo /map --once
ros2 run tf2_ros tf2_echo map odom
# 충분한 특징을 관찰한 뒤 지도 저장
bash Ch11/scripts/save_slam_map.sh "$HOME/Pysical_AI_maps/section_11_5"
~~~

프로세스는 각기 다른 터미널에서 실행한다. 시뮬레이션·EKF·SLAM을 중복 실행하지 않는다. 움직이는 데모는 정지 명령과 터미널 종료 방법을 미리 확보하고 안전한 시뮬레이션에서만 수행한다.

## 4. 관찰 항목
slam_toolbox 상태는 active, /map은 nav_msgs/OccupancyGrid, map→odom TF가 유효해야 한다. 저장 후 section_11_5.pgm과 .yaml이 실제 생겼는지 확인한다. 벽/장애물 특징과 루프 재방문을 통한 정렬은 GUI 실험으로만 평가한다.

## 5. 문제 해결
맵이 비면 /scan와 /scan/slam의 주기/헤더/frame을 확인하고 /clock 및 robot tf tree를 재점검. RViz Map QoS는 reliable/transient local 여부 확인. 중복 SLAM 또는 EKF 프로세스 제거.

## 6. 회귀 테스트
저장소 루트에서 실행한다. 테스트 PASS는 수치 로직/소스 계약에 한정된다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_slam_mapping.py -v
~~~

## 7. 응용 과제 및 수용 기준
주행 전·후 /map 크기, 해상도, 탐사 영역 변화를 기록하고 저장 맵을 Gazebo 벽 배치와 겹쳐 직선성·중복 벽 여부를 평가한다.

체크: [ ] Ch11 prefix [ ] colcon 빌드 [ ] 타입/QoS/TF [ ] 정상 출력 [ ] 실패 입력 [ ] 로그·그래프·맵 [ ] 알고리즘 한계 설명.

## 8. 기존 구현 문서
[SLAM_MAPPING_11_5_GUIDE_KO.md](SLAM_MAPPING_11_5_GUIDE_KO.md) · [절별 코드 리뷰](SECTION_11_5_REPORT_KO.md).

**검증 범위 주의:** 이번 문서화 작업에서는 새 WSL2 Gazebo 통합 실행을 수행하지 않았다. 이전 evidence의 단위 테스트 통과와 실물/물리 시뮬레이션의 실측 결과를 구분한다.
