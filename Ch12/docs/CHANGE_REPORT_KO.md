# 12.1절 구현 및 실제 실행 검증 보고서

검증일: 2026-10-17 KST. 대상 리포지토리: `silverbjin/Pysical_AI_ROS2`.
시작 커밋: `58fb5a0`. 작업 브랜치: `feat/ch12-section-12-1`.

## 구현한 내용

기존 리포지토리에는 Ch01~Ch11만 있었으므로 Ch12에 설치 가능한 Python 패키지 `physical-ai-quadruped-rl`을 추가했다. 기존 Ch11 소스는 변경하지 않는다.

| 파일 | 변경 내용 |
|---|---|
| `pyproject.toml` | Python 패키지·의존성·CLI·MJCF 포함 설정 |
| `src/quadruped_rl/models/quadruped.xml` | 자유 몸체, 12관절, 12 토크 actuator, 마찰 지면 |
| `src/quadruped_rl/env.py` | Gymnasium reset/step/render/close, 시드·관측·보상·종료 |
| `src/quadruped_rl/demo.py` | random/stand 실험, GUI, JSON 실행 요약 |
| `scripts/verify_mujoco.py` | 실제 엔진 반복 실행과 선택 RGB 이미지 검증 |
| `scripts/verify_gazebo.sh` | 기존 Ch11 빌드·회귀·실제 기립 관측·종료 검증 |
| `tests/` | 물리 엔진을 사용하는 환경 계약·입력·재현성·CLI·RGB 테스트 |
| `docs/LAB_12_1_GUIDE_KO.md` | 설치, 실습 순서, 상태·행동·보상 해석, Gazebo 비교 |
| `docs/DESIGN_KO.md`, `IMPLEMENTATION_PLAN_KO.md`, `REVIEW_KO.md` | 승인 설계, 실행 계획, 독립 리뷰 기록 |

본문 코드의 생략된 model/data 생성, 토크 변환, 실제 `mj_step`, 관측 계산, 보상과 종료를 구현했다. 기본 관측 30차원을 유지하고, 본문에 열거된 선속도·직전 행동까지 포함하는 45차원 모드를 추가했다. 관절과 actuator는 이름으로 매핑한다.

잘못된 행동 크기와 NaN/Inf는 물리 상태를 변경하기 전에 거부한다. 유한한 범위 초과 행동은 제한하고 info에 표시한다. 낙상과 시간 제한을 각각 terminated와 truncated로 반환하며, 종료 후 step은 reset을 요구한다. 렌더러와 viewer는 close에서 정리한다.

## 검증 환경

- Windows 호스트의 Ubuntu-24.04 WSL2, WSLg 사용.
- Python 3.12.3, MuJoCo 3.3.7, Gymnasium 1.2.1, NumPy 2.5.4.
- ROS 2 Jazzy를 source한 실행 환경의 Gazebo Sim 8.11.0 (Harmonic).
- 최초 source 전 조회는 8.14.0이었으나, 실제 ROS launch 검증에서는 Jazzy가 설정한 8.11.0 경로를 사용했다.
- 학습 의존성은 격리된 가상환경에 설치했다. 실제 테스트는 파일 생성이 빠른 WSL 임시 영역의 환경에서 수행했다. ROS 노드는 시스템 Python을 사용했다.

## MuJoCo 결과

| 검사 | 결과 |
|---|---|
| 환경 계약·시드·토크·입력 검증·종료·CLI·실제 EGL 렌더링 | pytest 23개 통과, skip 0개 |
| Gymnasium checker | 30/45차원 모두 통과 |
| 반복 물리 실험 | 2개 관측 모드 × 2개 정책 × 3개 seed × 1,000 스텝 = 12,000 제어 스텝 |
| PD 자세 유지 | 6개 실행 모두 낙상 0회, 각각 물리 10초 완료 |
| 무작위 행동 | seed 0/42/123에서 실행당 낙상 27/24/23회, reset 후 계속 실행 |
| RGB 렌더링 | 실제 EGL 640×480 이미지 생성 및 육안 확인 |
| viewer | 설치된 wheel에서 WSLg 창 실행, 물리 1초 진행, close 확인 |
| wheel 설치 | 소스 폴더 밖 `/tmp`에서 CLI와 포함된 MJCF 로드·실행 통과 |

