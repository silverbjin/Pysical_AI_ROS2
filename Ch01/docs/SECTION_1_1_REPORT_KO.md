# SECTION 1.1 — 원고·코드 리뷰: 로봇 개발의 패러다임 변화

- 작성: 2026-10-20 KST
- 기준: silverbjin/Pysical_AI_ROS2 / main f5aed1d250563efc298e717559497db3b4f205c7
- 브랜치: feat/ch01-section-1-1
- 범위: 원고 1.1.1~1.1.3: ROS 1 마스터, ROS 2 분산 discovery, DDS/QoS, AI/시뮬레이션. Ch01에 대응 전용 실행 코드 없음.
- 판정: **MANUSCRIPT_REVIEWED / STATIC_REVIEWED / ROS_RUNTIME_NOT_RUN**

## 1. 원고·저장소 매핑

이 절은 개념 장이며 저장소의 Ch01에 1.1 자체 노드 구현이 없다. 기존 Jazzy 데모를 활용한 관찰 실습만 설계하고 구현·성능 PASS를 주장하지 않는다.

## 2. 결함/정정 사항

| ID | 중요도 | 관찰·오해 가능성 | 권고 조치 |
|---|---|---|---|
| C01-11-01 | High | ROS 1 마스터 종료=이미 연결된 모든 노드 즉시 정지 | 기존 peer 연결은 계속 통신할 수 있음; 신규 탐색·등록·복구 실패 가능성과 구분 |
| C01-11-02 | High | ROS 2 채택=hard real-time 1ms 보장이라는 오해 | 실시간 커널·스케줄러·메모리·통신·제어기의 end-to-end 측정 필요 |
| C01-11-03 | Medium | DDS 보안, zero-copy, simulation time을 기본 보장으로 읽을 위험 | SROS2 보안 설정, RMW/메시지 지원 조건, 물리 Sim-to-Real 오차를 구분 |
| C01-11-04 | Medium | QoS Reliable 또는 Best Effort에 관한 일반화 | 호환성·유실률·지연을 실제 환경에서 측정, 성능 결과는 미검증 |

## 3. 구현·검증 및 남은 작업

- 문서 생성: `Ch01/docs/SECTION_1_1_REPORT_KO.md`, `Ch01/docs/LAB_1_1_GUIDE_KO.md`.
- 이 절에 고유 패키지 소스가 없는 경우, **원고의 코드가 실제 구현된 것처럼 판정하지 않는다**. 실습은 Jazzy 기본 패키지 및 CLI로 구성했다.
- **REVIEWED:** 업로드 원고와 저장소 대응, 기존 코드 범위 및 절 번호, 공식 Jazzy 설치/CLI 흐름.
- **NOT_RUN:** ROS 2 Jazzy/colcon/DDS/turtlesim/Gazebo 실제 실행 및 성능 수치. 현재 작업 환경에는 ros2와 colcon이 없다.
- 수정된 파일·실제 실행 명령·결과 수치는 각 검증 장소에서 별도 기록해야 한다. Ch12의 성공 로그를 Ch01 결과로 전용하지 않는다.

## 4. 재현/Acceptance

[LAB_1_1_GUIDE_KO.md](LAB_1_1_GUIDE_KO.md)의 STEP, 기대 출력, 실패 판정 기준에 따라 Ubuntu 24.04/ROS 2 Jazzy에서 실측한다. `git rev-parse HEAD`, `ros2 doctor --report`, 원본 로그, PASS/FAIL/NOT_RUN을 함께 저장하고 이 보고서를 갱신한 후 실습 Acceptance를 승인한다.

## 참고
- [ROS 2 Jazzy 공식 문서](https://docs.ros.org/en/jazzy/)
- [Ubuntu Jazzy deb 설치](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
