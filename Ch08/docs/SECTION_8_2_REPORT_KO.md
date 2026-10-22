# SECTION 8.2 코드 리뷰 — MuJoCo 모델과 실행

**판정: 조건부 실행 가능 / 실제 실행 미검증.** 2026-10-20, main `38fb4647aeff2d3ab951404d78e1812e598f2308`. 첨부 원고 8.2.1~8.2.5 및 GitHub `Ch08/ros2_ws/` 코드를 대조했다. 이 세션의 작업 컨테이너에는 `mujoco`가 설치되지 않았고 GitHub로의 로컬 네트워크 연결이 차단되어 **실제 MuJoCo 뷰어/물리 실행은 수행하지 못했다**. 이 문서의 PASS 예시는 실제 성공 기록이 아니다.

## 확인한 파일
- `run_mujoco.py`: `src/my_robot_description/urdf/hello_mujoco.xml` 로드, `mj_step`/passive viewer/실시간 동기화
- `src/my_robot_description/urdf/hello_mujoco.xml`: 0.002초 timestep, 6자유도 자유관절 빨간 구체
- `src/my_robot_description/assets/simple_arm_3dof.xml`: 3 hinge/3 motor, `link_ee`, 비충돌 mocap 목표
- `src/my_robot_description/assets/simple_arm_6dof.xml`: **6 hinge/6 motor**, `link_ee`, `ee_site`, mocap 목표
- `verify_model.py`: 2DOF 모델을 별도로 검사; 3/6DOF 학습 모델의 검증 근거가 아님.

## 발견 사항
| ID | 등급 | 현상·원인 | 권장 수정 |
|---|---|---|---|
| 8.2-R1 | HIGH | `run_mujoco.py`와 `verify_model.py`는 상대경로를 사용한다. 저장소 루트 또는 다른 작업 디렉터리에서 실행하면 파일을 찾지 못할 수 있다. | `__file__` 기반 절대 경로, 경로 인자 또는 `cd Ch08/ros2_ws` 명시 |
| 8.2-R2 | HIGH | 원고 8.2·8.4는 3자유도 학습인데 현재 주력 `rl_env.py`는 `simple_arm_6dof.xml`을 로드한다. | 3DOF 기초/6DOF 확장을 명시적으로 분리; 정책·관측 계약도 분리 |
| 8.2-R3 | MEDIUM | MJCF motor는 이미 `gear=50,50,30` (6DOF는 50,50,30,10,5,2)를 정의한다. 이 값과 Python `ctrl`에 다시 토크 50배를 넣는 로직을 혼합하면 제어 계약이 틀어진다. | `ctrl` [-1,1] 정규화와 gear 증폭을 구분; clipping/ctrlrange 테스트 |
| 8.2-R4 | MEDIUM | 본문에 MuJoCo를 일반적으로 '미분 가능한 물리 엔진', Gazebo보다 무조건 빠르거나 접촉에 항상 우월하다고 설명한 부분은 과장될 수 있다. | MuJoCo의 접촉 역학 강점과 별도 differentiable 엔진(MJX 등)의 특징 분리; 성능 비교는 측정치 필요 |
| 8.2-R5 | MEDIUM | ROS 패키지의 `setup.py`는 `urdf/*.urdf`/ `*.xacro`만 설치하며 MJCF `*.xml`과 `assets/*.xml`은 설치하지 않는다. | Python 원본 경로 실행과 `ros2 run` 설치 리소스 사용을 혼동하지 않도록 구성 |
| 8.2-R6 | LOW | `requirements-local-snapshot.txt`는 환경 전체 스냅샷이므로 최소 재현 의존성 명세가 아니다. | 필요한 패키지/버전/GUI 조건 별도 명시 |

## 테스트 설계
1. `cd Ch08/ros2_ws`; `python -c "import mujoco; print(mujoco.__version__)"`.
2. Python으로 세 MJCF 파일을 각각 `MjModel.from_xml_path`하여 `nq, nv, nu, opt.timestep, body/actuator`를 출력한다.
3. `python run_mujoco.py` 실행 시 뷰어가 열리고 공이 바닥에 도달하는지 육안으로 기록한다. GUI 없음/WSLg 오류와 XML 파싱 오류를 구분.
4. 제어 명령의 범위·엔진 내부 힘 관계를 검사할 때 모델의 `actuator_gear`, `actuator_ctrlrange`, `actuator_ctrllimited`를 같이 기록한다.

## 인수 기준
XML 3종 컴파일, 3DOF 3개/6DOF 6개 motor 확인, 공이 낙하하는 영상 혹은 위치 로그, ROS 미설치 조건에서 Python 시뮬레이션 독립 실행을 증거로 남길 것. **현재 상태: 미실행/미검증.** 이 PR 후보는 문서만 추가하며 코드 변경을 포함하지 않는다.

[실습 가이드](LAB_8_2_GUIDE_KO.md) · [Ch12 문서 패턴](../../Ch12/README.md)
