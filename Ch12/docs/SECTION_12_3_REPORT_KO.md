# 12.3절 수정 및 검증 보고서

기준 커밋 948718e, 패키지 0.3.0. 2026-10-17 Ubuntu-24.04 WSL에서 검증했다.

새 QuadrupedLocomotionEnv에 48차원 몸체 좌표 관측, 속도 명령, 위치 잔차 스케일, 항목별 보상 설정을 구현했다. 기존 12.1/12.2 관측 규격과 호환 모듈은 유지한다. 제곱오차 Gaussian, 회전 추종, 실제 모터 힘 비용, 행동 이력 시점, 낙상 시 양의 보상 차단을 반영했다. 초안의 관측 차원 오류와 선속도/각속도 혼동을 교정했다.

리뷰에서 지적한 낙상 이후 하위 스텝 접촉 누락을 수정했다. 종료 조건의 OR 단락 평가를 제거하여 바닥 반동 도중 생긴 접촉도 누적한다. 실제 MuJoCo 낙하·반동 회귀 사례로 검증했다. 잘못된 CLI 기본 명령 입력도 실행 전에 거부한다.

- 전체 테스트 65개 통과. 독립 리뷰 테스트도 65개 통과.
- 새 환경: 위치/토크 × 정지/무작위 × 명령 2종 × 시드 3종, 각 1,000스텝으로 24,000 제어 스텝. 독립 리뷰도 24,000스텝. 두 결과 PASS.
- 기존 12.1과 12.2 각각 12,000스텝 회귀 PASS. RGB 렌더링 검증 PASS.
- 별도 설치 wheel에서 48차원 환경과 실제 human viewer를 실행하고 100스텝/2초 진행, 자원 해제와 CLI Ctrl+C 종료 코드 130을 확인했다. 독립 최종 리뷰에서 추가 결함이 없음을 확인했다.
- 실제 Gazebo와 기존 ROS 패키지 빌드·104개 테스트 PASS. 시뮬레이션 8.024~38.046초 관측에서 몸체 높이 0.24794~0.24900m, 최대 기울기 1.25744도. 센서·TF 확인, 서버 종료 응답과 정상 종료 확인.

증거는 `evidence/section12_3`에 보관한다. 무한 Box 범위 경고, 의도적인 비정상 속도 주입 테스트 경고, 기존 KDL 루트 관성 경고가 있다. 단기 실습 환경 검증이며 강화학습 정책의 보행 성능을 입증하는 실험은 아니다.


---

## 2026-10-21 편집·코드 2차 리뷰: 원고 12.3 ↔ main 구현

> 검토 방식: GitHub `main/Ch12`의 공개 소스·기존 문서·저장된 2026-10-17 실행 증거와 첨부 원고를 **정적 대조**. **이번 세션에서 MuJoCo/Gazebo/ROS/PPO를 새로 실행하지 않았음.** 기존 문서의 과거 PASS를 새 실행 결과로 재표기하지 않는다. 구현 파일 변경 없음.

### 판정과 핵심 소견

**문서 보강 후 실습 가능(기존 검증 증거에 근거한 조건부 판정).** 실제 실행 장비/디스플레이/ROS overlay에 따라 현장 재현이 필요하며 학습 성능은 별도 판정이다.

1. **[높음·원고 교정]** 원고 12.3.5의 45차원 표에 외부 명령 3개가 빠졌다. 실행 정책 규격은 `[v 3,ω 3,gravity 3,cmd 3,q−q_nom 12,qdot 12,previous action 12]`의 **48차원**이다.
2. **[중간·보상 해석]** 코드의 속도·요 각속도 추적은 제곱 오차의 지수 함수이고, 토크 항은 `data.actuator_force`를 이용한다. 제어 입력 `data.ctrl`의 제곱을 곧바로 에너지라고 설명하면 틀린다. 지속 보상에 `dt`를 곱한다.
3. **[중간·리워드 타이밍]** `previous_action`은 갱신 순서가 중요하다. 실제 적용 행동의 이전값과 새 값을 비교해야 action-rate 벌점이 정의된다. 낙상에선 양의 추종 보상이 차단된다.

### 코드 및 증거 추적

- [`Ch12/src/quadruped_rl/locomotion_env.py`](../src/quadruped_rl/locomotion_env.py)
- [`Ch12/src/quadruped_rl/rewards.py`](../src/quadruped_rl/rewards.py)
- [`Ch12/config/section12_3_reward.json`](../config/section12_3_reward.json)
- [`Ch12/tests/test_locomotion_env.py`](../tests/test_locomotion_env.py)
- 기준 안내: [Ch12 README](../README.md), 기존 본 문서의 2026-10-17 검증 이력과 `Ch12/evidence/`.

### 독자·리뷰어 재검증 명령 (저장소 루트에서)

```bash
python -m pip install -e './Ch12[test,visual]'
python -m pytest Ch12/tests/test_locomotion_env.py -q
quadruped-rl --section 12.3 --policy stand --command 0 0 0 --steps 1000
quadruped-rl --section 12.3 --policy random --command .5 .2 .3 --steps 1000
```

**Acceptance:** 관측 shape=(48,), `info['reward_terms']` 합=reward(부동소수점 허용 오차), 지면 충돌과 시간 종료의 판정 차이, 명령 단위와 몸체 좌표계를 각각 확인한다.

**한계 및 조치:** 이 PR은 문서만 개정하며 실제 재실행·스크린샷·새 테스트 로그를 생성하지 않는다. 명령 실패 시 Python/MuJoCo/SB3/ROS 버전, 실행 위치, seed, stdout/stderr, 생성 JSON, git SHA를 남기고 버그/환경 문제를 분리해 새 코드 수정 PR로 처리한다.
