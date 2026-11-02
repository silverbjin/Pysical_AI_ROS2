# 4.1절 실습 가이드: 좌표계·TF2 최소 실험

**목표:** 프레임 이름, 부모/자식, 위치(m), 회전 quaternion, TF 조회 방향을 눈으로 검증한다. 이 절은 개념+표준 CLI 실습이며 독립 파이썬 소스를 요구하지 않는다.

## 1. 실습 환경

Ubuntu 24.04 + ROS 2 Jazzy + GUI가 가능한 RViz2를 기준으로 한다. 아래 명령은 새로운 터미널마다 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install ros-jazzy-tf2-ros ros-jazzy-tf2-tools ros-jazzy-rviz2
ros2 pkg prefix tf2_ros
```

설치가 이미 되어 있다면 apt 단계는 생략한다. 이전 장 워크스페이스의 `AMENT_PREFIX_PATH` 충돌을 피하려면 새 셸에서 시작한다.

## 2. 가설 → 실행 → 확인

**가설:** world 기준 base_link의 원점이 `(1.0, 0.0, 0.5)`이고 회전이 없다면, `tf2_echo world base_link`는 같은 병진과 quaternion `(0,0,0,1)`을 알려준다.

터미널 A (계속 실행):

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 1.0 --y 0.0 --z 0.5 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id world --child-frame-id base_link
```

터미널 B:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list -t
ros2 topic info /tf_static -v
ros2 run tf2_ros tf2_echo world base_link
```

**예상:** `/tf_static` 토픽과 변환이 존재하며 병진이 (1,0,0.5)에 가깝다. 메시지의 시간·출력 형식은 실제 실행 환경에 따라 다르다. 오류가 발생하면 두 셸의 `ROS_DOMAIN_ID`를 먼저 일치시킨다.

## 3. RViz와 TF 트리

```bash
rviz2
# 별도 터미널
ros2 run tf2_tools view_frames
```

RViz의 Global Options → Fixed Frame: `world`; Displays → Add → TF. `world→base_link` 축이 1.0m 앞, 0.5m 위에 나타나는지 확인한다. `view_frames`가 생성한 PDF의 저장 위치는 **명령을 실행한 현재 디렉터리**다.

## 4. 왜 중요한가: 역변환 비교

```bash
ros2 run tf2_ros tf2_echo base_link world
```

회전이 0이면 역방향 병진은 `(-1.0, 0.0, -0.5)`에 가깝다. 회전이 있으면 단순 부호 반전으로 역변환을 계산할 수 없다는 점이 핵심이다. 단일 자식에 부모를 추가해 충돌시키는 실험은 기존 발행자를 종료한 뒤 진행한다.

## 5. 체크리스트·기록

| 항목 | 합격 기준 |
|---|---|
| 프레임 | `world→base_link` 방향 정확 |
| 위치 | m 단위 (1.0, 0.0, 0.5) |
| 회전 | `w≈1`, `x=y=z≈0` |
| 내구성 | `/tf_static`에서 transient local QoS 확인 |
| TF 트리 | `view_frames`에서 단일 부모 |

실습 기록: 명령어/실행 OS/ROS 배포판/`tf2_echo` 출력/TF 트리 화면/정상 종료 여부를 기록한다. 새 변환을 실습할 때는 기존 publisher를 Ctrl+C로 종료한다.

**추가 질문:** `map→odom→base_link`를 하나로 합치면 왜 전역 위치 보정 시 급격한 점프를 피할 수 없는가?

참고: [4.1 보고서](SECTION_4_1_REPORT_KO.md) · [ROS REP-105](https://www.ros.org/reps/rep-0105.html).
