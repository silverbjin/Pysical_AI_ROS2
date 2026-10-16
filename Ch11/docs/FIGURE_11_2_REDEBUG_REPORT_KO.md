# Figure 11-2 기립 불안정 재발 디버깅 보고서

검증일: 2026-10-17 (KST). 시작 시점 HEAD: `031774e8` (`code 11.2.4`).

## 원인과 재현

이전 수정 커밋 `b718ec20`과 현재 코드를 비교한 결과, 최신 커밋에서 활성 `trot_controllerFSM.py`가 수정 전 코드로 되돌아갔다. 관성이 복구된 URDF와 기립 회귀 테스트는 그대로 남았지만, FSM의 다리 길이·고관절 오프셋·관절 회전 매핑 및 shutdown 보호가 제거됐다.

같은 디렉터리에 추가된 `trot_controllerFSM copy.py`는 `b718ec20`의 정상 FSM과 바이트 단위로 일치했다. 그러나 `setup.py`의 실행 항목은 `my_quadruped_bot.trot_controllerFSM:main`을 사용하므로 복사본의 수정은 실행에 반영되지 않는다. Git 기록상 최신 커밋의 파일 교체가 원인이며, 구체적으로 어떤 병합 명령이나 편집 과정에서 교체됐는지는 기록만으로 단정하지 않는다.

```bash
git diff b718ec20..031774e8 -- \
  Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_controllerFSM.py
source /opt/ros/jazzy/setup.bash
python3 -m unittest discover -s Ch11/tests -v
bash Ch11/scripts/run_figure_11_2.sh
```

수정 전 전체 34개 테스트 중 `test_standing_commands_reach_targets_in_actual_urdf`가 실패했다. 준비 높이에서 허벅지 명령 `−1.1110665 rad`가 URDF 하한 `−1.0 rad`보다 작았다. 실제 실행의 `/simulation/odom`에서도 시뮬레이션 시각 12.24초에 몸체 높이 `0.133371 m`, 월드 수직축 대비 기울기 `168.486°`를 확인했다. 단순한 화면 흔들림이 아니라 로봇이 뒤집힌 상태였다.

## 수정

1. 활성 FSM 파일만 `b718ec20`의 검증된 버전으로 복구했다. 최신 IMU 처리 코드와 다른 파일 변경은 유지했다.
   - 허벅지·종아리 길이: 0.20 m → 실제 URDF와 같은 0.25 m.
   - 몸체→고관절 Y 오프셋: ±0.15 m → ±0.10 m. 허벅지 연결부의 추가 ±0.05 m는 IK에서 처리한다.
   - 관절각 매핑: 기하학적 IK 결과를 URDF의 초기 회전과 무릎 방향에 맞춰 `[q1, −q2−1.2, −q3+2.4]`로 변환.
   - ROS context가 이미 종료된 경우 shutdown과 rosout 로그를 다시 호출하지 않도록 보호 복구.
2. `run_figure_11_2.sh`에서 빌드와 overlay 확인 후 기존 `test_figure_11_2.py`를 실행하도록 했다. 모델·기구학 검사에 실패하면 `set -e`에 의해 Gazebo 시작 전에 중단된다.

실행 전 검사는 실제 수정 전 FSM을 둔 상태에서 먼저 검증했다. 빌드는 성공했지만 8개 그림 검사 중 기립 검사가 실패했고 스크립트는 종료 코드 1로 끝났다. 이 실행에서는 Gazebo·RViz가 시작되지 않았다. FSM 복구 후에는 8개 검사 통과 뒤 정상 launch로 진행했다.

## 검증 기준

Ubuntu 24.04 / WSL2 / ROS 2 Jazzy / Gazebo Harmonic 환경에서 요청한 기본 명령을 사용한다. 각 회차 종료 후 새 Gazebo와 ROS 노드를 시작하여 초기화부터 다시 검증한다. 속도 명령은 발행하지 않는다.

관측 프로브는 필터 출력만 보고 판단하지 않고 `/simulation/odom`의 실제 모델 관측값을 사용한다. 시뮬레이션 8초 이후부터 최소 30초 동안 다음 조건을 검사한다.

