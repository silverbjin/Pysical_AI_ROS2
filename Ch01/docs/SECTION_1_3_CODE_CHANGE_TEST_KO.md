# 1.3절 코드 변경·정적 검증 보고서

- 기준: 업로드 1장 원고 1.3.1~1.3.5 + 기존 `SECTION_1_3_REPORT_KO.md`
- 상태: **NO_CUSTOM_INTERFACE_CODE / DOCUMENTATION_ONLY**
- 검증 경계: 실제 ROS 2 환경에서 `turtlesim` 명령은 실행하지 않음.

## 소스 현황과 결정

1.3절의 `SensorData.msg`, `AddTwoInts.srv`, `MoveRobot.action`은 **원고에 등장하는 선언 예제**로서 `Ch01`에 실제 빌드되는 사용자 정의 인터페이스 파일이 없다. 절별 코드를 임의로 생성하면 원고의 범위 및 인터페이스 계약이 바뀌므로, 본 회차는 구현 소스를 수정하지 않는다. 실습은 Jazzy의 표준 `turtlesim`에 의존한다.

## 정적 검토 판정

| 검사 | 상태 | 근거 |
|---|---|---|
| Ch01 커스텀 `.msg/.srv/.action` 실습 코드 | REVIEWED / 없음 | 기존 Ch01 매핑 및 1.3 보고서 |
| 일반 `Node` vs Managed Lifecycle Node | **원고 개선 필요** | REVIEW C01-13-01 |
| 중복 노드 이름, 비동기 Service, Action 취소 승인 | **원고 개선 필요** | C01-13-02~03 |
| Safety watchdog/E-stop 필요성 | **원고 개선 필요** | C01-13-05 |
| 실제 rosidl 빌드·Topic·Service·Action 실행 | NOT_RUN | 해당 코드 없음 / ROS2 런타임 없음 |

## 변경 파일·후속 작업

- **변경:** 이 보고서만 추가. 타 장의 인터페이스·통신 API를 임의로 도입하지 않음.
- 실제 실습은 [LAB_1_3_GUIDE_KO.md](LAB_1_3_GUIDE_KO.md)의 Topic/Spawn/RotateAbsolute 순서로 재현.
- 사용자 정의 인터페이스 생성 과제가 필요하면 별도 교육 목표·패키지 의존성 승인 후 작성하며, 지금 시점의 **PASS로 주장하지 않는다**.
