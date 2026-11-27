# G07 최종 인수 보고서 — T16/T17

## 범위 및 디버깅 이력
- RED1 [45952688381](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45952688381): 빌드/설치 성공, tzdata 누락 pip check FAIL. 물리 NOT_RUN. 원본 ZIP+6 확인, [디버깅 보고서](G07_RED1_DEPENDENCY_DEBUG_KO.md).
- V2 [45952988010](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45952988010), job140352899966, artifact15177811443, source e223f8940315d872e77c74b3148dbde15cd1dfc1. ZIP SHA256 44f3c9e89b281a0bfc8f70abc1aa0bc838e800abbbd92e6da0452feedafb87ad, 내부30/30 독립검증. 3개 빌드/설치, local wheel lock18/18, pip check, unit7/7 PASS. 기존 합격 기준/게인/모델 변경 없음.

## 실제 1DOF 결과 (MuJoCo 3.3.7)
각 4초 200Hz 800 step, gravity0, q_ref1rad, motor ±60Nm, joint ±2rad.
| 조건 | RMSE rad | overshoot % | 정착 s | 마지막 .5s 최대오차 rad |
|---|---:|---:|---:|---:|
| A 부족감쇠 | .349641 | 72.238844 | 미도달 | .128716 |
| B 튜닝 | .247561 | 0 | 1.230 | .003945 |
| C 과감쇠 | .313699 | 0 | 2.885 | .010435 |
| inertia +10% | .250053 | 0 | 1.170 | .003878 |
| damping half | .245621 | 0 | 1.170 | .003914 |
| delay 20ms | .249141 | 0 | 1.250 | .003964 |
PID5/5 PASS, robustness7/7 PASS. B baseline CSV hash reuse; delay applied[0:4]=0 then exact clipped[-4], no missing/NaN or limit violation, actual actuator=applied. CSV 4800 rows independently recomputed time/step, RMSE, overshoot, final error, limits, force and delay. B가 A보다 개선되며 C보다 빠르게 정착한다. 강건성은 정의된 세 조건만 해당.

## 합성 LPF
Seed15, 800 samples, alpha .2. RMSE .194290414→.108853930, lag4 samples=20ms. 합성 fixture를 실제 센서 데이터로 해석하지 않음. Raw seed 및 RMSE 독립 재계산. 세 PNG와 원본 CSV/JSON은 CI artifact. [Receipt](../../evidence/g07/final_receipt.json).

## 결론
PASS_SCOPED_G07_T16_T17. G04~G06 성공 경로 재실행 없음. 실물, 전체 로봇 관절 제어, PPO, WSL2 owner L3, 시각적 GUI 검수 미수행. Ch01~14 불변, main merge HOLD. G08 safety/recovery를 별도 검수 단위로 진행.
