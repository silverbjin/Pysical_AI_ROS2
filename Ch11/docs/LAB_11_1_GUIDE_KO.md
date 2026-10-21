# LAB 11.1 — 위치 추정·추측 항법

## 1. 목표와 핵심 개념
교육용 명령 적분과 운영용 Gazebo 모델 관측 경로가 분리되어 있다. 구조 검토는 통과, WSL2/Gazebo 런타임 검증은 보류.

데이터 흐름: 교육 데모: /demo/cmd_vel (Twist) → command_odometry_demo → /demo/odom (Odometry). 실제 시뮬레이션 추정: /simulation/odom → sim_odometry → /odom/raw → EKF → /odom. TF는 EKF가 odom → base_footprint 단독 발행.

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
# 터미널 A: 시뮬레이터 없는 교육용 적분 노드
ros2 run my_quadruped_bot command_odometry_demo --ros-args -p use_sim_time:=false
# 터미널 B: 10 Hz 명령, 몇 초 후 Ctrl+C
ros2 topic pub -r 10 /demo/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}'
# 터미널 C: 적분 결과 확인
ros2 topic echo /demo/odom
~~~

## 4. 기대 결과 및 판정
정상 시 /demo/odom의 x 값이 명령 입력 동안 증가하고, 명령이 0.2초 이상 끊기면 보고 속도가 0으로 바뀐다. 적분 거리 = 실제 로봇 주행 거리라는 뜻은 아니다. 별도 실험에서는 SLAM_simulation.launch.py를 단독 실행하여 /simulation/odom과 /odom/raw를 비교한다.

## 5. 오류 진단
토픽이 없으면 ros2 pkg executables my_quadruped_bot와 ros2 node info를 확인한다. 프레임/시간 문제가 있다면 다른 장의 install overlay, /clock, TF 발행자 수를 검사한다.

## 6. 자동 검사
아래 명령은 저장소 루트에서 실행한다. 단위 테스트가 성공해도 ROS 토픽, GPU LiDAR, 실제 물리 응답 검증은 별도이다.

~~~bash
cd ~/Pysical_AI_book
python3 -m unittest discover -s Ch11/tests -p test_localization_contract.py -v
~~~

## 7. 응용 과제
직진 및 회전 명령을 각 5초씩 적용하여 모델 예상 x/y/yaw와 실제 데모 출력을 비교하고, 시간 경과와 slip_factor가 측정 가능한 지표인지 토론한다.

## 8. 제출물과 한계
- [ ] Ch11 패키지 prefix 및 빌드 로그
- [ ] 핵심 토픽 타입·시각·메시지/그래프 캡처
- [ ] 정상 조건과 오류 조건의 관찰 메모
- [ ] 미검증 항목과 재실행 환경 표기

상세 구현 가이드 [CH11_LOCALIZATION_FIX_REPORT_KO.md](CH11_LOCALIZATION_FIX_REPORT_KO.md) · [절별 코드 리뷰](SECTION_11_1_REPORT_KO.md).

이번 문서 작성 과정에서 실제 WSL2·Gazebo 실행을 새로 수행하지 않았으므로 결과 화면이나 성공 로그를 만들어내지 않았다.
