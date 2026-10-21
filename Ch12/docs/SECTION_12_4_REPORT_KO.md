# 12.4절 PPO 구현 및 검증 보고서

2026-10-17, 기준 2776008, 패키지 0.5.0. 12.5와 공유하는 학습·재생 도구를 추가했다.

## 구현 변경

`ppo.py`에 SB3 PPO 학습·평가·모델 저장·재생을 구현했다. `quadruped-train`과 `quadruped-play`, 본문 파일명에 대응하는 예제를 제공한다. actor/critic 분리 256×256 Tanh와 본문 권장 하이퍼파라미터를 적용했다. CPU를 기본값으로 하고 dummy와 실제 subproc spawn 병렬화를 구분한다.

총 전이 수를 기준으로 평가·체크포인트 빈도를 조정했다. 별도 Monitor 평가 환경, TensorBoard, 주기 최고 모델, 마지막 업데이트 평가, 최종 모델, 중간 저장, Ctrl+C 시 저장과 환경 해제를 연결했다. 새 출력 폴더만 허용하며 환경 설정과 버전을 manifest로 보존한다. 같은 관측 차원인 다른 과제의 모델이 섞이지 않도록 ZIP 내부의 schema와 환경 설정도 검사한다.

초안의 오래된 net_arch 표현을 현재 dict 형식으로 바꾸었다. CUDA 필수 가정, 벡터 환경=실제 병렬이라는 설명, 8배 속도 향상, clipping의 엄밀한 20% 정책 상한, 정해진 학습량에서 보행 완성 등의 보장은 제거했다. 학습은 원시 관측을 사용하며 정규화 wrapper는 적용하지 않았다.

## 실제 실행 결과

Ubuntu-24.04 WSL / Python 3.12 / MuJoCo 3.3.7 / Gymnasium 1.2.1 / SB3 2.7.1 / CPU PyTorch 2.5.1에서 실행했다. Windows Python 3.11 / CPU PyTorch 2.14.1에서도 초기 PPO·목표 테스트를 실행했다. 확정 환경 전체 목록은 `evidence/section12_4/dependencies.txt`에 있다.

- 실제 PPO: locomotion dummy 2,048전이, goal dummy 2,048전이, goal subproc 128전이. 각 실험은 2개 환경과 실제 신경망 업데이트를 사용했다.
- 파라미터 L2 변화량: locomotion 1.37549, goal dummy 2.29528, goal subproc 0.30091. 유한 파라미터와 실제 변화 확인.
- 각 실험에서 최적·최종·중간 모델 저장 및 로드, 200스텝 결정적 추론, RGB·CSV 출력 확인. TensorBoard 가치·엔트로피 손실, 평가 보상과 goal 성공률 이벤트 확인.
- 별도 학습 프로세스에 실제 SIGINT를 전달하여 종료 코드 130, 중단 모델 저장·재로드·추론을 확인했다.
- 전체 테스트와 독립 리뷰 테스트 각각 90개 통과. `section12_5/green.log`, `reviewer_tests.log`에 기존 절·EGL 회귀를 포함해 보관한다. 공개 CLI 학습 64전이·재생 20스텝도 확인했다.

짧은 평가의 최종 평균 보상은 locomotion 5.156461, goal dummy 2.570138, goal subproc 1.289233이다. 목표 성공률은 0%다. 실험 길이·보상 함수가 다르므로 과제 간 점수를 비교해 성능을 판단하면 안 된다. 실행 경로를 검증한 결과이며 안정적인 보행이나 목표 이동을 학습했다는 증거는 아니다.

독립 리뷰에서 목표 평가의 중간 도착 누락과 동일 차원 체크포인트 혼용을 재현하여 수정했다. 평가 goal_mode는 terminate로 고정하며 ZIP의 과제·환경 메타데이터를 검사한다. 불일치 파일 거부 회귀 테스트를 추가했다. subproc 학습과 dummy 평가의 wrapper 종류가 다르다는 SB3 경고는 이 의도적인 구성에서 발생하며 정규화 wrapper는 없다.

