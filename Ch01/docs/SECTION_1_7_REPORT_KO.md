# SECTION 1.7 — Twist 발행과 ROS 2 의존성 코드 리뷰 보고서

- 작성: 2026-10-20 KST / 저장소 `silverbjin/Pysical_AI_ROS2`
- 기준 `main`: `f5aed1d250563efc298e717559497db3b4f205c7`
- 작업 브랜치: `feat/ch01-section-1-7`
- 상태: **STATIC_REVIEW_COMPLETE / FIXES_APPLIED / ROS_RUNTIME_NOT_VERIFIED**
- 분류 근거: `Ch01/ref/my_first_package/cmd_publisher_node.py`의 “1.7절 실습” 및 “1.7절 의존성 관리” 주석.

## 1. 소스·기능 계약

| 대상 | 원래 코드 | 검토 결과 |
|---|---|---|
| `Ch01/ref/my_first_package/cmd_publisher_node.py` | `rclpy.Node`, `geometry_msgs.msg.Twist`, `create_publisher(Twist,'cmd_vel',10)`, 0.5초 타이머 | 2Hz Twist 발행 구조는 적합 |
| `Ch01/ref/setup.py` | `cmd_publisher = my_first_package.cmd_publisher_node:main` | 진입점과 `main()` 정의가 일치 |
| `Ch01/ref/package.xml` | `rclpy`, `geometry_msgs`, `sensor_msgs` | 실제 import 의존성 `rclpy`·`geometry_msgs`는 선언됨. `sensor_msgs`는 현재 미사용 |
| `Ch01/ref/setup.cfg` | **부재** | `ros2 run` 표준 실행파일 설치 경로 불확실 → 파일 추가 |
| `cmd_vel` 토픽 | 상대 이름, 네임스페이스 없으면 `/cmd_vel` | 실제 로봇의 속도 명령과 충돌 가능. 실습에서는 이름 변경 권고 |

`Twist`는 3차원 선속도·3차원 각속도 벡터이며 이 예제는 `linear.x`와 `angular.z`만 사용한다. 이 노드는 속도 명령의 **송신**까지만 담당한다. 실제 이동, 로봇 구동기, 피드백, 폐루프 제어 및 안전 정지를 증명하지 않는다.

## 2. 결함 분석 및 수정

| ID | 심각도 | 근거/영향 | 처리 |
|---|---|---|---|
| 17-01 | High | 기존 코드가 기본 `linear.x=0.2m/s`, `angular.z=0.5rad/s`를 무기한 발행. 실물 로봇이 `/cmd_vel`을 구독하면 의도치 않은 구동 위험 | **수정:** 기본 0/0, 10회 발행 후 정지·자체 종료; 실제 이동 시연은 명시적인 ROS 파라미터로만 허용 |
| 17-02 | High | 기존 코드 Ctrl+C에서 즉시 노드 파괴하며 마지막 정지 `Twist()`를 발행하지 않음 | **개선:** 횟수 완료 및 정상 종료 시 정지 명령 발행; **DDS 수신/물리 정지를 보장하지 않음** |
| 17-03 | High | `ref/setup.cfg` 미존재, 기본 진입점 설치 경로가 `ros2 run` 기대 경로와 다를 수 있음 | **수정:** `[develop]/[install]`의 `lib/my_first_package` 경로 추가 (1.6 브랜치와 동일한 내용) |
| 17-04 | Medium | 송신 횟수에 제한이 없고 외부 파라미터로 속도·횟수를 조정할 수 없음 | **수정:** `linear_x`, `angular_z`, `publish_count` 추가; 비유한 속도/0 이하 횟수 거부 |
| 17-05 | Medium | 기본 `cmd_vel`이 모의·실제 로봇의 제어 토픽과 충돌 가능 | **가이드:** `-r cmd_vel:=/ch01_demo/cmd_vel` 로 격리하여 관찰 |
| 17-06 | Low | `sensor_msgs` 미사용 의존성 및 `setup.py` placeholder maintainer·라이선스 | **OPEN:** 불필요 의존성 정리, 저작권자 메타데이터 확정 권고 |

**중요한 의도적 동작 변경:** 원본의 무한·비영 속도 송신에서 **기본 정지 + 2Hz × 10회 + 정지 송신 + 프로세스 종료**로 바뀌었다. 교재의 수치 예시 `0.2m/s, 0.5rad/s`는 `--ros-args -p linear_x:=0.2 -p angular_z:=0.5`로 재현한다.

정지 `Twist()`를 송신하더라도, DDS 연결 상태·수신 주기·컨트롤러 타임아웃·로봇 구동기 구현에 따라 정지가 지연되거나 누락될 수 있다. **실물 로봇에서 하드웨어 안전 정지/워치독을 대체하지 않는다.** 실습의 권장 경로는 오직 모의 토픽 에코 확인이다.

## 3. 변경 파일

