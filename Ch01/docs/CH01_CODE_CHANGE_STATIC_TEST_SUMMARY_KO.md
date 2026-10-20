# 1장(1.1~1.7) 코드 수정 및 정적 테스트 통합 보고서

- 일자: 2026-10-20
- 기준 저장소: https://github.com/silverbjin/Pysical_AI_ROS2
- 기준 `main`: `f5aed1d250563efc298e717559497db3b4f205c7`
- 정책: 절별 `feat/ch01-section-1-N` 브랜치에 Commit/Push. PR 생성 및 main 병합 없음.
- 검증 환경: Debian 13, Python 3.13.5, Bash 5.2; `ros2`·`colcon` 없음.

## 1. 절별 변경 내역

| 절 | 코드 수정/추가 | 오프라인 확인 | 잔여 검증 |
|---|---|---|---|
| 1.1 | 원고의 개념 절: 전용 실행 코드가 없어 보고서만 생성 | 소스 부재 및 기존 리뷰 범위 확인 | DDS/QoS 실측 NOT_RUN |
| 1.2 | `Ch01/scripts/check_jazzy_environment.sh`: 설치/쉘 변경 없는 사전 환경 검사 | `bash -n` PASS; 비지원 Debian 거부(exit 2) PASS | Jazzy 현장 검사 NOT_RUN |
| 1.3 | 원고의 `.msg/.srv/.action`은 가상 예시: 구현 변경 없이 보고서 | 원고·소스 범위 확인 | turtlesim·rosidl NOT_RUN |
| 1.4 | `check_workspace_layout.sh` 및 오프라인 테스트 | 비파괴 진단 unittest 3/3 PASS, bash -n PASS | colcon/DDS NOT_RUN |
| 1.5 | `test_ch01_package_contract.py` 추가; 기존 실행 인터페이스 보존 | manifest/entrypoint/setup.cfg/AST 4/4 PASS | colcon build NOT_RUN |
| 1.6 | `simple_controller.py` 생성·종료 오류 복구 강화 및 Mock 테스트 | 노드·Heartbeat·종료·생성 오류 4/4 PASS | 실제 `ros2 run`, 1Hz 실측 NOT_RUN |
| 1.7 | `package.xml`, `setup.py` 설명·이메일 정합성 수정 및 테스트 | 메타데이터 3/3 PASS | rosdep, 실환경 빌드 NOT_RUN; 라이선스 OPEN |

## 2. 실제 실행 테스트와 범위

- 분리된 브랜치의 변경을 **조합한 로컬 후보 스냅샷**에서 `python3 -m unittest discover -s Ch01/tests -p 'test_*.py' -v` 실행: **14 tests, OK (14 PASS / 0 FAIL)**.
- `python3 -m compileall -q Ch01/robot_ws/src/my_robot_controller Ch01/tests`: **PASS**.
- `bash -n Ch01/scripts/check_jazzy_environment.sh Ch01/scripts/check_workspace_layout.sh`: **PASS**.
- 실제 Debian 13에서 `check_jazzy_environment.sh`는 **exit 2 / 의도한 BLOCKED**. 이는 오류가 아니라 잘못된 플랫폼에 대한 가드 테스트다.
- 새 워크스페이스 진단은 `build/install/log` 파일을 생성하거나 삭제하지 않음을 확인했다.
- GitHub에 Push된 **9개 주요 코드·테스트 파일**의 Git blob SHA를 로컬에서 테스트한 파일 해시와 비교: **9/9 동일**.
- **NOT_RUN:** ROS 2 Jazzy, colcon 빌드, DDS discovery, 실제 node/spin, turtlesim, Gazebo/MuJoCo, 제어기 하드웨어 안전 테스트. 오프라인 Mock PASS는 ROS 런타임 성공 근거가 아니다.

## 3. 파일 위치와 브랜치

각 절 보고서: `Ch01/docs/SECTION_1_N_CODE_CHANGE_TEST_KO.md` (N=1~7). 해당 파일은 각각 `feat/ch01-section-1-N` 브랜치에 보존한다. 1.7 브랜치에 이 통합 요약도 추가한다.

- 1.1 `ee5f57521e8f8eeb43a7ab2b8a3ec78aa2a9d292`
- 1.2 `a4e308a9b76c316717e5a02ae1473b153ede7cb8`
- 1.3 `0f45581385ae4d66ab51c6948486759c42c59e63`
- 1.4 `acd284c36f44cbdde77748a76faff4ac129ae91b`
- 1.5 `8b623a277508eae8bfde8617cd5bd2e93f500de0`
- 1.6 `4901fbd42c2b6ea1fb81f76326db7577489ceed8`
- 1.7 코드/절별 보고 `c6ddac5aea6cf8bb9da76aadbed69957928887cc` (통합 요약 commit은 이후 갱신).

## 4. PR 및 검증 계획

기존 사용자 정책에 맞게 자동 PR은 생성하지 않았다. `1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7` 순서로 변경 범위를 검토한다. 1.6과 1.7에서 공통 `Ch01/ref/setup.cfg`가 추가된 이력이 있어 PR 간 파일 중복을 확인한다. `Ch01/README.md`는 1.6 브랜치에 포함되어 앞선 절들의 병합 전에는 모든 상대 링크가 동작하지 않을 수 있다.

Jazzy 통합 단계에서 다음을 수행한다.

```bash
source /opt/ros/jazzy/setup.bash
python3 -m unittest discover -s Ch01/tests -p 'test_*.py' -v
python3 -m compileall -q Ch01/robot_ws/src/my_robot_controller
colcon build --symlink-install --base-paths Ch01/robot_ws/src/my_robot_controller
# 또는 절별 실습 전용 워크스페이스에 패키지를 복사하여 빌드
ros2 run my_robot_controller test_node
```

※ 마지막 명령은 해당 패키지를 빌드한 `install/setup.bash`를 소싱한 셸에서만 수행한다. `colcon build`는 패키지를 복사한 전용 워크스페이스 루트에서 실행하는 편이 안전하다. 실제 ROS 환경에서 명령 종료 코드와 로그를 확인하기 전까지 실행 Acceptance는 **BLOCKED/NOT_RUN**이다.

**열린 결정 사항:** 주교재 `my_robot_controller`의 `license`가 여전히 TODO이다. 소유자의 라이선스 확정 없이는 임의로 라이선스를 지정하지 않는다. 보조 `Ch01/ref`의 무제한 비영 `cmd_vel` 발행 코드는 실제 로봇과 연결해 실행하지 않는다.