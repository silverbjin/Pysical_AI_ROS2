# 11.4절 실습 가이드 — EKF 오도메트리 보정

## 1. 이번 절의 목표
운영 EKF와 명령 적분 교육용 EKF가 분리되어 중복 TF를 피한다. 운영 입력은 시뮬레이터 관측 기반이므로 실물 보행 슬립 오차 보정 검증이라고 해석할 수 없다.

실제 연결: 운영: /simulation/odom → /odom/raw + /imu/data_raw → ekf_filter_node → /odom, TF odom→base_footprint. 분리된 교육: /cmd_vel → leg_odometry → /ekf_lab/raw + /ekf_lab/imu → ekf_lab_filter → /ekf_lab/filtered; 교육 필터 publish_tf=false.

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
# 터미널 A: Gazebo·기본 EKF는 단 한 번
ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false
# 터미널 B: 교육용 EKF 분리 실행
ros2 launch my_quadruped_bot ekf_lab.launch.py use_acceleration:=false
# 터미널 C: 비교할 토픽
ros2 topic echo /ekf_lab/raw --once
ros2 topic echo /ekf_lab/filtered --once
ros2 topic echo /odom --once
ros2 run tf2_ros tf2_echo odom base_footprint
# 별도 A/B 실험: B 종료 후 use_acceleration:=true로 재실행
~~~

프로세스는 각기 다른 터미널에서 실행한다. 시뮬레이션·EKF·SLAM을 중복 실행하지 않는다. 움직이는 데모는 정지 명령과 터미널 종료 방법을 미리 확보하고 안전한 시뮬레이션에서만 수행한다.

## 4. 관찰 항목
/ekf_lab/filtered가 생성되고, 기본 /odom은 EKF 1개만 발행한다. /ekf_lab 구간은 TF를 퍼블리시하지 않으므로 odom→base_footprint에 중복 발행자가 생기지 않아야 한다. 두 필터 오차 우열은 현재 실습 구조만으로 확정할 수 없다.

## 5. 문제 해결
정지된 출력은 /cmd_vel 지속 발행 여부, /imu/data_raw, /ekf_lab/imu, 시뮬레이션 /clock 확인. TF warning이면 ros2 topic info /tf -v와 ekf 설정의 publish_tf 권한을 확인한다.

## 6. 회귀 테스트
저장소 루트에서 실행한다. 테스트 PASS는 수치 로직/소스 계약에 한정된다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_ekf_lab.py -v
~~~

## 7. 응용 과제 및 수용 기준
동일 이동 명령에서 /ekf_lab/raw, /ekf_lab/filtered, /simulation/odom을 CSV로 수집하고 시간 동기/위치 오차를 계산한다. 각 출력의 오차 원인과 참값 누출 여부를 설명한다.

체크: [ ] Ch11 prefix [ ] colcon 빌드 [ ] 타입/QoS/TF [ ] 정상 출력 [ ] 실패 입력 [ ] 로그·그래프·맵 [ ] 알고리즘 한계 설명.

## 8. 기존 구현 문서
[EKF_11_4_GUIDE_KO.md](EKF_11_4_GUIDE_KO.md) · [절별 코드 리뷰](SECTION_11_4_REPORT_KO.md).

**검증 범위 주의:** 이번 문서화 작업에서는 새 WSL2 Gazebo 통합 실행을 수행하지 않았다. 이전 evidence의 단위 테스트 통과와 실물/물리 시뮬레이션의 실측 결과를 구분한다.
