# 11.6절 실습 가이드 — 4족 SLAM 최적화·스캔 안정화

## 1. 이번 절의 목표
IMU-스캔 시간 매칭·기울기 게이트와 balanced/wide_search 튜닝 프로필이 있다. 넓은 검색이 실제 정합성을 높인다는 실험 수치는 없어 비교 과제로만 제시해야 한다.

실제 연결: 기본 2D: /imu/data_raw + /scan → scan_stabilizer → /scan_stabilized → slam_toolbox. 대안 stabilizer:=tf는 EKF-TF 게이트. 3D 실습은 lidar_3d:=true+slam_3d.launch.py로 분리한다.

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
# 터미널 A: 시뮬레이션+단일 기본 EKF
ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false
# 터미널 B: IMU 기반 필터와 balanced SLAM
ros2 launch my_quadruped_bot slam_optimized.launch.py profile:=balanced
# 터미널 C: 실제 안정화 스캔 확인
ros2 topic hz /scan_stabilized
ros2 topic info /scan_stabilized -v
ros2 lifecycle get /slam_toolbox
# B를 종료한 뒤 wide_search로 같은 이동 시나리오 반복
ros2 launch my_quadruped_bot slam_optimized.launch.py profile:=wide_search
~~~

프로세스는 각기 다른 터미널에서 실행한다. 시뮬레이션·EKF·SLAM을 중복 실행하지 않는다. 움직이는 데모는 정지 명령과 터미널 종료 방법을 미리 확보하고 안전한 시뮬레이션에서만 수행한다.

## 4. 관찰 항목
/scan_stabilized는 입력 /scan과 stamp/frame을 유지하면서 기울어진 표본 일부를 버릴 수 있다. 프로필별 map 품질과 CPU 처리율을 함께 측정해야 하며 wide_search가 언제나 더 좋다는 판정은 하지 않는다.

## 5. 문제 해결
스캔이 0Hz이면 /imu/data_raw quaternion·covariance, lidar TF, max_imu_delta=0.03, max_tilt_degrees=5 확인. 기존 slam.launch.py를 동시에 띄우면 map/TF 중복이 발생한다.

## 6. 회귀 테스트
저장소 루트에서 실행한다. 테스트 PASS는 수치 로직/소스 계약에 한정된다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_slam_optimization.py -v
~~~

## 7. 응용 과제 및 수용 기준
3도·5도·10도 기울기 허용치와 balanced/wide_search 프로필을 비교해 스캔 보존 비율, 지도 중복 벽, 처리율, 실측 시각을 기록한다.

체크: [ ] Ch11 prefix [ ] colcon 빌드 [ ] 타입/QoS/TF [ ] 정상 출력 [ ] 실패 입력 [ ] 로그·그래프·맵 [ ] 알고리즘 한계 설명.

## 8. 기존 구현 문서
[SLAM_OPTIMIZATION_11_6_GUIDE_KO.md](SLAM_OPTIMIZATION_11_6_GUIDE_KO.md) · [절별 코드 리뷰](SECTION_11_6_REPORT_KO.md).

**검증 범위 주의:** 이번 문서화 작업에서는 새 WSL2 Gazebo 통합 실행을 수행하지 않았다. 이전 evidence의 단위 테스트 통과와 실물/물리 시뮬레이션의 실측 결과를 구분한다.
