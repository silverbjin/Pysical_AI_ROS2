# Ch08 §8.6 학습 코드 수정·정적 테스트 보고서 (2026-10-21)

## 수정 및 보호
- 기존 브랜치: `docs/ch08-section-8-6-review-lab`, 변경 파일: `Ch08/ros2_ws/train_reach.py`
- 원본 blob: `f0beb59e80e3ab205d1152977857a6a9bb74f083`; 수정 커밋: `72fd6688e9888457098afd43151ff5008efed5e9`
- 기존 문제: 100만/200만 학습 안내 불일치, 시드 부재, 에피소드 무한 지속 가능, `models/ppo_reach_final.zip` 덮어쓰기, 검증되지 않은 성공 표현.
- 해결: CLI 학습량과 고정 seed, `TimeLimit(500)`, 관측 18D/행동 6D 환경 확인, 고유 `runs/<run_name>/` 폴더, JSON manifest, 완료/중단 모델명 구분, checkpoint 보존.
- 기존 pretrained 모델 파일은 수정하지 않았으며 모델 계약 변경으로 재학습 필요 여부는 실제 평가 후 판단.

## 실제 수행한 소스 정적 계약 검사
| 정적 검사항목 | 방법 | 결과 |
|---|---|---|
| `TimeLimit(env, max_episode_steps=` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `env.seed(args.seed)` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `seed=args.seed` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `exist_ok=False` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `check_env(probe, warn=True)` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `args.timesteps` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `ppo_reach_interrupted` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `manifest.json` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
| `finally:         env.close()` | 수정할 전체 파일 텍스트의 필수 계약 확인 | PASS |
**STATIC_CONTRACT_PASS 9건**; **SYNTAX_PASS NOT_RUN** (로컬 컴파일 미수행); **RUNTIME_PASS NOT_RUN** (SB3/MuJoCo 미설치); **TASK_PASS NOT_RUN** (PPO 학습·목표 성공 미검증).

## 실행·회귀 검증(환경에서 수행 필요)
```bash
cd Ch08/ros2_ws
python -m py_compile train_reach.py
python train_reach.py --timesteps 2048 --seed 42 --max-episode-steps 500
# runs/<run_id>/manifest.json + models/*.zip 검사, SB3/Gymnasium 확인
```
- 학습 smoke 완료와 성공률 검증은 다른 Acceptance. 평가는 §8.7의 도구로 별도 수행.
- 이미 생성된 파일과 덮어쓰기 방지를 위해 같은 `--run-name` 사용 시 명시적 실패가 정상.
- 기준 `main`을 수정하지 않았으며 PR 생성 없음.
