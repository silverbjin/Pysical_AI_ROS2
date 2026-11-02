# 9.2절 실습 가이드 — Xacro 매크로와 4개 다리 자동 생성

> 첨부 원고 「9.2 효율적인 모델링을 위한 Xacro 매크로 설계」의 학습 목적을 유지하면서 **현행 Ch09 소스의 실제 명칭·경로**를 적용했다. 환경: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / Python 3.12 기준. 아래 명령은 검증 절차이며 이 세션에서 실제 실행되었다는 뜻이 아니다.

## 학습 목표

전역 파라미터 → 다리 매크로 → 4회 호출 구조를 추적하고, 설치된 Xacro와 RViz의 자산 경로를 검증한다.

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

## 2. Xacro 전개와 반복 매크로 검수

```bash
xacro "$PKG/urdf/robot.urdf.xacro" > /tmp/ch09_9_2.urdf
check_urdf /tmp/ch09_9_2.urdf
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
p=Path('/tmp/ch09_9_2.urdf')
r=ET.parse(p).getroot()
names=[j.get('name') for j in r.findall('joint')]
assert len(names)==len(set(names))
for leg in ('fr','fl','rr','rl'):
    for joint in ('hip','thigh','calf'):
        assert f'{leg}_{joint}_joint' in names
print('PASS: 12 distinct articulated joint names')
PY
```

`check_urdf` 명령이 없다면 `liburdfdom-tools` 설치를 확인한다. 각 링크의 `visual`, `collision`, `inertial`은 전개된 XML의 실제 내용을 보고 확인한다.

## 3. 설치 자산과 RViz 확인

```bash
find "$PKG/urdf" -type f | sort
test -f "$PKG/rviz/display.rviz" && echo "RViz asset installed"
ros2 launch my_quadruped_bot display.launch.py
```

**주의:** 마지막 명령은 현재 코드의 `my_robot_description` 잘못된 의존성 때문에 실패할 수 있다. 이것은 알려진 정적 리뷰 이슈다. `display.launch.py`에서 `package_name = 'my_robot_description'` 행을 확인하고, 실행 실패 로그를 증거로 남긴다. 해결 전까지 성공이라고 기록하지 않는다.

## 4. 파라미터 변경 실험

별도 복사본에서 `thigh_length`를 0.25 → 0.27m로 임시 변경해 전개한 XML의 4개 thigh 형상이 모두 바뀌는지 확인한다. 원본은 복원하고 `git diff --check`로 원치 않는 변경이 없는지 검증한다. 힘·접촉·IK 값까지 그대로 유효하다는 뜻은 아니다.

## 6. 학습 과제·증거 기록

| 실습 과제 | 제출 Evidence |
|---|---|
| 1. 4개의 다리에 총 12개 유일한 회전 관절이 전개되는가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 2. robot_properties.xacro 한 곳의 변수 변경이 4개 다리에 모두 반영되는가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |
| 3. Ch09 단독 overlay에서 display.launch.py가 작동하는가? 실패한다면 정확히 어떤 패키지 조회가 원인인가? | 실행 명령, 콘솔 출력 또는 스크린샷, PASS/FAIL과 이유 |

**수용 기준:** Xacro 확장, 링크/조인트 고유성, 설치된 파일 위치가 확인되어야 한다. RViz 실행은 현재 교차 패키지 참조 문제를 분리해 판정한다.

## 7. 흔한 오류와 교정 포인트

원고의 예시 `xacro ~/ros2_ws/src/my_bot/...`는 실제 Ch09 경로가 아니다. 실제 패키지 share 경로를 사용한다.

오류를 만나면 재현 명령과 `ros2 pkg prefix my_quadruped_bot` 출력, `ros2 topic list` 결과, 사용 중인 ROS/Gazebo 버전을 함께 남긴다. 다른 장의 동명 패키지 overlay를 먼저 배제한다. 필요한 코드를 검토한 다음 실제 환경에서 다시 검증할 때까지 **실행 완료로 판정하지 않는다.**

관련: [코드 리뷰](SECTION_9_2_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 교육 문서 형식](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs).
