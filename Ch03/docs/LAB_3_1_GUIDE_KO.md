# LAB 3.1 — URDF로 첫 강체와 관절 정의하기

## 학습 목표
`visual`, `collision`, `inertial`, `link`, `joint`를 비교하고, 좌표계·질량중심·관성 모멘트가 동일한 형상을 다른 목적으로 기술함을 설명한다. 결과물은 **2개 링크/1개 관절**의 `simple_arm.urdf`이다.

## 준비
Ubuntu 24.04, ROS 2 Jazzy. 책의 `~/ros2_ws`는 예시 경로이며 실제 저장소는 `~/Pysical_AI_ROS2/Ch03/ros2_ws`이다. 다른 장의 `install/setup.bash`를 중첩 source하지 않는다.
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y liburdfdom-tools ros-jazzy-xacro ros-jazzy-robot-state-publisher
```

## 실습 A — XML/URDF 정적 점검
```bash
python3 - <<'PY'
import xml.etree.ElementTree as ET
p='src/my_robot_description/urdf/simple_arm.urdf'
r=ET.parse(p).getroot()
print('robot:',r.attrib['name'])
print('links:',[x.get('name') for x in r.findall('link')])
print('joints:',[x.get('name') for x in r.findall('joint')])
assert len(r.findall('link'))==2
assert len(r.findall('joint'))==1
PY
check_urdf src/my_robot_description/urdf/simple_arm.urdf
```
**예상 관찰**: `simple_bot`, `base_link`·`link1`, `joint1`; 파싱 성공. XML 파싱만으로 물리값의 현실성은 확인되지 않는다.

## 실습 B — 링크의 중심 비교
`base_link/visual/origin`과 `base_link/inertial/origin`의 z=0.025, `link1`의 z=0.15를 비교한다. `joint1/origin`의 z=0.05는 부모 원점에서 **관절 부착 지점**을 나타내므로 관성 중심과 다르다. 변환 전후 모델의 링크 개수·관절 개수가 변하지 않는 것을 확인한다.

## 실습 C — 응용 실험
별도 실험 브랜치에서만 link1의 `visual/origin` z=0.15→0 변경 후 RViz에서 중심 변화를 관찰하고 원복한다. **관성 값만 변경해서 RViz 화면이 달라지지는 않는다.** 물리 엔진 실험은 3.7~3.8절에서 수행한다.

## 검증 체크리스트
- [ ] XML 파서/URDF 파서 종료코드 0
- [ ] 질량이 모두 양수이고 관성 대각이 양수
- [ ] joint 축·회전 범위를 설명
- [ ] 정적 형상과 실제 중력하 운동 검증을 구분
- [ ] 터미널 출력과 수정 전후 `git diff` 보관

**문제 해결**: `check_urdf: command not found`면 `liburdfdom-tools` 설치, `package not found`면 ROS 환경 source, 시각화는 3.2절의 `display.launch.py` 수정 이후 연결한다. 참고: [코드 리뷰](SECTION_3_1_REPORT_KO.md).
