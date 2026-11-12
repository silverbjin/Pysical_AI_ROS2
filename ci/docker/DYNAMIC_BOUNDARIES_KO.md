# 교재 동적 실패 경계 — Ch05 / Ch09 / Ch10 / Ch11

공개 GitHub Actions: Book dynamic failure boundaries Ch05 Ch09 Ch10 Ch11

기존 검수기 ci/docker/next_scope.sh 의 BOOK_DYNAMIC=1 선택 실행만 추가한다. 미설정 시 기존 동작 유지. 고정 GHCR 이미지: ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f

## 검수 계약

| 챕터 | 목표 | PASS 근거 | 제외 범위 |
|---|---|---|---|
| Ch05 | joint2 0.5rad 및 home 추종 | 원본 simple_controller 명령 후 1.15~1.70초 측정 오차 각각 0.10rad 이내 | 전체 관절, 3회 반복, GUI |
| Ch09 | single_leg_mover에서 실제 Gazebo 관절 반응 | 명령 10+ 샘플, 관절 10+ 샘플, 명령 변동 0.15rad 이상, 측정 0.10rad 이상 | 기립 균형, 12관절 전체 |
| Ch10 | 실제 IK 모델 대 URDF 다리 길이 | l2/l3 대 thigh_length/calf_length 오차 각 1e-4m 이하 | 수치 불일치 시 물리 보행은 NOT_RUN |
| Ch11 | 실제 센서 토픽 | 원본 센서 월드와 ROS/GZ bridge에서 IMU 5+개, scan 2+개, 유효 거리와 timestamp | EKF, SLAM, 지도 저장, GUI |

## 원칙

- 한 번 검증된 base/spawn/clock만 재사용하고 새 동적 기능의 실패 경계에서 멈춘다. 성공한 옛 증거 재검 금지.
- 소스 SHA, 이미지 digest, 독립 ROS_DOMAIN_ID/GZ_PARTITION, 명령 로그, 첫 실패 STAGE, JSON 증거를 Actions Artifact로 보존한다.
- 실패는 FAIL로 표시한다. 외부 권한/환경 장애가 확정된 경우만 BLOCKED다. KNOWN_FAIL 검출을 PASS로 승격하지 않는다.
- 교재 코드는 이번 CI 작업에서 직접 수정하지 않으며, 별도 수정 검토가 필요하면 이슈로 기록한다.
- 이전 CI를 반복 실행하는 과도한 트리거를 축소한다. WSL2 GUI 및 Gazebo 시각 인수는 별도다.

## Ch10 known failure 판정

- 실제 IK/URDF 길이 차이(0.20m vs 0.25m)를 검출하면 JSON status=FAIL, 종료코드 10, verdict=KNOWN_FAIL로 기록한다. 문제는 Issue #123에서 추적한다.
- 전체 워크플로는 **검수기 자체의 기대 결함 탐지 성공**만 인정한다. Ch10 실습 또는 보행이 PASS라는 뜻이 아니다.
- 메시지 시그니처와 JSON status를 모두 확인하지 못한 비정상 실패는 여전히 CI FAIL. 길이 문제가 수정되어 실제 정합성이 확인되면 해당 검사는 PASS로 변경될 수 있으나 보행 물리 테스트는 계속 NOT_RUN이다.
