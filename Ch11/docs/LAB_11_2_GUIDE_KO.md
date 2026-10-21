# LAB 11.2 — IMU 자세 추정·상보 필터

## 1. 목표와 핵심 개념
센서 header.stamp 기반 dt, 유효성 검사, max_dt 리셋이 구현되어 있다. 상보 필터 그래프·실시간 동작은 아직 재검증하지 않았다.

데이터 흐름: Gazebo IMU → /imu/data_raw (sensor_msgs/Imu, BEST_EFFORT) → imu_processor → /imu/rpy_filtered (std_msgs/Float32MultiArray, [roll,pitch,yaw] rad). EKF 자체는 /imu/data_raw 구독.

## 2. 시작 전 점검
Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / WSL2 기준. Conda·venv·Ch07~Ch10 다른 장의 overlay를 해제하고 새 터미널을 연다. 저장소가 ~/Pysical_AI_book 이외의 경로라면 변경한다.

~~~bash
cd ~/Pysical_AI_book
source /opt/ros/jazzy/setup.bash
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
~~~

각 터미널에 Jazzy 및 Ch11 install/setup.bash를 source한다. 동일 시스템에서 다른 장의 Gazebo를 실행할 경우 ROS_DOMAIN_ID와 GZ_PARTITION도 분리한다.

## 3. 따라 하기
~~~bash
# 터미널 A: Gazebo+ROS 브리지+로봇을 단 한 번 실행
ros2 launch my_quadruped_bot SLAM_simulation.launch.py
# 터미널 B: 자세 처리만 별도 실행
ros2 launch my_quadruped_bot imu_processing.launch.py alpha:=0.98
# 터미널 C: 토픽 진단
ros2 topic echo /imu/data_raw --once --qos-reliability best_effort
ros2 topic info /imu/rpy_filtered -v
ros2 topic echo /imu/rpy_filtered
# 선택: rqt_plot 설치 뒤 그래프
ros2 run rqt_plot rqt_plot
~~~

## 4. 기대 결과 및 판정
rqt_plot의 /imu/rpy_filtered/data[0]와 data[1]에 roll/pitch [rad]가 표시된다. 자세 변화를 준 뒤 응답 방향을 확인하고 alpha=0.95와 0.98의 지연/피크를 비교한다. 단일 alpha에 대한 일반적인 최적성은 미검증.

## 5. 오류 진단
데이터가 없으면 /imu/data_raw 실제 메시지, QoS BEST_EFFORT, use_sim_time 및 IMU frame_id 확인. IMU orientation_covariance=-1이라도 처리할 수 있지만 가속도·자이로 미제공이면 샘플이 폐기된다.

## 6. 자동 검사
아래 명령은 저장소 루트에서 실행한다. 단위 테스트가 성공해도 ROS 토픽, GPU LiDAR, 실제 물리 응답 검증은 별도이다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_imu_processing.py -v
~~~

## 7. 응용 과제
정지·완만한 기울임·걸음 중 roll/pitch 그래프를 기록하고 α별 지연과 진폭, yaw 누적 오차를 분리해 해설한다.

## 8. 제출물과 한계
- [ ] Ch11 패키지 prefix 및 빌드 로그
- [ ] 핵심 토픽 타입·시각·메시지/그래프 캡처
- [ ] 정상 조건과 오류 조건의 관찰 메모
- [ ] 미검증 항목과 재실행 환경 표기

상세 구현 가이드 [IMU_PROCESSING_11_2_4_GUIDE_KO.md](IMU_PROCESSING_11_2_4_GUIDE_KO.md) · [절별 코드 리뷰](SECTION_11_2_REPORT_KO.md).

이번 문서 작성 과정에서 실제 WSL2·Gazebo 실행을 새로 수행하지 않았으므로 결과 화면이나 성공 로그를 만들어내지 않았다.
