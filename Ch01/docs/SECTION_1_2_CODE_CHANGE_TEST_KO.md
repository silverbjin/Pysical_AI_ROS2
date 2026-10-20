# 1.2절 코드 변경·정적 테스트 보고서

- 기준 원고: 1.2.1~1.2.5 / 기존 `SECTION_1_2_REPORT_KO.md`
- 결과: **STATIC_PASS / ROS_RUNTIME_NOT_RUN**
- 추가 소스: `Ch01/scripts/check_jazzy_environment.sh`

## 수정 및 선택 근거

원고의 설치 명령을 자동으로 다시 실행하거나 시스템 apt/.bashrc를 변경하지 않고, **읽기 전용 환경 점검 스크립트**를 추가했다. Ubuntu 24.04 버전, Jazzy setup, Conda 활성화 충돌, `ROS_DISTRO`, `ros2`·`colcon`, Python 3.12, `rclpy` import를 조건부 점검하며 실패 시 `BLOCKED`와 종료 코드 2를 반환한다. WSLg·GPU 성능이나 Gazebo 실행을 PASS라고 선언하지 않는다.

## 실제 정적 시험 기록

| 검증 항목 | 수행 결과 | 판정 |
|---|---|---|
| `bash -n Ch01/scripts/check_jazzy_environment.sh` | exit 0 | **PASS** |
| Debian 13에서 실행 시 설치 OS 가드 동작 | exit 2, `BLOCKED: Ubuntu 24.04 required (actual: debian 13)` | **PASS (의도한 거부)** |
| apt 설치·.bashrc 파일 변경 부재 | 소스 정적 확인 | **PASS (정적 검토)** |
| Ubuntu 24.04/Jazzy 실제 구성 탐지 | ROS 2가 없는 Debian 13 리뷰 컨테이너 | **NOT_RUN** |
| GPU·WSL2·DDS 실측 | 해당 환경 없음 | **NOT_RUN** |

## 재현 명령

```bash
bash -n Ch01/scripts/check_jazzy_environment.sh
bash Ch01/scripts/check_jazzy_environment.sh
```

**출판 전 검증:** 실제 Ubuntu 24.04/Jazzy에서 스크립트 exit 0, `rclpy` import 성공, 두 터미널의 talker/listener 통신 증거를 추가해야 한다. Jazzy 이외 OS에서 종료 코드 2는 **의도된 BLOCKED**이며 로봇 실행 성공이 아니다.
