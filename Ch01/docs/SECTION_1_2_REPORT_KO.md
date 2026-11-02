# SECTION 1.2 — 원고·코드 리뷰: ROS 2 Jazzy 및 Ubuntu 24.04 설치

- 작성: 2026-10-20 KST
- 기준: silverbjin/Pysical_AI_ROS2 / main f5aed1d250563efc298e717559497db3b4f205c7
- 브랜치: feat/ch01-section-1-2
- 범위: 원고 1.2.1~1.2.5: 하드웨어·WSL2, locale, ros2-apt-source, ros-jazzy-desktop/ros-dev-tools, .bashrc, DDS 데모, PEP668.
- 판정: **MANUSCRIPT_REVIEWED / STATIC_REVIEWED / ROS_RUNTIME_NOT_RUN**

## 1. 원고·저장소 매핑

Jazzy 공식 Ubuntu deb 설치 문서에서 ros2-apt-source 기반 repository, ros-jazzy-desktop, ros-dev-tools, demo_nodes_cpp/py 검증을 확인했다. Ch01에는 전용 설치 스크립트가 없으므로 apt 실행 결과를 가장하지 않는다.

## 2. 결함/정정 사항

| ID | 중요도 | 관찰·오해 가능성 | 권고 조치 |
|---|---|---|---|
| C01-12-01 | High | 원고의 ‘최신 LTS’ 표현을 2026년 현재 최신이라고 오해 가능 | 본 교재 **기준 버전** Jazzy+Ubuntu 24.04라고 고정 |
| C01-12-02 | Medium | 다운로드/태그 요청 실패 및 apt 업데이트 검사 부족 | OS 코드명·빈 태그·다운로드 상태 사전 확인, 공식 설치 페이지 재검증 |
| C01-12-03 | Medium | ~/.bashrc에 source를 무조건 append하면 반복·overlay 충돌 | 중복 source 방지 및 ROS_DISTRO/AMENT_PREFIX_PATH 확인 |
| C01-12-04 | High | WSL2에서 모든 시뮬레이션이 차질 없다는 단정 | GPU/WSLg/OpenGL/드라이버 및 실측 FPS는 별도 검증 필요 |
| C01-12-05 | Medium | Conda/PEP 668을 무조건적 금지처럼 취급 | ROS 2 시스템 Python 우선; 호환 venv는 용도별 격리 가능 |

## 3. 구현·검증 및 남은 작업

- 문서 생성: `Ch01/docs/SECTION_1_2_REPORT_KO.md`, `Ch01/docs/LAB_1_2_GUIDE_KO.md`.
- 이 절에 고유 패키지 소스가 없는 경우, **원고의 코드가 실제 구현된 것처럼 판정하지 않는다**. 실습은 Jazzy 기본 패키지 및 CLI로 구성했다.
- **REVIEWED:** 업로드 원고와 저장소 대응, 기존 코드 범위 및 절 번호, 공식 Jazzy 설치/CLI 흐름.
- **NOT_RUN:** ROS 2 Jazzy/colcon/DDS/turtlesim/Gazebo 실제 실행 및 성능 수치. 현재 작업 환경에는 ros2와 colcon이 없다.
- 수정된 파일·실제 실행 명령·결과 수치는 각 검증 장소에서 별도 기록해야 한다. Ch12의 성공 로그를 Ch01 결과로 전용하지 않는다.

## 4. 재현/Acceptance

[LAB_1_2_GUIDE_KO.md](LAB_1_2_GUIDE_KO.md)의 STEP, 기대 출력, 실패 판정 기준에 따라 Ubuntu 24.04/ROS 2 Jazzy에서 실측한다. `git rev-parse HEAD`, `ros2 doctor --report`, 원본 로그, PASS/FAIL/NOT_RUN을 함께 저장하고 이 보고서를 갱신한 후 실습 Acceptance를 승인한다.

## 참고
- [ROS 2 Jazzy 공식 문서](https://docs.ros.org/en/jazzy/)
- [Ubuntu Jazzy deb 설치](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
