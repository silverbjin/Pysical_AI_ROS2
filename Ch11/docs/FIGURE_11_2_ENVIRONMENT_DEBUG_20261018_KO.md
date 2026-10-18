# Figure 11-2 기립 이상 재발: 환경 충돌 디버깅 보고서

검증일: 2026-10-18 (KST). 저장소: `/home/jinho/Pysical_AI_book`. 시작 HEAD: `0b198923ac5cad8843ac843d7e4c1b373ff902f0`. 작업 시작 시 Git 작업 트리는 깨끗했다.

## 결론

이번 재발 원인은 **기립 코드의 재손실이 아니라 다른 시뮬레이터와 Gazebo Transport 통신 공간을 공유한 것**이다. 실제 기본 명령으로 기립 이상과 센서 부재를 재현했다. 코드 수정 없이 `GZ_PARTITION`만 바꾼 비교 실험에서 정상으로 돌아왔으며, 실행 스크립트에 같은 격리를 기본 적용한 후 원래 명령으로 다시 검증했다.

최종 실행은 시뮬레이션 30.022초 동안 높이 0.247993~0.249050 m, 최대 기울기 1.265°로 이전 정상 evidence 범위와 일치했다. IMU·스캔·표시 자세·관절·오도메트리·TF 검사와 전체 테스트 **40개가 모두 통과**했다. 다른 Ch13 시뮬레이터를 종료하지 않고 검증했다.

## 이전 evidence와 무엇이 다른가

| 항목 | 2026-10-17 정상 evidence | 2026-10-18 수정 전 | 격리 적용 후 기본 명령 |
|---|---|---|---|
| 활성 FSM | 기립 수정 버전 | 정상 버전과 SHA-256 일치 | 동일 코드 유지 |
| 실제 실행 검사 | 3회 PASS | 기립 이상·센서 부재 재현 | PASS |
| 관찰 구간 | 각 8.024~38.046 s | 시계·오도메트리 6775~6778 s | 8.024~38.046 s |
| 몸체 높이 | 0.247983~0.253945 m | 수신한 모델 z≈0.368706 m | 0.247993~0.249050 m |
| 기울기 | 최대 1.268° | 수신한 모델 약 81.337° | 최대 1.265° |
| IMU / 스캔 / 표시 자세 | 모두 수신 | 12초 관측 중 모두 0개 | 3805 / 381 / 1100개 |
| LiDAR 유효 거리 | 360/360 | 메시지 없음 | 360/360 |
| TF | 정상 | 센서 경로 검증 불가 | 두 경로 조회 성공 |

이전 기준은 `figure_11_2_redebug_20261017/run1.json`~`run3.json`이다. 당시 별도 경고 검증 `figure_11_2_warnings_20261017/probe_ready.json`에서도 스캔 45개가 측정 시각의 TF로 변환됐다. 비교 수치와 원본 경로는 새 evidence의 `comparison.json`에 함께 저장했다.

수정 전 수신한 오도메트리는 의도한 Figure 월드의 데이터라고 신뢰할 수 없었다. 다른 월드에 같은 이름의 로봇이 존재했고, ROS 브리지가 공유 Gazebo 토픽에 연결돼 있었다. 따라서 81°라는 값을 정상 Ch11 월드에서 동일 제어기가 항상 실패한다는 증거로 해석하지 않았다.

## 조사와 원인 증거

### 1. 지난번 기립 수정은 보존돼 있었다

`trot_controllerFSM.py`는 이전 정상 커밋 `b718ec20`의 파일과 바이트 단위로 일치했다. 양쪽 SHA-256은 다음과 같다.

```text
2d78cb6b57f92feb9f236186e58a0fb01af7b2ee593e03343383af1a2c281978
```

0.25 m 다리 길이, ±0.10 m 고관절 위치, `[q1, −q2−1.2, −q3+2.4]` 관절 회전 매핑이 유지됐다. 기존 38개 테스트도 수정 전부터 모두 통과했다. 이전에 있었던 병합 중 FSM 되돌림과는 다른 원인이다.

### 2. 다른 장의 Gazebo가 기본 통신 공간에서 실행 중이었다

기존 Ch13 프로세스는 다음과 같은 환경이었다.

| 프로세스 | ROS domain | Gazebo partition |
|---|---|---|
| 기존 Ch13 Gazebo (PID 156634) | 131 | 미지정, 기본 공간 |
| 수정 전 Ch11 | 0 | 미지정, 기본 공간 |

