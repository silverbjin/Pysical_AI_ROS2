# SECTION 8.6 코드 리뷰 — PPO 학습·정책 추론

**기준:** 2026-10-20 / main `38fb4647aeff2d3ab951404d78e1812e598f2308`. 첨부 원고 8.6.1~8.6.4, `Ch08/ros2_ws/train_reach.py`, `rl_env.py`, `test_model.py`, `models/ppo_reach_final.zip`의 존재 여부, Ch12의 PPO 보고서/가이드 구성을 확인.

**판정: 학습 API 연결은 존재하나, 학습 목표/종료 조건·재현성·모델 정합성 검증 필요.** 현재 환경에 MuJoCo/SB3가 없어 학습 업데이트·PPO 성공률·시각 추론의 동작은 실행 검증하지 못함. 모델 ZIP 파일이 Git에 있다고 해서 이번 세션에서 해당 모델의 품질을 검증한 것은 아니다.

## 코드 구조
`train_reach.py`는 `check_env(ReachEnv)` → `Monitor` → `DummyVecEnv([env_fn])` → `PPO("MlpPolicy", ..., device="cpu")` → `CheckpointCallback` → `learn` → `model.save` 순서. `test_model.py`는 `PPO.load` 후 1000 action 예측을 수행한다. 실제 환경 관측은 **18차원**, 행동은 **6차원**이며, 원고의 3자유도 정책과 호환되지 않는다.

## 핵심 이슈
| ID | 수준 | 코드·원고 불일치 | 수정 제안 |
|---|---|---|---|
| 8.6-R1 | HIGH | `rl_env.step`는 목표 성공 이외 `truncated=False`로 고정. `train_reach.py`는 `TimeLimit` 미사용 | `TimeLimit(max_episode_steps=300~500)` 적용; 종료/타임아웃 차별적 평가 |
| 8.6-R2 | HIGH | 원고 `total_timesteps=1_000_000`; 현재 `train_reach.py`는 **2_000_000**, 기본 호출시 장시간 작업 시작 | smoke CLI 옵션과 본 학습 옵션 분리; 명령별 스텝 명시 |
| 8.6-R3 | HIGH | 정책 ZIP의 관측/행동 차원, XML SHA, MuJoCo 버전, 보상 가중치 메타데이터 계약 없음 | 저장 전/로드 후 observation_space/action_space·모델/코드 버전 검사 |
| 8.6-R4 | MEDIUM | 학습 시드 미지정, 개별 실행에서 동일 logs/models 디렉터리 공유, 기존 파일 덮어쓰기 위험 | 개별 run ID, seed, manifest, overwrite 방지 |
| 8.6-R5 | MEDIUM | `DummyVecEnv` 하나는 병렬 처리 아님. 본문은 SubprocVecEnv를 소개하나 현재 스크립트는 사용하지 않음 | 1환경 PPO임을 설명; 병렬화는 추가 설계에서 시험 |
| 8.6-R6 | MEDIUM | `CheckPointCallback(save_freq=100000)`, 실제 2M 학습; `KeyboardInterrupt` 후에도 같은 `ppo_reach_final.zip` 저장 | 완료/중단 별도 이름과 상태 기록 |
| 8.6-R7 | MEDIUM | `test_model.py`의 설명은 20Hz지만 실제 XML 0.002s×5=100Hz; 환경이 timeout을 반환하지 않아 실패 episode가 reset 안 될 수 있음 | 표시 지연과 시뮬레이션 시간 분리; 별도 max_steps |
| 8.6-R8 | MEDIUM | PPO clip_range=.2를 '정책 변화 20% 보장'으로 해석한 원고 | 확률비 objective의 클리핑으로 설명; 글로벌 파라미터/성능 상한 아님 |
| 8.6-R9 | LOW | `check_env` 출력에 '100% 통과' 표현이 있으나 체크 항목은 API 적합성 일부 | 제어 역학·성공률·렌더링 보증 아님을 기록 |

## 검증 설계
1. **환경 API:** `check_env(ReachEnv(render_mode=None))` 정상 종료 여부.
2. **PPO smoke:** 작은 `n_steps/batch_size`와 128~256 timesteps로 rollout 수집·학습·ZIP 저장·재로드·predict action shape 확인. 문서 내 임시 명령 사용하며 기존 최종 모델을 덮어쓰지 않는다.
3. **정량 평가:** 별도 시드의 최소 20 episode, episode별 500 step 상한, 성공률·목표 거리·보상·action change 기록. 매 평가 조건/모델 해시 보관.
4. **장기 학습:** 별도 승인·리소스 확보 뒤 다중 seed·학습 곡선으로 재현성 검증. smoke 성공으로 목표 도달 학습이 완료됐다고 보지 않는다.

**검증 증거:** 일시, Python/MuJoCo/Gymnasium/SB3/PyTorch 버전, 명령·exit code, 실패 traceback, 모델 파일 SHA256, 평가 분포. **실제 동적 검증은 미수행**.

[실습 가이드](LAB_8_6_GUIDE_KO.md) · [Ch12 PPO 가이드](../../Ch12/docs/LAB_12_4_GUIDE_KO.md)
