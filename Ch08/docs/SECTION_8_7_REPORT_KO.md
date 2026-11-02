# SECTION 8.7 코드 리뷰 — TensorBoard·정량 평가·녹화

**기준:** 2026-10-20 / main `38fb4647aeff2d3ab951404d78e1812e598f2308`, 원고 8.7.1~8.7.3; `Ch08/ros2_ws/train_reach.py`, `evaluate_robot.py`, `evaluate_robot_record.py`, `rl_env.py`, `logs/tb/`.

**판정: TensorBoard 로그 경로 존재 / 정량 평가 메트릭 일부 무효 / MP4 녹화 차단 가능성 HIGH.** 파일 존재와 이벤트 내용을 실제로 분석했다는 뜻은 아니다. GUI, renderer, 평가 실행은 미수행.

## 발견 사항
| ID | 등급 | 파일 근거와 영향 | 권장 변경 |
|---|---|---|---|
| 8.7-R1 | BLOCKER | `ReachEnv.metadata.render_modes`에는 `rgb_array`가 있으나 `render()`는 human만 처리하고 RGB 배열을 반환하지 않음. `evaluate_robot_record.py`는 `RecordVideo(ReachEnv(render_mode="rgb_array"))` 호출 | 오프스크린 `mujoco.Renderer`로 `H×W×3 uint8` 구현 후 녹화 테스트; 수정 전 MP4 성공 주장 금지 |
| 8.7-R2 | HIGH | `evaluate_robot.py`는 `info['distance']`가 있을 때만 SSE 리스트에 축적; 실제 `ReachEnv.step` info에 `distance` 없음 → 0.0mm 출력은 **결측 처리 버그** | `distance` 직접 기록, 비어 있으면 N/A/테스트 실패 처리 |
| 8.7-R3 | HIGH | 정량 평가의 episode는 500 스텝에서 외부 반복만 중단. 환경의 `truncated`/훈련 TimeLimit이 아니다. | 평가/학습 시간 제한을 구분; 결괏값에 제한 규칙 기재 |
| 8.7-R4 | MEDIUM | 'Action Jerk Score'는 `mean ||action_t-action_(t-1)||`이지 물리 jerk(가속도 미분)도 전력 소비량도 아니다 | '평균 action 변화량'으로 정확히 표기 |
| 8.7-R5 | MEDIUM | TensorBoard 실제 학습 로그 경로는 `logs/tb/`, Monitor CSV는 `logs/monitor/`. 원고의 `tensorboard --logdir ./logs/`은 더 넓은 경로 | `tensorboard --logdir logs/tb`와 `rollout` 지표 유무 확인 |
| 8.7-R6 | MEDIUM | PPO scalar `entropy_loss` 부호·`value_loss` 크기는 단순히 0으로 감소해야 성공이라는 보장이 없다. episode 보상만으로 품질 확정 불가 | 평가 성공률·최종 거리·분산·복수 seed와 함께 해석 |
| 8.7-R7 | MEDIUM | `evaluate_robot_record.py`가 기존 ZIP을 로드하여 시도하지만 카메라 초기화/패키지 코덱 설치 보장 없음 | RGB 프레임 테스트 → 짧은 episode 녹화 → 파일 decode 확인 순서 |
| 8.7-R8 | LOW | `logs/tb/PPO_*`에는 과거 이벤트 파일이 존재함 | '저장소에 과거 로그 존재'와 이번 실행 결과를 분리, 실행 일시/실험 ID 기록 |

## 검증 계획
1. `env=ReachEnv(render_mode="rgb_array")`, `env.reset()`, `frame=env.render()`: `isinstance(frame,np.ndarray)`, `ndim==3`, 채널 수 3, uint8 확인. **현재는 None 예상**, 따라서 녹화 수행 중단.
2. `tensorboard --logdir logs/tb` 실행 후 `train/approx_kl`, `train/value_loss`, `rollout/ep_rew_mean` 존재 여부 확인(로그가 부족하면 없는 것이 정상일 수 있음).
3. 기존 학습 모델로 다양한 시드/100 episode 평가, 성적표에 `success_rate, final_distance, return, step_count, action_delta` 사용; 결측은 실패 표시.
4. RGB 구현을 수정한 이후에만 녹화/비디오 열기 확인. 원본을 변경하지 않은 이 브랜치에서는 막힌 테스트로 기록.

**증거 상태:** 소스 정적 리뷰 완료, 분석/렌더/MP4 실제 검증 미수행. 문서만 추가한다.

[실습 가이드](LAB_8_7_GUIDE_KO.md) · [Gymnasium RecordVideo](https://gymnasium.farama.org/main/api/wrappers/misc_wrappers/#gymnasium.wrappers.RecordVideo)
