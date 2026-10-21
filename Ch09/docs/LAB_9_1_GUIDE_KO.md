# 9.1절 실습 가이드 — 4족 로봇 12자유도와 링크 구조

> 대상: ROS 2 Jazzy / Gazebo Harmonic / Ubuntu 24.04(WSL2 포함). Ch09 독립 워크스페이스를 사용한다. 이 문서는 실제 코드에 맞춘 점검 절차이며, 정상 실행은 아직 실측하지 않았다.

## 학습 목표와 사전 지식

12개 독립 회전 관절의 이름을 읽고, REP-103 축을 설명하고, FR/FL/RR/RL의 반사 부호를 검증한다. 토크 제어·보행보다 먼저 **관절 영점과 TF의 의미**를 일관되게 이해하는 것이 목표다.

```text
base_footprint (고정 루트)
  └── base_link
      ├── fr_hip_link → fr_thigh_link → fr_calf_link → fr_foot
      ├── fl_hip_link → fl_thigh_link → fl_calf_link → fl_foot
      ├── rr_hip_link → rr_thigh_link → rr_calf_link → rr_foot
      └── rl_hip_link → rl_thigh_link → rl_calf_link → rl_foot
```

## 1. 준비: 장별 ROS overlay 분리

이전 Ch07/Ch08/Ch10/Ch11의 `install/setup.bash`를 source하지 않은 새 터미널에서 시작한다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
```

마지막 출력은 `Ch09/ros2_ws/install/...` 아래여야 한다. 그렇지 않으면 새 터미널에서 소싱을 다시 수행한다.

## 2. Xacro 확장 및 기구 구조 검사

```bash
PKG="$(ros2 pkg prefix --share my_quadruped_bot)"
xacro "$PKG/urdf/robot.urdf.xacro" > /tmp/ch09_robot.urdf
check_urdf /tmp/ch09_robot.urdf
python3 - <<'PY'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/ch09_robot.urdf').getroot()
joints = r.findall('joint')
revolute = [j for j in joints if j.get('type') == 'revolute']
fixed = [j for j in joints if j.get('type') == 'fixed']
links = r.findall('link')
mass = sum(float(l.find('inertial/mass').get('value')) for l in links if l.find('inertial/mass') is not None)
print('revolute=', len(revolute), 'fixed=', len(fixed), 'links=', len(links), 'total_mass_kg=', mass)
print('\n'.join(j.get('name') for j in revolute))
assert len(revolute) == 12
assert len(fixed) == 5
assert abs(mass - 12.0) < 1e-8
PY
```

**기대:** 12개 회전 관절, 5개 고정 관절, 18개 링크, 총질량 12.0kg. 이는 *구조 검증*이며 물리적 기립을 보증하지 않는다. `check_urdf`가 없다면 `liburdfdom-tools` 설치 여부를 확인한다.

## 3. 축·영점 비교 실습

`urdf/parts/leg.xacro`에서 `hip axis=1 0 0`, `thigh/calf axis=0 1 0`을 확인한다. 그러나 thigh와 calf의 `origin rpy`는 각각 `0 1.2 0`, `0 -2.4 0`이다. 따라서 관절 position 0이 기하학적으로 수직 다리라는 원고 설명을 검증 없이 사용하지 않는다.

선택 시각화는 `ros2 launch my_quadruped_bot display.launch.py`다. **현재 소스는 Ch08의 `my_robot_description` RViz 설정을 찾는 버그가 있다.** 이 명령이 실패해도 URDF 결함으로 단정하지 말고, 우선 `PKG/rviz/display.rviz` 존재 여부와 `display.launch.py`의 외부 패키지 참조를 확인한다. 원인을 기록한 뒤 별도 수정 PR에서 상대 패키지 참조를 정정한다.

## 4. 학습 과제와 기록

| 과제 | 증거 | 합격 기준 |
|---|---|---|
| 다리별 hip·thigh·calf 목록 | 전개된 URDF 관절 목록 | 4×3 정확히 12개 |
| 좌표축 정의 | FR/FL/RR/RL `origin xyz` 표 | 앞=+X, 왼쪽=+Y |
| 영점·회전부호 | RViz 슬라이더 캡처 또는 관절계산 | (+) 각도를 양 다리에서 각각 검증 |
| 질량 확인 | XML 파싱 출력 | 12.0 kg |
| TF 루트 | `ros2 run tf2_tools view_frames` (구동 시) | 루트는 `base_footprint` |

**다음 절:** [9.2 Xacro 재사용](LAB_9_2_GUIDE_KO.md). 오류를 확인하면 [9.1 리뷰](SECTION_9_1_REPORT_KO.md)에 제시한 수정 후보와 비교한다.
