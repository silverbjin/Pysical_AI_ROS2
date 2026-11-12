# Physical AI 실무 가이드

ROS 2를 기반으로 로봇 모델링, 제어, 비전, 강화학습, 4족 보행과 복합 시스템 검증을 단계적으로 익히는 도서의 실습 저장소입니다. 각 챕터의 코드와 실습 가이드를 통해 실행 결과를 관찰하고, 동작한 범위와 실패 원인을 기록하는 방법을 다룹니다.

## 대상 독자

- Python 또는 C++ 기초를 갖추고 ROS 2 로봇 개발을 시작하려는 독자
- 로봇 모델링·제어·비전·강화학습을 하나의 실습 흐름으로 연결하려는 학생과 개발자
- 시뮬레이션의 실행·측정·실패 분석과 재현 가능한 검증 방법을 익히려는 연구자와 교육자

## 도서 목표

1. ROS 2의 통신 구조와 개발 환경을 이해하고 패키지를 구성합니다.
2. 로봇 모델과 좌표계, 센서, 제어기를 시뮬레이터와 연결합니다.
3. 운동학·MoveIt·비전·강화학습을 이용한 로봇 동작을 실습합니다.
4. 4족 로봇의 보행, 상태 추정, 지도 작성과 복합 시스템을 다룹니다.
5. 실제 실행 기록을 바탕으로 완료한 기능, 실패 원인, 안전 종료와 검증 한계를 설명합니다.

## 챕터별 실습 가이드

각 챕터의 README에서 절별 실습 가이드로 이동할 수 있습니다. 현재 저장소에 제공된 1~13장을 연결합니다.

| 챕터 | 주제 | 실습 안내 |
|---|---|---|
| 1장 | ROS 2 시작하기 | [1장 README](Ch01/README.md) |
| 2장 | ROS 2 통신 시스템 | [2장 README](Ch02/README.md) |
| 3장 | 로봇 모델링과 시뮬레이션 환경 | [3장 README](Ch03/README.md) |
| 4장 | 좌표계와 TF2 | [4장 README](Ch04/README.md) |
| 5장 | 로봇 기초 제어 | [5장 README](Ch05/README.md) |
| 6장 | 로봇팔 운동학과 MoveIt | [6장 README](Ch06/README.md) |
| 7장 | 로봇 비전과 인식 기반 조작 | [7장 README](Ch07/README.md) |
| 8장 | 강화학습과 MuJoCo | [8장 README](Ch08/README.md) |
| 9장 | 4족 보행 로봇 모델링 | [9장 README](Ch09/README.md) |
| 10장 | 보행 패턴 생성 및 제어 | [10장 README](Ch10/README.md) |
| 11장 | 센서 융합과 SLAM | [11장 README](Ch11/README.md) |
| 12장 | 강화학습 기반 4족 보행 | [12장 README](Ch12/README.md) |
| 13장 | 복합 로봇 실습 | [13장 README](Ch13/README.md) |

## 실습 시작 전

챕터마다 사용하는 환경과 의존성이 다릅니다. 해당 README와 실습 가이드의 버전·설치·실행 순서를 먼저 확인하세요. ROS 2 Jazzy, Gazebo Harmonic 또는 MuJoCo 등은 각 가이드가 명시한 범위에서 사용하며, 외부 모델과 정책 자산은 별도 준비가 필요할 수 있습니다.

실제 동작 검증, 부품 시험, 모의 실행과 과거 시연 기록은 구분합니다. 과거의 성공 사례가 최신 코드의 반복 재현성이나 실기 안전을 보증하지는 않습니다.

### 13.8절의 제공 범위

- **기본 실습:** 이동·관측·상태 확인·안전 종료와 실패 판독. [시작 가이드](Ch13/docs/START_HERE_13_8_KO.md)
- **Level 2 확장 시연:** 과거 전체 운반·놓기 기록 해설. [시연 자료](Ch13/docs/DEMO_13_8_LEVEL2_ARCHIVE_KO.md)
- **향후 과제:** 최신 버전의 연속 임무 재현과 Level 3 파지 이후 동작. [과제 범위](Ch13/docs/FUTURE_13_8_TASKS_KO.md)

[13.8 수정 교재 본문](Ch13/docs/TEXTBOOK_SECTION_13_8_REVISED_KO.md) · [기본 실습 검증 보고](Ch13/docs/SECTION_13_8_BOOK_CLOSEOUT_REPORT_20261112_KO.md)

## 저자 연락처

- 이메일: [silverbjin@gmail.com](mailto:silverbjin@gmail.com)
- 블로그: [https://blog.naver.com/silverbjin](https://blog.naver.com/silverbjin)

실습 문의 시 사용한 챕터·절, 소스 버전, 실행 환경, 명령과 오류 내용을 함께 알려 주세요.