모델 ZIP은 28MB 이상이므로 Git 이력에는 넣지 않고, 설정·수치·로그·경로·렌더링과 모델 해시를 증거로 남긴다. 동일 명령으로 새 학습을 실행해 모델을 생성한다. 이 작업은 로컬 커밋이며 원격 push는 수행하지 않는다.


---

## 2026-10-21 편집·코드 2차 리뷰: 원고 12.4 ↔ main 구현

> 검토 방식: GitHub `main/Ch12`의 공개 소스·기존 문서·저장된 2026-10-17 실행 증거와 첨부 원고를 **정적 대조**. **이번 세션에서 MuJoCo/Gazebo/ROS/PPO를 새로 실행하지 않았음.** 기존 문서의 과거 PASS를 새 실행 결과로 재표기하지 않는다. 구현 파일 변경 없음.

### 판정과 핵심 소견

**문서 보강 후 실습 가능(기존 검증 증거에 근거한 조건부 판정).** 실제 실행 장비/디스플레이/ROS overlay에 따라 현장 재현이 필요하며 학습 성능은 별도 판정이다.

1. **[높음·원고 교정]** 원고의 `make_vec_env(...,n_envs=8)`이 반드시 8개 CPU 코어 병렬을 의미하지 않는다. 이 코드 기본 `backend=dummy`는 순차형이며 `--backend subproc`로 spawn worker를 분리해야 한다. 고정 8배 가속 주장은 제거한다.
2. **[높음·오해 방지]** `--total-timesteps 512` 또는 2,000,000회는 PPO 업데이트 횟수의 증거일 뿐 보행 숙달을 보장하지 않는다. 성공은 별도 seed의 에피소드 보상·전진 속도·낙상률로 평가한다.
3. **[중간·자원/호환성]** 소형 MLP는 CPU가 적절할 수 있어 `device='cuda'`를 강제하지 않는다. `manifest.json`과 모델 ZIP·환경 schema를 한 묶음으로 보관한다. `--output` 경로는 기존 디렉터리를 재사용하지 않는다.

### 코드 및 증거 추적

- [`Ch12/src/quadruped_rl/ppo.py`](../src/quadruped_rl/ppo.py)
- [`Ch12/tests/test_ppo.py`](../tests/test_ppo.py)
- [`Ch12/examples/train_ppo.py`](../examples/train_ppo.py)
- [`Ch12/evidence/section12_4/ppo_runs/cli/result.json`](../evidence/section12_4/ppo_runs/cli/result.json)
- 기준 안내: [Ch12 README](../README.md), 기존 본 문서의 2026-10-17 검증 이력과 `Ch12/evidence/`.

### 독자·리뷰어 재검증 명령 (저장소 루트에서)

```bash
python -m pip install -e './Ch12[test,visual,train]'
python -m pytest Ch12/tests/test_ppo.py -q
quadruped-train --output Ch12/runs/review-12-4 --total-timesteps 512 --n-envs 2 --n-steps 64 --batch-size 64 --n-epochs 2 --eval-every 256 --eval-episodes 2 --checkpoint-every 256
quadruped-play --output Ch12/runs/review-12-4 --steps 200
```

**Acceptance:** 학습 output 신규 생성, manifest/final_model/best_model/평가 기록 생성 여부, 재생 시 schema 검사 및 에피소드 종료 처리 확인. 성공률·장기 보행은 별도 실험으로 판정한다.

**한계 및 조치:** 이 PR은 문서만 개정하며 실제 재실행·스크린샷·새 테스트 로그를 생성하지 않는다. 명령 실패 시 Python/MuJoCo/SB3/ROS 버전, 실행 위치, seed, stdout/stderr, 생성 JSON, git SHA를 남기고 버그/환경 문제를 분리해 새 코드 수정 PR로 처리한다.
