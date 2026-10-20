# LAB 3.4 — Gazebo Harmonic 월드를 직접 실행하고 검증하기

## 목표
설계된 로봇과 SDF 환경을 구분하고, 물리 시계·빛·지면·시뮬레이터 플러그인이 실제로 존재하는지 확인한다.

## 1. 실행 환경 (Ubuntu 24.04 + Jazzy + Gazebo Harmonic)
```bash
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y ros-jazzy-ros-gz
gz sim --versions
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
```
책의 `~/ros2_ws` 대신 본 저장소의 **Ch03 전용 워크스페이스**를 사용한다.

## 2. SDF 검사
```bash
python3 - <<'PY'
from xml.etree import ElementTree as ET
p='src/my_robot_description/worlds/my_world.sdf'
root=ET.parse(p).getroot()
world=root.find('world')
assert world.get('name')=='my_first_world'
plugins=[p.get('name') for p in world.findall('plugin')]
assert 'gz::sim::systems::Physics' in plugins
assert world.find("./model[@name='ground_plane']") is not None
print('world:',world.get('name'),'plugins:',len(plugins))
PY
gz sdf -k src/my_robot_description/worlds/my_world.sdf
```

## 3. 월드 실행 / 관찰
```bash
gz sim -v 4 -r src/my_robot_description/worlds/my_world.sdf
```
다른 터미널에서 `gz topic -l`, `gz stats` 실행. GUI에서 바닥·태양광이 보이고 재생하면 시뮬레이션 시간이 증가한다. 모델은 아직 없어야 정상이다. Real Time Factor는 머신 부하에 따라 1.0보다 낮을 수 있다.

## 4. 분리 진단·응용
GUI가 검은 화면이면 `gz sim -s -r ...`로 서버만 먼저 확인하고 WSLg / Ogre2 문제를 분리한다. 물리 단계 `max_step_size=0.001`을 별도 복사본에서 0.002로 변경해 RTF 변화를 비교하되, **정확도·속도 개선을 단정하지 않는다**. 실습 후 원본 복구.

## 수집할 Evidence
SDF 파서 exit, Gazebo 서버 로그, `gz topic -l`, `gz stats`, 월드 스크린샷. `my_world.sdf`의 실제 world 이름을 3.6 브리지 설정에 재사용하라. [리뷰](SECTION_3_4_REPORT_KO.md).
