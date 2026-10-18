# Camera ownership 실행 기록

실행 UUID: `35954ef5-3ada-46e9-886b-c5e1f6d4a5a4`.
시작 source HEAD: `124061f32bc6492ac42a67fe43a7bb67ed245050`.
브랜치: `feat/ch13-section-13-4`. 승인된 계획의 네이티브 실행이며 서브에이전트 없음.
외부 underlay: `mujoco_ros2_control@c261f5552edf124d1000a23fb25b6c07cadeb807` (변경 없음).

## Task1

| 검사 | 결과 / 원본 |
|---|---|
| 기존 소스 회귀 | PASS, 254건, 123.19초, `baseline-pytest.log`, exit0 |
| API 미구현 RED | 의도된 실패, 새 snapshot_mailbox.hpp 부재, `mailbox-red-build.log`, exit2 |
| 새 코어 build | PASS, `mailbox-green-build.log`, exit0 |
| 실제 mjData 소유권 시험 | PASS, 9건/실패0, `mailbox-green.log`, `mailbox-green.xml`, exit0 |
| 변경 후 소스 회귀 | PASS, 254건, 117.42초, `task1-pytest.log`, exit0 |
| TSAN 별도 build | PASS, `mailbox-tsan-build.log`, exit0 |
| TSAN 첫 실행 | 비정상 종료139, 시험 시작 전, `mailbox-tsan.log` 출력0바이트 |
| TSAN 진단 재실행 | exit1, unexpected memory mapping, `mailbox-tsan-diagnostic.log` |
| TSAN underlay+verbosity2 실행 | exit0, 9건 PASS, race warning 없음, `mailbox-tsan-diagnostic-sourced.log` |

TSAN 시작은 이 WSL 환경에서 불안정하다. 성공한 한 번의 코어 검사와 실패한 두 실행을
모두 보존한다. 시스템 정책/ASLR을 바꾸지 않았으며 외부 MuJoCo/GL은 계측하지 않았다.
플러그인·실제 카메라 엔진·종단 추적의 인수 결과는 아직 아니다.

경로는 저장소 기준이다. 일반 build/install/log suffix는
`13_4_snapshot_35954ef5-3ada-46e9-886b-c5e1f6d4a5a4`, TSAN은
`13_4_snapshot_tsan_35954ef5`다. ROS Jazzy + 고정 vendor underlay +
`/home/jinho/ch13_vision_13_4_venv`를 사용했고 기존 Ch13 overlay를 새 코어 build에
source하지 않았다. Python 기존 회귀는 기존 debug install 환경에서 실행했다.

다음 단계: 새 플러그인 구현, 실제 GL 및 동적 로딩 검증, backend 선택/설치 감사,
실제 두 엔진 인수. 전체13.4 완료나13.5 재개를 선언하지 않는다.