PD 실험의 전체 최소 몸체 높이는 0.392179 m, 최대 기울기는 0.634409°였다. 목표 전진 속도는 이 검증에서 0 m/s다. 이는 PD 기립 baseline 검증이며, 학습된 보행이나 외란 회복을 검증한 결과가 아니다.

`Box(-inf, inf)`는 본문 규격을 유지하므로 checker가 상·하한 관련 경고 4개를 출력한다. 테스트 실패는 없으며 경고를 숨기지 않았다. 향후 학습에서는 관측 정규화와 범위 설정을 별도로 설계해야 한다.

## Gazebo 결과와 종료 검증

기존 Ch11 회귀 테스트 104개가 통과했고 두 ROS 패키지 빌드가 성공했다. 실제 로봇 스폰 후 시뮬레이션 8.024~38.046초 구간을 관측했다. 첫 실행은 높이 0.247981~0.249038 m, 최대 기울기 1.267473°, 수평 이동 약 1.15 mm였고 관절·IMU·자세·오도메트리·LiDAR·TF 검사가 모두 통과했다.

첫 실행 종료 중 ROS 예외를 발견하여 관측 통과와 종료 성공을 분리했다. 프로세스 그룹 전체의 중복 SIGINT 가능성, Bash 백그라운드 작업의 SIGINT 무시 상속, 좀비 프로세스 판정 문제를 순차적으로 조사했다. launch 전 SIGINT 기본 동작을 복원하고, launch 부모에게 한 번 전달하여 정상 전파하게 했다. 이후 ROS 노드는 정상 종료했지만 Gazebo CLI 래퍼가 남는 것을 확인했다. 공식 `/server_control` 서비스에 `stop: true`를 보내는 독립 실행에서 정상 종료를 확인한 뒤 통합했다. 대기 중에는 실행 중인 프로세스만 판정하며 시간 제한 뒤 TERM/KILL을 사용한다. 종료 서비스의 승인 응답이 없거나 강제 정리·오류 로그가 있으면 최종 PASS로 인정하지 않는다. 서비스는 실험 고유 GZ_PARTITION에만 전달한다.

최종 실행은 **PASS**다. 시뮬레이션 8.024~38.046초에서 높이 0.249265~0.250299 m, 최대 기울기 1.115032°, 수평 이동 1.134 mm를 기록했다. 실제 모델 관측 1,119개, 관절 상태 36,085개, IMU 3,805개를 수신했고, LiDAR 360개 반환 모두 유효했다. 여섯 데이터 스트림과 TF 검사를 통과했다. 종료 서비스 응답은 true, 강제 정리는 false이며 Gazebo와 ROS 실행 프로세스가 모두 정상 종료했다. 종료 후 관련 Gazebo·ROS launch·프로브 프로세스가 남지 않았음을 확인했다.

`shutdown_clean`의 판정 범위는 종료 승인, 강제 정리 없음, launch의 `[ERROR]`/Python traceback 없음이다. 최종 로그에는 `parameter_bridge`의 `Failed to delete datawriter`라는 **DDS 종료 진단 1건이 남았다**. 해당 프로세스는 정상 종료했고 기립·센서 검증에도 실패는 없었으나, 이 진단까지 해결했다고 주장하지 않는다. 실제 결과와 원문은 `evidence/gazebo/result.json`과 `launch.log`에 보존했다.

## 구현·리뷰에서 수정한 문제

