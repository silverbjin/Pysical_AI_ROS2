# 9.8절 실습 가이드 — 통합 QA·트러블슈팅·다음 장 인계

> 이 문서는 첨부 원고의 학습 단계와 실제 저장소 코드를 맞춘 **재현 가이드**다. 권장: ROS 2 Jazzy, Gazebo Harmonic, Ubuntu 24.04/WSL2. 실행 예시는 현재 세션에서 물리 시뮬레이터로 성공 검증된 명령이 아니다.

## 목표

정적 QA와 실제 Gazebo 런타임 QA를 구분하여 Ch10으로 넘어가기 전 명명·좌표계·관성·접촉·TF·제어 안정성을 증거로 남긴다.

## 1. Ch09 단독 환경 설치·검사

```bash
# 기존 Ch07/Ch08/Ch10/Ch11 설치물을 source하지 않은 새로운 터미널
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
PKG="$(ros2 pkg prefix --share my_quadruped_bot)"
```

패키지 prefix는 **Ch09**의 `install`이어야 한다. 다른 장의 `my_quadruped_bot`이 조회되면 새 터미널에서 source를 다시 수행한다. `package.xml`의 실행 의존성 선언은 불충분하므로 `rosdep`만으로 모든 프로그램이 설치된다고 가정하지 말고 `ros2 pkg executables ros_gz_sim`, `ros2 pkg executables ros_gz_bridge` 등을 점검한다.

## 2. 오프라인 정적 검사 (Gazebo 없이도 가능)

```bash
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
p=Path('src/my_quadruped_bot')
for f in sorted(p.rglob('*.xacro'))+sorted(p.rglob('*.xml'))+[p/'worlds/empty_world.sdf']:
    ET.parse(f)
    print('XML OK', f)
PY
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot src/my_quadruped_bot/launch
python3 - <<'PY'
import yaml
from pathlib import Path
p=Path('src/my_quadruped_bot/config/ros_gz_bridge.yaml')
a=yaml.safe_load(p.read_text())
cmd=[x for x in a if x.get('direction')=='ROS_TO_GZ']
assert len(cmd)==12
assert len({x['ros_topic_name'] for x in cmd})==12
assert len({x['gz_topic_name'] for x in cmd})==12
print('bridge 12 command pairs OK')
PY
xacro "$(ros2 pkg prefix --share my_quadruped_bot)/urdf/robot.urdf.xacro" > /tmp/ch09_final.urdf
check_urdf /tmp/ch09_final.urdf
colcon test --packages-select my_quadruped_bot --event-handlers console_direct+
colcon test-result --verbose
```

`yaml` import가 없다면 `python3-yaml` 설치 여부를 확인한다. **이 명령은 실행 지침**이며 이 PR에서 테스트 결과를 실제 수집한 것이 아니다. `compileall`은 Python 구문 검사이지 import 성공이나 Gazebo 정상 기동을 보장하지 않는다.

## 3. 물리·ROS 통합 스모크

```bash
ros2 launch my_quadruped_bot simulation.launch.py
```

새 터미널에서:
```bash
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
ros2 param get /robot_state_publisher use_sim_time
ros2 run tf2_tools view_frames
ros2 topic list | grep cmd_pos | wc -l
```

**기준:** 시간 동기화 true, 12개 관절 명령 입력, /joint_states 갱신, 로봇 스폰 및 단일 TF 트리. 현재 코드에는 시간 동기화 누락이 있으므로 일부 항목은 FAIL 가능성이 있으며 이는 후속 코드 수정 사항이다.

## 4. 기립·제어·접촉 QA

```bash
ros2 run my_quadruped_bot stand_up
```

20초 이상의 동일 시뮬레이션 구간을 잡아 몸체 높이/기울기/발 슬립/관절 오차를 로그로 기록한다. 명령 퍼블리셔 경합을 막기 위해 `stand_up`과 `single_leg_mover`를 동시에 실행하지 않는다. 한 다리 이동을 검증할 때는 9.7의 명령 소유권 문제를 해결한 후 반복한다.

| 항목 | 관찰·증거 | 현재 정적 판정 |
|---|---|---|
| 질량 합계 | URDF inertial/mass | 12.0 kg 기대(미실행) |
| 좌표축·관절영점 | Xacro rpy, 진폭 부호 | 원고·코드 불일치 확인 |
| TF 루트 | view_frames | base_footprint 기대(미실행) |
| 시뮬레이션 시간 | ros2 param get | simulation 런치에 누락 확인 |
| 발 마찰 | gz sdf -p 및 contact | 실제 반영 미확인 |
| 기립 안정성 | 자세·관절 데이터 | NOT_RUN |
| 단일 다리 sine 추종 | joint states와 cmd_pos | NOT_RUN |

## 5. 트러블슈팅 순서

1. **패키지 불일치:** `ros2 pkg prefix my_quadruped_bot`가 Ch09인지 확인한다.
2. **RViz 실행 실패:** `display.launch.py`가 `my_robot_description`을 조회하는지 확인한다.
3. **로봇이 안 움직임:** ROS `cmd_pos`에 `/0/`를 넣지 않았는지, 브리지 매핑과 publisher 수를 검사한다.
4. **TF 지연:** `use_sim_time`과 `/clock`을 확인하고 동일 TF 발행자의 중복 여부도 검사한다.
5. **로봇 폭발/낙상:** 지면 collision, inertial, joint 원점, 출력 한계, 접촉 마찰, P/I/D를 순서대로 확인한다. 눈에 띄는 현상만으로 원인을 확정하지 않는다.

## 6. 과제 및 제출 Evidence

| 확인할 질문 | 기록할 결과 |
|---|---|
| 1. XML/YAML·Python 구문 검사 결과와 colcon test 결과를 각각 보존했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 2. 로봇 총질량·TF·브리지 12개가 실제로 확인되었는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 3. Gazebo 20초 기립 중 자세 오차와 미끄러짐을 기록했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |
| 4. Ch10으로 인계할 관절 영점·이름·부호·소유권 계약을 문서화했는가? | 명령·원본 콘솔 로그·ROS 토픽 출력 및 화면 캡처, PASS/FAIL 사유 |

**Acceptance Criteria:** 정적 규칙과 실제 물리 성공을 독립 PASS/FAIL 판정하고 근거 로그를 확보해야 다음 장의 보행 코드에 연결한다. 현재 이 PR만으로 Ch09 전체 기능을 PASS 판정하지 않는다.

## 7. 원고 대비 유의점

원고의 '마무리/기립 성공' 서술은 테스트 실제 증거 확보 후에만 승인할 수 있다. 현행 루트는 base_footprint이고, WSL2 오버레이 충돌도 재현성 위험이다.

연습 환경에서 실제 Gazebo 물리·ROS 연결을 실행하지 못했다면 모든 런타임 지표를 **NOT_RUN**으로 남긴다. 섣부른 수치 추정이나 과거 장의 증거 재사용은 금지한다.

[리뷰 보고서](SECTION_9_8_REPORT_KO.md) · [Ch09 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09) · [Ch12 문서 기준](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch12/docs)
