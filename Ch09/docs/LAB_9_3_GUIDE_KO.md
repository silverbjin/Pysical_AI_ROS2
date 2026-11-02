# 9.3절 실습 가이드 — 관성 텐서·질량 중심·충돌 형상

> 첨부 원고 「9.3 시뮬레이션의 핵심: 관성과 충돌 속성」의 학습 목적을 유지하면서 **현행 Ch09 소스의 실제 명칭·경로**를 적용했다. 환경: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / Python 3.12 기준. 아래 명령은 검증 절차이며 이 세션에서 실제 실행되었다는 뜻이 아니다.

## 학습 목표

visual, collision, inertial의 서로 다른 목적과 중심 좌표를 구분하고 총질량·관성 양의 값을 검사한다.

## 1. 사전 준비와 워크스페이스

```bash
# 새 터미널: 다른 장의 install/setup.bash는 source하지 않음
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
PKG="$(ros2 pkg prefix --share my_quadruped_bot)"
```

`ros2 pkg prefix`가 **Ch09/ros2_ws**를 가리켜야 한다. 같은 이름의 Ch10/Ch11 패키지가 overlay에 남으면 지금 점검 중인 코드와 다른 버전이 실행된다. WSL2에서는 Gazebo GUI와 ROS 실행을 Ubuntu 터미널에서 수행한다.

## 2. URDF 전개와 질량·관성 자동 점검

```bash
xacro "$PKG/urdf/robot.urdf.xacro" > /tmp/ch09_9_3.urdf
python3 - <<'PY'
import xml.etree.ElementTree as ET
r=ET.parse('/tmp/ch09_9_3.urdf').getroot()
M=0.0
for link in r.findall('link'):
    iner=link.find('inertial')
    if iner is None: continue  # massless base_footprint
    m=float(iner.find('mass').get('value'))
    I=iner.find('inertia')
    d=[float(I.get(k)) for k in ('ixx','iyy','izz')]
    assert m>0 and all(x>0 for x in d), (link.get('name'),m,d)
    M+=m
    if 'thigh' in link.get('name') or 'calf' in link.get('name'):
        print(link.get('name'), 'inertial_origin=', iner.find('origin').get('xyz'),
              'collision_origin=',link.find('collision/origin').get('xyz'))
print('total_mass_kg=', M)
assert abs(M-12.0)<1e-8
PY
```

**기대:** 질량 12.0kg, 각 물리 링크의 대각 관성값 양수, calf·thigh의 관성/충돌 원점 차이가 출력됨. 양수 대각 성분만 검사하는 것은 3×3 관성행렬의 완전한 양의 정부호 검증을 대체하지 않는다.

## 3. Gazebo 물리 관찰

```bash
ros2 launch my_quadruped_bot simulation.launch.py
```

새 터미널에서 Ch09 overlay source 후 `ros2 topic echo /joint_states --once`로 관절 상태가 실제 수신되는지 확인한다. 로봇이 낙하한 뒤에도 바닥 평면과 접촉하는지, 링크가 튀거나 관절이 관통하는지 눈으로 기록한다. 이 절에서는 **기립 성공까지 요구하지 않는다**(9.6절에서 제어).

## 4. 비교 과제

한 가지 파라미터만 바꾸어 관성의 영향을 비교한다. 예를 들어 임시 복사본에서 calf_mass를 0.50→0.60 kg로 올리고 `xacro` 출력의 inertia 값이 계산식대로 증가하는지 기록한다. 값은 원복한다. 실제 접촉 안정성 비교는 동일 초기조건·PID·time step으로 반복해야 하며 결과를 예측하거나 만들어 쓰지 않는다.

## 6. 학습 과제·증거 기록

| 실습 과제 | 제출 Evidence |
|---|---|
| 1. 전개된 URDF 전체 질량은 몇 kg인가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 2. thigh와 calf의 충돌 중심과 관성 중심은 각각 얼마만큼 다른가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 3. 관성 매크로의 축과 원통의 길이축은 일치하는가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 4. 자유낙하 후 로봇이 지면에 안착하는가(물리 실행 환경에서만 판정)? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |

**수용 기준:** 형상별 inertia가 양수이고 합계 12.0kg이며, 중심 좌표 차이를 설명할 수 있어야 한다. 안정성은 실제 Gazebo 재현으로만 판정한다.

## 7. 흔한 오류와 교정 포인트

원고의 '물리적으로 완벽하다'는 설명은 실제 코드의 질량중심·충돌중심 불일치와 검증 부재를 고려하면 과한 단정이다.

오류를 만나면 재현 명령과 `ros2 pkg prefix my_quadruped_bot` 출력, `ros2 topic list` 결과, 사용 중인 ROS/Gazebo 버전을 함께 남긴다. 다른 장의 동명 패키지 overlay를 먼저 배제한다. 필요한 코드를 검토한 다음 실제 환경에서 다시 검증할 때까지 **실행 완료로 판정하지 않는다.**

관련: [코드 리뷰](SECTION_9_3_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 교육 문서 형식](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs).
