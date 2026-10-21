# 11.3절 실습 가이드 — LiDAR 거리·장애물 감지

## 1. 이번 절의 목표
동적 angle_min/angle_increment를 통한 전방 ±30° 계산, NaN/Inf·측정 영역·수신 시간 검사가 구현되어 있다. 경고 동작과 실제 자동 정지는 구별해야 한다.

실제 연결: /scan (LaserScan, lidar_link, BEST_EFFORT) → lidar_safety → /lidar_safety/status (String 안의 JSON). status=OBSTACLE/CLEAR/UNKNOWN/STALE. 경고 노드는 /cmd_vel을 발행하지 않음.

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
# 터미널 A: 전체 시뮬레이션은 한 번만
ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false
# 터미널 B: 전방 스캔 감시
ros2 launch my_quadruped_bot lidar_safety.launch.py safe_distance:=0.5
# 터미널 C: QoS/상태
ros2 topic echo /scan --once --qos-reliability best_effort
ros2 topic info /scan -v
ros2 topic echo /lidar_safety/status
# RViz: 필요 시 별도 rviz2 실행, LaserScan /scan 추가
~~~

프로세스는 각기 다른 터미널에서 실행한다. 시뮬레이션·EKF·SLAM을 중복 실행하지 않는다. 움직이는 데모는 정지 명령과 터미널 종료 방법을 미리 확보하고 안전한 시뮬레이션에서만 수행한다.

## 4. 관찰 항목
장애물과 전방 최소거리가 0.5m 미만이면 OBSTACLE, 충분한 전방 유효 관측은 CLEAR, 센서 오류·결손은 UNKNOWN, 수신 단절은 STALE로 분류한다. 전방만을 판정하고 제동 명령은 보내지 않는다.

## 5. 문제 해결
/scan이 없다면 GZ bridge, lidar_link, Gazebo Ogre2 센서 플러그인, ROS_DOMAIN_ID/GZ_PARTITION 확인. status가 STALE이면 /clock·Gazebo pause·header.stamp와 timeout 확인. UNKNOWN은 JSON reason으로 추적한다.

## 6. 회귀 테스트
저장소 루트에서 실행한다. 테스트 PASS는 수치 로직/소스 계약에 한정된다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_lidar_processing.py -v
~~~

## 7. 응용 과제 및 수용 기준
안전거리 0.5m와 2.0m를 비교하고, 경고 시 로봇이 자동 정지하지 않는 이유를 정리한다. 로봇 주변 충돌 방지를 위한 추가 watchdog/footprint/하드웨어 E-stop 설계 항목도 제안한다.

체크: [ ] Ch11 prefix [ ] colcon 빌드 [ ] 타입/QoS/TF [ ] 정상 출력 [ ] 실패 입력 [ ] 로그·그래프·맵 [ ] 알고리즘 한계 설명.

## 8. 기존 구현 문서
[LIDAR_SAFETY_11_3_4_GUIDE_KO.md](LIDAR_SAFETY_11_3_4_GUIDE_KO.md) · [절별 코드 리뷰](SECTION_11_3_REPORT_KO.md).

**검증 범위 주의:** 이번 문서화 작업에서는 새 WSL2 Gazebo 통합 실행을 수행하지 않았다. 이전 evidence의 단위 테스트 통과와 실물/물리 시뮬레이션의 실측 결과를 구분한다.