1. **RGB import 범위:** `import mujoco.viewer` 때문에 RGB 경로에서 UnboundLocalError가 발생했다. viewer만 명시적으로 import하도록 수정하고 실제 렌더 테스트를 통과했다.
2. **과거 PASS 잔류:** Gazebo 조기 실패 때 이전 결과가 남을 수 있었다. 시작 시 초기화하고 관측 JSON과 종료까지 포함한 최종 JSON을 분리했다. 잘못된 DDS domain 입력으로 조기 실패 시 FAIL을 새로 기록하는 것을 확인했다.
3. **종료 검증:** 위 SIGINT·좀비 문제를 수정했다. 관측 통과만으로 전체 검증 통과를 주장하지 않도록 했다.
4. **Windows/WSL Git 줄바꿈:** WSL Git이 Windows 체크아웃의 CRLF를 다른 장의 변경으로 오인했다. 증거 수집에서는 `core.autocrlf=true`로 정규화한다. 다른 장의 코드를 수정하지 않는다.
5. **실행 파일 줄바꿈:** Ch12의 `.gitattributes`로 shell·Python·XML·TOML 파일의 LF를 지정하여 Windows 체크아웃 후 WSL 실행 시 줄바꿈 오류를 예방했다.

독립 리뷰의 두 중요 지적(오래된 결과·종료 대기)과 종료 서비스의 강제 종료 제한 지적을 반영했고, 환경·모델·CLI·패키지와 가이드에 남은 조치 지적은 없었다. 검토자도 Ubuntu-24.04에서 실제 MuJoCo 테스트 23개와 12 × 1,000 제어 스텝을 독립 실행하여 PASS를 확인했다. 관측 모드별 무작위 정책의 seed별 낙상 횟수와 stand의 무낙상 결과가 구현자 실행과 일치했다. Gazebo는 리뷰 지적을 반영한 뒤 구현자가 통합 재실행했다.

## 재현과 증거

```bash
python -m pip install -e './Ch12[test,visual]'
CH12_TEST_RENDER=1 MUJOCO_GL=egl python -m pytest Ch12 -q
MUJOCO_GL=egl python Ch12/scripts/verify_mujoco.py \
  --output Ch12/evidence/my_mujoco.json --image Ch12/evidence/my_frame.png
# 새 터미널, 학습용 venv 비활성 상태
bash Ch12/scripts/verify_gazebo.sh
```

- `env_red.log`, `demo_render_red.log`, `render_red.log`: 구현 전·수정 전 실패 증거.
- `all_green.log`, `mujoco.json`, `mujoco.log`, `mujoco_frame.png`: 전체 테스트·반복 물리·렌더링.
- `mujoco_human.json`, `wheel_*.log`, `wheel_smoke.json`: viewer·배포 설치 실행.
- `reviewer_tests.log`, `reviewer_mujoco.json`, `reviewer_mujoco.log`: 리뷰 담당의 실제 MuJoCo 독립 실행.
- `gazebo/`: 최종 빌드·기립 프로브·실행·종료 로그.
- `gazebo_shutdown_before.log`, `gazebo_parent_signal_failure.*`: 종료 조사 증거. 과거 실패를 최종 결과로 혼동하지 않는다.
- `gazebo_gui_signal_failure.*`: ROS는 정상 종료했지만 Gazebo 래퍼 종료에 실패한 중간 실행.
- `gazebo_stop_race_failure.*`: 종료 승인 직후 ROS 신호를 보내 CLI 종료와 경합한 중간 실행. 최종본은 정상 종료 로그를 제한 시간 동안 기다린다.
- `gazebo_early_failure/`: 잘못된 domain 입력의 조기 실패 검증. 이 디렉터리의 FAIL은 의도한 음성 검사다.
- `python_packages.txt`: 실제 설치 버전. `source_manifest.json`: 검증한 코드의 SHA-256.

## 해석 범위

MuJoCo 모델은 Ch11의 주요 제원을 반영했지만 센서 부착물·관성·충돌 형상·자체 충돌과 제어 계층에 차이가 있다. 엔진 간 동일 동역학 비교나 정책 이전을 보장하지 않는다. 45차원 관측도 완전한 마르코프 상태가 아니며, 이번 실습은 RL 인터페이스와 물리 실행의 입문용 기반이다. 실제 강화학습 수렴·보행·실물 로봇·Sim-to-Real 검증은 수행하지 않았다.

Gazebo 로그에는 기존 모델의 `base_footprint` 루트 관성을 KDL이 지원하지 않는다는 경고가 있다. 이번 작업에서 기존 모델은 유지했으며 실제 Gazebo 기립, 센서와 TF는 별도 프로브로 검사했다.
