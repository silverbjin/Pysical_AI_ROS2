# LAB 3.5 — 로봇 외형과 실제 충돌 범위 비교

## 목표
`visual`은 표현, `collision`은 접촉 검사, `inertial`은 질량 분포임을 **동일 링크에 대한 XML·GUI 관찰**로 설명한다. 본 절은 3.2와 3.3의 수정이 main에 반영되어야 완전 검증할 수 있다.

## 1. 파일 선택·모델 구분
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
grep -n -A 22 '<link name="link1"' src/my_robot_description/urdf/two_dof_arm.urdf
find src/my_robot_description/meshes -maxdepth 1 -type f -name '*.stl' -print
```
기본 URDF는 단순 primitive box/cylinder, STL은 주석화된 심화 경로다. 책 속 예제에 STL 메시는 기본 동작 필수 조건이 아니다.

## 2. 정적 비교 실험
```bash
python3 - <<'PY'
from xml.etree import ElementTree as ET
p='src/my_robot_description/urdf/two_dof_arm.urdf'
r=ET.parse(p).getroot()
l=next(x for x in r.findall('link') if x.get('name')=='link1')
for tag in ['visual','collision','inertial']:
    e=l.find(tag)
    print(tag, 'origin=',e.find('origin').attrib if e.find('origin') is not None else {})
PY
```
**기대**: 3.2 수정 병합 후 link1 visual/collision `xyz=0 0 0.25`, `rpy=0 0 0`; inertial 중심 `z=0.25`. 서로 다른 geometry를 써도 중심축은 같아야 한다.

## 3. GUI 검사
```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description display.launch.py model:=two_dof_arm.urdf
```
RViz에서 RobotModel의 Collision geometry 표시를 켜거나 Gazebo에서 충돌 형상 렌더링을 활성화하여 visual과 비교한다. 3.2 병합 전에는 수평으로 누운 visual과 세로 collision의 차이를 관찰할 수 있다. 실제 물리 운동은 3.7·3.8에서 별도로 확인한다.

## 4. 응용 과제
STL로 visual을 바꾸더라도 collision은 저해상도 primitive를 유지한다. STL 단위와 축을 Blender에서 확인하지 않고 임의 scale로 맞추지 말 것. `link_1.stl`·`link_2.stl` 동일성은 파일 정보로 확인되지만 형상 설계 의도는 확인되지 않았다.

## 합격 기준
코드 링크, XML 출력, 충돌체/외형 스크린샷, CoM 공식 계산 과정, 전체 시스템 테스트 미수행 항목을 증거로 남긴다. [리뷰](SECTION_3_5_REPORT_KO.md).
