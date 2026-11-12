# 1.1절 코드 변경·정적 검증 보고서

- 기준: 업로드 1장 원고 1.1.1~1.1.3 + 기존 `SECTION_1_1_REPORT_KO.md`
- 상태: **NO_SOURCE_CODE_IN_SCOPE / DOCUMENTATION_ONLY**
- 기준 환경: Ubuntu 24.04 / ROS 2 Jazzy. 이 실행 환경에는 `ros2`·`colcon`이 없음.

## 소스 현황과 결정

1.1절은 ROS 1→ROS 2의 전환, DDS discovery, QoS, 실시간성·보안·zero-copy에 대한 **개념 절**이다. 저장소 `Ch01`에 1.1절 전용 노드, QoS 프로파일 또는 DDS 성능 측정 코드가 없다. 따라서 없는 소스를 수정했다거나 ROS 1 마스터 장애 시험이 통과했다고 기술하지 않는다. 기존 실습의 `demo_nodes_cpp talker` / `demo_nodes_py listener`는 Jazzy 외부 기본 패키지다.

## 정적 검토 판정

| 검사 | 상태 | 근거 |
|---|---|---|
| 1.1 전용 실행 코드 존재 여부 | REVIEWED / 없음 | 기존 Ch01 소스 매핑·1.1 리뷰 |
| ROS 1 마스터 단일 장애점 과장 | **원고 수정 필요** | 기존 REVIEW C01-11-01, 코드 수정으로 해결 불가 |
| hard real-time 1ms, 자동 DDS 보안·zero-copy | **원고 수정 필요** | C01-11-02~03, 지원 조건·안전 요구 재서술 |
| QoS 호환성과 전송 성능 | **실험 필요** | C01-11-04, 코드와 유실/지연 시험 없음 |
| `ros2 run`·DDS 통신 실험 | NOT_RUN | 이 환경에 Jazzy 미설치 |

## 변경 파일·추후 실행 확인

- **변경:** 이 보고서만 추가; 실행 소스는 수정하지 않음.
- 재현: [LAB_1_1_GUIDE_KO.md](LAB_1_1_GUIDE_KO.md)의 talker/listener·`ros2 topic info -v /chatter`.
- **출판 전 남은 작업:** ROS 1 마스터·DDS 실시간성 설명 개정, 실기/무선 QoS 시험의 수치 증거 확보. 개념 설명 변경은 코드 수정 완료로 대체할 수 없음.
