# LAB 3.3 — Xacro로 2-DOF 팔을 재사용 가능한 설계로 바꾸기

## 학습 목표
중복 상수 제거(`xacro:property`), 공통 링크·관성 계산 매크로, 자동 URDF 변환을 직접 확인한다. **물리량의 좌표축**을 설명할 수 있어야 합격이다.

## 준비
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt install -y ros-jazzy-xacro liburdfdom-tools
```

## 1. Xacro 출력 생성
```bash
XACRO=src/my_robot_description/urdf/two_dof_arm.urdf.xacro
xacro "$XACRO" > /tmp/two_dof_arm.urdf
check_urdf /tmp/two_dof_arm.urdf
```
예상: `two_dof_arm` 로봇, 링크 `base_link/link1/link2/end_effector_link`, `joint1/joint2/joint_ee`. 원고의 예제에는 일부 매크로가 생략되었지만 GitHub 파일에 구현되어 있다. 기존의 `urdf/two_dof_arm_generated.urdf`는 **오래된 산출물**이므로 비교 기준으로 재사용하지 않는다.

## 2. 매크로와 숫자 검증
```bash
python3 - <<'PY'
from xml.etree import ElementTree as ET
root=ET.parse('/tmp/two_dof_arm.urdf').getroot()
assert {e.get('name') for e in root.findall('link')}=={'base_link','link1','link2','end_effector_link'}
assert {e.get('name') for e in root.findall('joint')}=={'joint1','joint2','joint_ee'}
for name in ['link1','link2']:
    link=next(e for e in root.findall('link') if e.get('name')==name)
    origin=link.find('inertial/origin')
    inertia=link.find('inertial/inertia')
    assert abs(float(origin.get('xyz').split()[2])-0.25)<1e-9
    assert abs(float(inertia.get('ixx'))-0.0210416666667)<1e-6
    assert abs(float(inertia.get('iyy'))-0.0210416666667)<1e-6
    assert abs(float(inertia.get('izz'))-0.0004166666667)<1e-6
print('Xacro inertia & chain: PASS')
PY
```

## 3. 응용 실험
Xacro의 `link_len`을 0.5→0.6m로 실험용 복사본에서 변경한 뒤 변환한다. `joint2/origin`과 EE 부착 좌표가 함께 0.6m로 바뀌어야 한다. 관성도 `Ixx/Iyy` 증가, `Izz` 일정(너비·깊이 불변)이 되는 이유를 설명한다. 변경 후 `git diff`로 실험을 원복한다.

## 4. 결과물과 문제 해결
증거: 생성 URDF, 파서 출력, Python assertion 결과, 변경 전후 관성값 표. `unknown macro cylinder_inertia`는 매크로 정의 누락, `property not defined`는 변수 범위 오류, `check_urdf` 실패는 XML 생성·트리 검사를 순서대로 확인한다. WSL2에서도 정적 검증은 GUI 없이 수행된다.

**다음 단계**: 생성한 URDF를 3.7 스폰과 3.8 제어에 사용하며, Gazebo 동역학 성공 여부는 별도로 검증한다. [리뷰](SECTION_3_3_REPORT_KO.md).
