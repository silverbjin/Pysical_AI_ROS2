# Ch01 ROS 2 기초 패키지: my_first_package

Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12 / colcon 기준. 이 `ref/` 디렉터리 자체가 `ament_python` 패키지 루트다. 저장소 전체를 워크스페이스 `src/`에 넣지 말고 `ref/`만 패키지명으로 복사한다.

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git ~/Pysical_AI_ROS2
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ch01_ref_ws/src
cp -a ~/Pysical_AI_ROS2/Ch01/ref ~/ch01_ref_ws/src/my_first_package
cd ~/ch01_ref_ws
colcon build --symlink-install --packages-select my_first_package
source install/setup.bash
ros2 pkg executables my_first_package
ros2 run my_first_package simple_node
```

`simple_node`는 [1.6 실습](../docs/LAB_1_6_GUIDE_KO.md), `cmd_publisher`는 [1.7 실습](../docs/LAB_1_7_GUIDE_KO.md)을 따른다. 원본 README의 미완성 저장소 URL 및 명령을 수정했으며 `setup.cfg`에 ROS 2 실행파일 설치 경로를 추가했다. 두 실습은 실제 Jazzy 환경에서 별도 검증이 필요하다.
