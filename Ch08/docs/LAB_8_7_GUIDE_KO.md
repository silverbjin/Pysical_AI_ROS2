# LAB 8.7 — TensorBoard, 평가 메트릭, RGB 녹화 사전점검

**학습 목표:** PPO 학습 로그를 읽고 무효 수치를 걸러내며, 영상 제작에 필요한 RGB 렌더 계약을 테스트한다. Ch12와 같이 **실행 증거/실패 증거/한계**를 구분해 제출한다.

## 준비
```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
source .venv/bin/activate
python -m pip install tensorboard moviepy imageio imageio-ffmpeg numpy
```
학습 환경 의존성은 8.6절과 동일. TensorBoard 서버를 외부 전체 네트워크에 노출하지 않고 로컬에서 사용한다.

## 1. TensorBoard 시연
```bash
tensorboard --logdir logs/tb --host 127.0.0.1 --port 6006
```
브라우저: http://localhost:6006/ . **기존 `logs/tb/PPO_*` 이벤트는 이전 실행의 결과**이므로 새 실험의 성능으로 인용하지 않는다. 그래프가 비어 있다면 해당 지표가 저장되지 않았거나 이력이 부족한지 먼저 확인한다.

## 2. 원리 분석
- `rollout/ep_rew_mean`: 수집된 episode 평균 return. 에피소드 종료가 드물면 비거나 왜곡된다.
- `train/value_loss`: 가치함수 손실. 무조건 0에 수렴해야 하는 지표가 아니다.
- `train/entropy_loss`: 이름에 loss가 있어 부호가 정책 엔트로피와 다르다. 학습/평가 지표와 함께 읽는다.
- `train/approx_kl`: PPO 업데이트 진단값, 성공률 자체는 아니다.

## 3. 정량 평가(현 코드의 결측을 관찰)
```bash
python evaluate_robot.py
```
저장된 `models/ppo_reach_final.zip`을 사용한다. ZIP이 현재 6DOF 환경과 호환되지 않으면 **정상 실패 증거**로 남기고 차원/버전을 조사한다. 출력에 '정착 오차 0.0 mm'가 있더라도 실제 `info`에 `distance`가 없어 결측 처리된 것일 수 있으므로 **성능 입증에 사용하지 않는다.**

```bash
python - <<'PY'
from rl_env import ReachEnv
env=ReachEnv(render_mode=None)
try:
    env.reset(seed=3)
    _,_,_,_,info=env.step(env.action_space.sample())
    print("info keys", sorted(info))
    print("distance available?", "distance" in info)
finally: env.close()
PY
```

## 4. 녹화: 차단 조건 먼저 재현
```bash
python - <<'PY'
import numpy as np
from rl_env import ReachEnv
env=ReachEnv(render_mode="rgb_array")
try:
    env.reset(seed=3)
    frame=env.render()
    print("frame type",type(frame),"shape",getattr(frame,"shape",None))
    if not (isinstance(frame,np.ndarray) and frame.ndim==3 and frame.shape[-1]==3):
        print("BLOCKED: RGB 렌더러가 없으므로 RecordVideo를 실행하지 않음")
finally: env.close()
PY
```
현재 소스에서는 `render()`가 None을 반환하므로 비디오 성공을 기대할 수 없다. 구현 수정 후 `H×W×3 uint8` 보장, 모의 1 episode `RecordVideo`, MP4 파일 크기·프레임 재생 검사를 순서대로 수행한다. **이 브랜치는 소스 수정 없이 문제를 기록한 문서다.**

## 5. 평가 과제·인수 조건
학습 곡선 3개 해석(보상/손실/정책 업데이트)과 시드별 성공률·최종 거리·action delta의 차이를 논한다. 로그 주소·실험 run ID·모델 해시·결측 항목을 함께 제출한다. '실행 실패'와 '학습 실패'는 구분한다.

[리뷰 보고서](SECTION_8_7_REPORT_KO.md)
