# Ch10 보류 이후 교재 검수 — 범위/판정 계약

2026-11-12 기준. Ch10의 IK/URDF 길이 불일치 [Issue #123](https://github.com/silverbjin/Pysical_AI_ROS2/issues/123)는 수정하거나 재실행하지 않는다. 이전 수치/실패 증거는 그대로 보존한다.

## 재사용 환경

- Gazebo: 기존 `ci/docker/next_scope.sh`와 GHCR 고정 이미지 `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`. Dockerfile 재빌드 없음.
- Ch05: `BOOK_DYNAMIC=1`로 이미 PASS한 목표 추종 검사를 독립 컨테이너 3회 cold-session 반복하여 각 회차 결과와 원본 로그를 별도 저장. 물리 GUI나 실하드웨어 인수 아님.
- Ch09: `BOOK_EXTENDED=1`로 원본 `stand_up` 노드의 12개 ROS 명령과 12개 Gazebo 관절 상태를 확인. 첫 구간 측정값의 변화량 0.08rad 이상인 관절 4개 이상을 요구하지만, 기립 **균형/낙상 여부는 측정하지 않음**.
- Ch11: `BOOK_EXTENDED=1`로 원본 `sim_odometry`가 Gazebo `/simulation/odom`에서 /odom/raw로 전달하는지 원본 타임스탬프·프레임·XYZ를 비교. **EKF/SLAM/map 저장은 미실행**. 실제 관절/접촉 오도메트리가 아닌 Gazebo의 ground-truth observation임을 명시한다.
- Ch08: ROS 컨테이너에 MuJoCo를 섞지 않고 Ubuntu Python 3.12 + 고정 MuJoCo/Gymnasium/NumPy에서 `ReachEnv` 6행동·18관측·60 스텝·보상 및 리셋 재현성을 검사. PPO 장시간 학습, 정량 도달률 및 GUI는 NOT_RUN.
- Ch06 6.4 / Ch07 7.2: 기존 출판 가이드의 사전 의존성 BLOCKED를 파일 경로·엔트리포인트 기준으로 읽기 전용 재점검. **KNOWN_BLOCKED의 재현은 장 전체 PASS가 아니다.**
- Ch12: 기존 MuJoCo 파일럿 PASS 증거를 사용하고 재실행하지 않는다. Ch13: 외부 플랫폼 자산/로컬 렌더링·현장 검수 없이 장 전체 PASS로 승격하지 않는다.

## PASS와 중단 조건

- 하나의 실행에 대해 해당 명령이 모든 검사값을 통과해야 scoped PASS. 한 번 성공한 기존 원본 증거를 새로운 수치로 덮어쓰지 않는다.
- 실패할 때 원본 가이드와 검사기의 런타임/환경 결함을 분리한다. `ci-results/extended` Artifact에는 소스 SHA·이미지 digest·각 실행 종료 코드·모델/센서 검증 JSON 및 로그를 남긴다.
- Ch10은 어떠한 루프에도 추가하지 않는다. 향후 수정 필요 시 별도 PR에서 Issue #123을 해결한 뒤 안전 검증 절차를 계획한다.
- 실측되지 않은 시각 기립·EKF·SLAM, MoveIt 계획 실행, 카메라 토픽, PPO 학습 성능 또는 Ch13 전체 임무는 NOT_RUN / BLOCKED로 유지한다.

## 실행

GitHub Actions > `Book continued acceptance excluding Ch10` > Run workflow > `chapter=all` (또는 Ch05, Ch09, Ch11). PR은 기본적으로 세 Job(Ch06/07 게이트, Ch08 물리 API, Ch05/09/11 Gazebo)을 실행한다. GUI 및 현장 WSL2는 여전히 별도 최종 인수 대상이다.
