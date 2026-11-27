# 15.7 가상 관절 튜닝 및 강건성 (G07 후보)
실제 HW 없음. WSL2 Ubuntu24.04/Jazzy. G07은 독립 MuJoCo 1DOF이며 제어 토픽 발행 없음. 모델은 설치 share 경로를 사용. apt Python/ROS와 venv를 분리하되 system-site-packages를 통해 기존 ROS overlay를 사용한다. joint.lock.txt는 cp312/Linux hash lock.
```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 -m venv --system-site-packages "$HOME/ch15-joint-venv"
"$HOME/ch15-joint-venv/bin/python" -m pip install --only-binary=:all: --no-deps --ignore-installed --require-hashes -r Ch15/requirements/joint.lock.txt
"$HOME/ch15-joint-venv/bin/python" -m pip check
P="$HOME/ch15-joint-venv/bin/python"
MODEL="$(ros2 pkg prefix --share ch15_simulation)/models/joint_lab.xml"
OUT="$HOME/ch15-joint-$(date +%s)"
export MUJOCO_GL=disable MPLBACKEND=Agg
"$P" Ch15/python/pid_experiment.py --model "$MODEL" --out "$OUT"
"$P" Ch15/python/robustness_experiment.py --model "$MODEL" --out "$OUT"
"$P" Ch15/python/filter_experiment.py --out "$OUT/filter"
```
A underdamped / B tuned / C overdamped. 4초/200Hz 실제 800스텝, 관절 ±2rad, torque ±60Nm. CSV에는 요청/clip/적용/실제 actuator torque 및 제어 계산 ns가 분리된다. B의 기준은 overshoot≤5%, 마지막 .5s 오차≤.02rad, A 대비 RMSE·overshoot 개선. Rise/settling 미도달 null. 강건성은 B CSV 재사용 후 inertia+10%, damping 반감, 20ms 명령 지연 각각 1조건. URDF friction과 MJCF frictionloss는 물리 엔진별 해석 차이를 설명한다. LPF는 seed15의 합성 데이터이고 실제 센서 노이즈를 의미하지 않는다. 강건 보행/학습/실제 전력에 대한 결론을 내리지 않는다. GUI는 별도 사용자 시각 검수.