- 몸체 높이 0.20~0.30 m 유지.
- 몸체의 수직축과 월드 수직축 사이 기울기 5° 미만 유지. quaternion으로 계산해 뒤집힘도 검출한다.
- 실제 오도메트리, EKF 오도메트리, IMU, IMU 표시 자세, 관절 상태 및 LiDAR를 모두 수신하고 마지막 수신이 실제 시간 기준 5초 이내일 것.
- LiDAR 유효 거리 반환 존재, `odom → base_link`, `odom → lidar_link` TF 조회 성공.

## 검증 결과

전체 Ch11 테스트는 **34개 모두 통과**, skip 0개다. Bash 문법 검사 및 변경 파일의 `git diff --check`도 통과했다. 반복 실행 수치는 아래 증거의 JSON에 기록한다.

| 회차 | 관찰한 시뮬레이션 시각 | 몸체 높이 범위 | 최대 기울기 | 수평 이동 | 결과 |
|---|---|---|---|---|---|
| 1 | 8.024~38.046 s | 0.252950~0.253945 m | 0.988° | 1.113 mm | PASS |
| 2 | 8.024~38.046 s | 0.249113~0.250151 m | 1.143° | 1.136 mm | PASS |
| 3 | 8.024~38.046 s | 0.247983~0.249039 m | 1.268° | 1.149 mm | PASS |

세 회차 모두 LiDAR 360개 거리값 전부 유효했고 센서·자세·TF 검사도 통과했다. 각 회차에서 1,119개의 실제 모델 오도메트리 메시지를 수신했다.

초기 낙하·기립 전이 구간(시뮬레이션 0~8초)은 위 안정성 수치에서 제외했다. 검증 범위는 기본 명령의 무속도 기립 및 센서 데이터 경로이며, 보행·외란 회복·실물 로봇 검증을 뜻하지 않는다. GUI 창 시작은 로그로 확인하며, 출판용 화면 구성의 육안 검증은 별도다.

## 남은 경고와 종료 관찰

기립 관측 중에는 `gz_frame_id` 확장 요소 경고 및 IMU의 시각 일치 TF 대기 경고가 남았다. 실제 센서·자세·TF 수신은 위 프로브로 별도 확인했다.

첫 번째 실행은 FSM·IMU 표시·오도메트리 노드가 정상 종료했다. 두 번째 실행에서는 **관측 완료 후 Ctrl+C를 보냈을 때** `imu_pose_viz`와 `sim_odometry`가 rclpy 메시지 수신 내부의 `RuntimeError: Unable to convert call argument '0' to Python object`로 종료했다. 이전 보고서에서도 종료 중 유사 현상이 관찰됐다. 이번 기립 회귀와 구분하여 남은 종료 문제로 기록하며, 이 오류까지 해결됐다고 주장하지 않는다. 복구한 FSM 자체는 정상 종료했다.

Gazebo 실행 래퍼는 Ctrl+C에 의해 종료 코드 −2로 기록된다. 각 재실행 전 앞선 Gazebo·RViz·launch 프로세스가 남지 않았는지 확인했다.

## 재검증 및 증거

```bash
bash Ch11/scripts/run_figure_11_2.sh
```

다른 터미널에서 다음과 같이 읽기 전용 관측을 반복할 수 있다.

```bash
source /opt/ros/jazzy/setup.bash
python3 Ch11/evidence/figure_11_2_redebug_20261017/repeat_probe.py \
  --output /tmp/figure_11_2_stability.json
```

각 회차 전에 앞선 실행을 Ctrl+C로 종료한다. 프로브는 속도 명령을 발행하지 않는다. 로그와 검증용 프로브는 [증거 디렉터리](../evidence/figure_11_2_redebug_20261017/)에 보관했다.

- `regression_red.log`, `regression_green.log`: 전체 회귀 검사 수정 전후.
- `before_launch.log`, `before_odom.log`: 수정 전 실제 실행과 뒤집힌 자세.
- `preflight_red.log`: 수정 전 기립 오류에 대한 실행 전 차단 검증.
- `run1.log`~`run3.log`, `run1.json`~`run3.json`: 각 회차 실행 및 안정성 관측.
- `repeat_probe.py`: 실제 모델 자세·센서·TF를 관측한 프로브 원본.

커밋·병합·브랜치 변경은 수행하지 않았다.
