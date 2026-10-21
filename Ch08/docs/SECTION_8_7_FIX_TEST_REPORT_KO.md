# Ch08 §8.7 평가·녹화 코드 수정 및 정적 검사 보고서 (2026-10-21)

## 수정된 소스
- 기존 브랜치: `docs/ch08-section-8-7-review-lab`; 변경 파일 3개.
- `Ch08/ros2_ws/evaluate_robot.py` — commit `71e81b34d649526a1cc7cb7db69d9d22e6fd837d`
- `Ch08/ros2_ws/recording_env.py` — commit `dfe2f3a7e127d46d8c07922987b6696e69a8b4c1`
- `Ch08/ros2_ws/evaluate_robot_record.py` — commit `55d5fc409050dfb828d0686b72a177e415e3cfac`
- 기존 결함: `info.distance` 없음 → 종단 오차 데이터를 수집하지 못해 평균 0mm로 잘못 표기. `render_mode='rgb_array'`를 지정해도 렌더링 프레임은 `None`; 녹화 불가.
- 수정: `info.distance`가 없으면 관측 18D의 `ee/target` 좌표로 거리를 계산하고 **측정 불가를 0으로 대체하지 않음**. 성공률은 명시된 `is_success`만 인정. 물리 jerk가 아닌 제어입력 변화량으로 지표 명칭 수정.
- `ReachRGBEnv`를 추가해 MuJoCo Renderer 실제 프레임을 제공; 녹화 래퍼가 이를 사용하며 close 시 자원 해제.
- 평가 정책 경로를 CLI에 명시하도록 변경하여 8.6의 독립 run 폴더와 호환. 환경 정책 관측/행동 공간 검사 추가.

## 실제 정적 계약 검사
| 검사 | 방법 | 결과 |
|---|---|---|
| `evaluate_robot.py: np.linalg.norm(obs[-6:-3] - obs[-3:])` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot.py: if not np.isfinite(distance)` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot.py: seed=seed + episode` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot.py: Mean \|delta action\|/step` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot.py: if model.observation_space != env.observation_space` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `recording_env.py: mujoco.Renderer(self.model` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `recording_env.py: return self._renderer.render().copy()` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot_record.py: RecordVideo(` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot_record.py: ReachRGBEnv()` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |
| `evaluate_robot_record.py: --model` | 저장 대상 전체 소스의 필수 API/분기 존재 검사 | PASS |

- **STATIC_CONTRACT_PASS (10건)**.
- **SYNTAX_PASS NOT_RUN** (원격 소스 Python 컴파일 미수행).
- **RUNTIME_PASS NOT_RUN** (MuJoCo/OpenGL/영상 인코더 미설치).
- **TASK_PASS NOT_RUN** (정책 성공률/영상 저장은 실측하지 않음).

## 실제 실행이 가능한 컴퓨터에서 확인
```bash
cd Ch08/ros2_ws
python -m py_compile evaluate_robot.py recording_env.py evaluate_robot_record.py
python evaluate_robot.py --model runs/<run_id>/models/ppo_reach_final.zip --episodes 10
python evaluate_robot_record.py --model runs/<run_id>/models/ppo_reach_final.zip --episodes 3
```
- 헤드리스 녹화는 MuJoCo가 지원하는 EGL/OSMesa 등 OpenGL 백엔드 설정 및 영상 인코더 설치가 필요할 수 있음.
- 종단 오차는 '모든 에피소드 마지막 프레임 거리'이지 엄밀한 steady-state error가 아님.
- 녹화 API 호환성은 지원 Gymnasium 버전에서 다시 확인 필요.