ROS domain이 달라도 Gazebo Transport에는 적용되지 않는다. Gazebo partition의 기본값은 호스트명과 사용자명으로 만들어지므로 같은 사용자로 실행한 두 시뮬레이터가 토픽·서비스를 공유했다. [Gazebo Transport 13 공식 설명](https://gazebosim.org/api/transport/13/classgz_1_1transport_1_1NodeOptions.html)

공유 공간에는 `/world/section_13_2/*`와 `/world/sensor_figure_world/*` 서비스가 함께 보였다. Ch13의 실제 scene graph에는 `integrated_robot`뿐 아니라 `my_quadruped` 모델도 나타났다. `create` 노드가 `Entity creation successful`을 출력했다고 해서 Figure 월드에 생성됐다고 보장할 수 없는 상황이었다. 현재 launch의 spawn은 명시적인 world 선택 없이 `/gazebo/worlds`를 조회한다.

Gazebo의 전역 `/clock`은 기존 시뮬레이터가 제공하고 있었다. 새 Gazebo가 기존 `/clock` publisher를 발견하면 자기 시계는 `/world/<worldname>/clock`에만 발행할 수 있다. 그런데 Ch11 브리지는 전역 `/clock`을 구독하므로 다른 시뮬레이터의 시계를 ROS로 가져왔다. [ros_gz_bridge 공식 문서의 Clock 주의사항](https://index.ros.org/p/ros_gz_bridge/)

기본 실행 직후 `/clock`은 약 6771.564초, `/simulation/odom`은 약 6772.148초였다. 12초 별도 관측에서는 clock 1284개와 오도메트리 75개만 수신하고 IMU·스캔·표시 자세는 받지 못했다. 시계 점프는 관측되지 않았으므로, 임의로 계속 왕복하는 시계가 아니라 **잘못된 출처에 일관되게 연결된 상태**로 해석했다.

### 3. 환경 한 가지를 바꾼 실험으로 인과관계를 확인했다

기존 Ch13은 그대로 둔 채 Ch11만 종료하고 다음을 실행했다.

```bash
GZ_PARTITION=ch11_ab_20261018 bash Ch11/scripts/run_figure_11_2.sh
```

코드 수정 없이 로봇이 정상 생성되고 센서·TF가 복구됐다. 같은 이전 프로브로 30.022초를 관찰한 결과 높이 0.247961~0.249016 m, 최대 기울기 1.254°, 수평 이동 1.148 mm로 PASS였다. 제어기 재튜닝 없이 환경 격리만으로 결과가 바뀌었다.

## 수정과 재발 방지

`run_figure_11_2.sh`에 다음 처리를 추가했다.

```bash
export GZ_PARTITION="${GZ_PARTITION:-ch11_figure_11_2_${UID}_$$}"
printf 'ROS_DOMAIN_ID=%s\nGZ_PARTITION=%s\n' "${ROS_DOMAIN_ID:-0}" "$GZ_PARTITION"
```

기본 실행마다 독립 Gazebo partition을 생성하고, Gazebo 서버·GUI·spawn·ROS 브리지에 동일하게 상속한다. 명시적으로 지정한 사용자 partition은 유지한다. `ROS_DOMAIN_ID`는 바꾸지 않아 기존 ROS 진단 터미널 사용법을 유지했다.

실제 프로세스의 `/proc/<PID>/environ`을 읽어 Gazebo·브리지·RViz가 모두 `ch11_figure_11_2_1000_218959`를 상속한 것을 확인했다. 기존 Ch13은 계속 기본 공간과 ROS domain 131에 남아 있었다. 로봇 모델·IK·PID 게인은 변경하지 않았다.

지난번에도 문서에는 격리 권고가 있었지만, 실행 스크립트가 자동 적용하지 않았고 이전 정상 실행은 다른 시뮬레이터와 공유하는 조건을 시험하지 않았다. 이 실행 환경 의존성이 기본 동작에 남아 있었던 것이 재발 이유다. 이번에는 **다른 장이 실제로 실행 중인 조건**에서 기본 명령을 검증했다.

## 최종 검증

원래 요청 명령을 추가 환경변수 없이 실행했다.

```bash
bash Ch11/scripts/run_figure_11_2.sh
```

- 두 패키지 빌드 및 기존 그림 검사 8개 통과.
- 이전과 동일한 읽기 전용 프로브로 시뮬레이션 8.024~38.046초 관찰 PASS.
- 최대 기울기 1.265°, 수평 이동 1.149 mm. IMU 3805개, 스캔 381개, 표시 자세 1100개, 실제 모델 오도메트리 1119개 수신.
- 스캔은 360/360개가 유효하고 약 1.494~4.859 m 범위였다. `odom → base_link`, `odom → lidar_link` 조회 성공.
- 실제 실행 스크립트를 `--show-args`로 실행하는 회귀 검사에서 자동 partition의 실행별 고유성과 사용자 지정 partition 보존을 확인. 수정 전 2 FAIL → 수정 후 PASS.
- 전체 `python3 -m unittest discover -s Ch11/tests -v`: **40 PASS, skip 0**. Bash 문법 검사 및 `git diff --check` 통과.

초기 낙하·기립 전이 0~8초는 안정성 수치에서 제외했다. 기본 기립 및 센서·TF 데이터 경로를 검증했으며, 보행·실물 로봇·출판용 화면 육안 검증을 완료했다고 주장하지 않는다.

## 별도로 확인한 사항과 한계

- `evidence/wsl2-20261018-000045/result.json`은 `pytest` 미설치로 **BLOCKED / runtime_executed=false**였다. 이는 별도 WSL2 통합 검증 스크립트의 의존성 검사 실패이고, 기본 `run_figure_11_2.sh`의 기립 이상 원인과는 다르다. 이번 보고서는 실제 수행한 기본 명령과 unittest·관측 프로브 결과를 사용한다. pytest를 임의로 설치하거나 BLOCKED를 PASS로 덮어쓰지 않았다.
- 시작 직후 IMU 샘플 만료 경고 및 시각 0.002초 스캔 폐기 INFO가 각각 관찰됐다. 초기화 후 센서 수신이 이어졌으며, 이를 이번 재발 원인으로 오인하지 않았다.
- 종료 중 rosout context 무효 경고가 한 번 있었다. 기립 관찰이 끝난 뒤의 현상이며 종료 예외 전체를 해결했다고 주장하지 않는다.
- 별도 진단 스크립트의 마지막 `tf2_echo odom lidar_link`는 시뮬레이터 종료와 겹쳐 TF를 받지 못한 채 timeout 124로 끝났다. 실행 중인 전체 프로브의 두 TF 검사 PASS와 구분했다. 종료 시 Gazebo 래퍼는 SIGINT 후 5초에 SIGTERM으로 종료됐으며, 이후 이번 Ch11 프로세스가 남지 않은 것을 확인했다.
- Gazebo partition만으로 ROS 토픽 충돌까지 분리되지는 않는다. Ch11 두 개를 병렬 실행하려면 서로 다른 ROS domain도 지정해야 한다. 사용자 지정 `GZ_PARTITION`이 다른 장과 같으면 다시 공유할 수 있으므로, 의도하지 않은 값은 `unset GZ_PARTITION` 후 실행한다.
- `ros2 launch ...`를 직접 실행하면 이 Bash 스크립트의 자동 격리를 거치지 않는다. 직접 실행할 때는 먼저 고유한 `GZ_PARTITION`을 export하고 관련 Gazebo 도구도 같은 값을 사용해야 한다.

## 증거 및 산출물

[증거 디렉터리](../evidence/figure_11_2_environment_20261018/)에는 기존 정상 evidence를 보존한 상태로 다음을 추가했다.

- `code_comparison.json`, `process_environment.json`: 소스 동일성 및 실제 프로세스 환경.
- `initial_launch.log`, `initial_metrics.json`, `initial_clock.log`, `initial_odom.log`: 수정 전 실제 재현.
- `external_scene.txt`, `external_*_publisher.txt`: 공유 공간에서 관찰한 외부 월드·토픽 출처.
- `isolated_launch.log`, `isolated_runtime.json`: 코드 수정 전 환경만 바꾼 비교 실험.
- `fixed_launch.log`, `fixed_runtime.json`, `fixed_diagnostics.log`: 수정한 기본 명령 실행과 수신 진단.
- `tests_before.log`, `environment_red.log`, `tests_after.log`: 기존 38 PASS, 새 회귀 검사 2 FAIL, 최종 40 PASS.
- `comparison.json`: 이전 정상·수정 전·격리 실험·최종 실행의 수치 비교.

커밋·병합·브랜치 변경은 수행하지 않았다. 기존 Ch13 실행을 종료하지 않았다.