- `Ch01/ref/my_first_package/cmd_publisher_node.py`: ROS 파라미터, 유한 값 검증, 유한 발행, best-effort zero Twist, 종료 정리
- `Ch01/ref/setup.cfg`: ROS 2 entry point 설치 위치 (1.6 브랜치에도 동일한 파일이 추가됨)
- `Ch01/docs/SECTION_1_7_REPORT_KO.md` 및 `LAB_1_7_GUIDE_KO.md` 추가

다른 장과의 인터페이스 공유, 기존 ROS 프로젝트의 `/cmd_vel` 계약 변경은 수행하지 않았다. 각 절 브랜치는 동일한 `main`에서 독립적으로 시작하므로, 1.6 먼저 병합한 후 1.7 PR을 검토하면 된다.

## 4. 검증 현황 (Ch12 증거 구분 방식)

| 검증 | 상태 | 근거 |
|---|---|---|
| `Twist` import·ROS 패키지 의존성·entry point 정적 추적 | **REVIEWED** | 원격 소스·메타데이터 읽기 |
| 2Hz timer, 기본 0/0, 카운트/정지 호출 경로 | **REVIEWED** | 수정 코드 정적 리뷰 |
| `compileall` | **PASS (offline)** | 원격 blob SHA와 일치하는 수정 파일을 Python 3.13.5에서 구문 컴파일 |
| Jazzy `colcon build` | **NOT_RUN** | 현재 환경에는 `ros2` 및 `colcon` 없음 |
| 실제 DDS `/ch01_demo/cmd_vel` 발행/수신 | **NOT_RUN** | ROS 그래프 실행 환경 없음 |
| 카운트 10회·마지막 zero Twist·자동 exit 0 | **NOT_RUN** | ROS2 런타임 검증 필요 |
| 하드웨어 안전성 및 워치독 | **OUT_OF_SCOPE** | 센서/모터/안전컨트롤러 부재 |

호스트는 Debian 13 / Python 3.13으로 ROS 2 Jazzy 실습 조건과 다르다. **실제 테스트 PASS를 보고하지 않는다**. Ch12 테스트 수치와 별개로 Ch01에 대한 신규 실행 증거가 필요하다.

## 5. 재현 및 최종 ACCEPT

[LAB_1_7_GUIDE_KO.md](LAB_1_7_GUIDE_KO.md)에 따라 작업 브랜치를 체크아웃하고 독립 워크스페이스를 생성한다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ch01_lab_17
python3 -m compileall -q src/my_first_package
colcon build --symlink-install --packages-select my_first_package
source install/setup.bash
# 터미널 A: ros2 topic echo /ch01_demo/cmd_vel
ros2 run my_first_package cmd_publisher --ros-args \
  -r cmd_vel:=/ch01_demo/cmd_vel \
  -p linear_x:=0.2 -p angular_z:=0.5 -p publish_count:=10
echo "exit_code=$?"
```

**ACCEPT:** 패키지 빌드 성공, `ros2 pkg executables`의 `cmd_publisher` 노출, remap된 토픽의 `geometry_msgs/msg/Twist` 확인, 약 0.5초 주기로 비영 `linear.x`와 `angular.z` 10회·종료시 zero 명령 관찰 및 자체 종료 코드 0, 기본 실행에서는 비영 속도 명령이 전혀 없어야 한다. ROS 그래프 타이밍상 종료 zero 수신 확인이 불안정하면 **미통과로 기록**하고 추후 확인한다. 로그와 로봇 미연결 상태를 증거로 남긴다.

## 6. 별도 오프라인 검증 (2026-10-20)

원격 `cmd_publisher_node.py`의 Git blob SHA는 `b16e8b5e745affc460da47d8929c0220c00f6366`. 별도 Debian 13/Python 3.13.5 공간의 검사 파일에 대해 `git hash-object`가 **동일한 SHA**를 반환했고 `python3 -m compileall -q`가 성공했다(`PY_COMPILE_PASS`).

ROS 의존성을 가짜 `Node`/`Publisher`/`Twist` 객체로 대체한 **오프라인 콜백 테스트** 결과:
- `TWIST_DEFAULT_PASS`: 기본 속도 0/0, 10번 발행 후 정지 `Twist` 추가, `finished`·timer 취소.
- `TWIST_OVERRIDE_PASS`: 파라미터 0.2m/s·0.5rad/s·횟수 3 → 비영 메시지 3회와 마지막 zero 메시지 1회.
- `TWIST_PARAM_VALIDATION_PASS`: NaN 속도 및 0회 카운트에 대해 `ValueError` 확인.

하네스는 GitHub에 보존하지 않은 일시 검증 코드이므로 독립 CI 증거는 아니다. fake 객체는 ROS 2의 파라미터 서비스·Executor·DDS 전송을 모사하지 않으며, 실제 `ros2 run` 성공·2Hz 실시간 전송·종료 zero 수신을 증명하지 않는다. 실습 Acceptance의 ROS 항목은 여전히 **NOT_RUN**이다.
