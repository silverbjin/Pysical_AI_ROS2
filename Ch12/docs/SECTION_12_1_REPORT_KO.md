# 12.1절 코드 리뷰 및 실습 적합성 보고서

기존 2026-10-17 구현·실행 보고서는 [CHANGE_REPORT_KO.md](CHANGE_REPORT_KO.md)에 보존한다.


---

## 2026-10-21 편집·코드 2차 리뷰: 원고 12.1 ↔ main 구현

> 검토 방식: GitHub `main/Ch12`의 공개 소스·기존 문서·저장된 2026-10-17 실행 증거와 첨부 원고를 **정적 대조**. **이번 세션에서 MuJoCo/Gazebo/ROS/PPO를 새로 실행하지 않았음.** 기존 문서의 과거 PASS를 새 실행 결과로 재표기하지 않는다. 구현 파일 변경 없음.

### 판정과 핵심 소견

**문서 보강 후 실습 가능(기존 검증 증거에 근거한 조건부 판정).** 실제 실행 장비/디스플레이/ROS overlay에 따라 현장 재현이 필요하며 학습 성능은 별도 판정이다.

1. **[높음·원고 교정]** 원고 12.1의 30차원 관측 예시와 실제 `QuadrupedEnv`의 기본 30차원, 선택 `full` 45차원은 구별해야 한다. 예시는 완전한 마르코프 상태를 증명하지 않는다.
2. **[중간·실습 구분]** 이 절의 기본 환경은 토크 제어·100 Hz이며 이후 12.2의 위치 제어·50 Hz 및 12.3의 48차원과 정책 호환되지 않는다. 행동 `(12,)`이 같아도 의미가 다르다.
3. **[중간·성능 판정]** PD 자세 유지와 무작위 토크 실행을 '학습된 보행'으로 표시하지 않는다. 지면 접촉·관절 제한과 종료 판정을 관찰하는 탐색 실습이다.

### 코드 및 증거 추적

- [`Ch12/src/quadruped_rl/env.py`](../src/quadruped_rl/env.py)
- [`Ch12/src/quadruped_rl/models/quadruped.xml`](../src/quadruped_rl/models/quadruped.xml)
- [`Ch12/src/quadruped_rl/demo.py`](../src/quadruped_rl/demo.py)
- [`Ch12/tests/test_env.py`](../tests/test_env.py)
- 기준 안내: [Ch12 README](../README.md), 기존 본 문서의 2026-10-17 검증 이력과 `Ch12/evidence/`.

### 독자·리뷰어 재검증 명령 (저장소 루트에서)

```bash
python -m pip install -e './Ch12[test,visual]'
python -m pytest Ch12/tests/test_env.py -q
quadruped-rl --policy random --steps 1000 --seed 42 --output /tmp/ch12-12-1-random.json
quadruped-rl --policy stand --steps 1000 --seed 42 --target-velocity 0 --output /tmp/ch12-12-1-stand.json
```

**Acceptance:** 30차원 기본 관측과 45차원 선택 관측, 12개 행동, 종료 후 reset 의무, random과 stand의 서로 다른 실험 목적을 구분한다. JSON과 pytest 결과를 남긴다.

**한계 및 조치:** 이 PR은 문서만 개정하며 실제 재실행·스크린샷·새 테스트 로그를 생성하지 않는다. 명령 실패 시 Python/MuJoCo/SB3/ROS 버전, 실행 위치, seed, stdout/stderr, 생성 JSON, git SHA를 남기고 버그/환경 문제를 분리해 새 코드 수정 PR로 처리한다.
