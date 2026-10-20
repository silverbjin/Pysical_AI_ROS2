# LAB 8.2 — MuJoCo 설치, MJCF 검사, 낙하 시뮬레이션

**학습 목표:** MuJoCo의 `MjModel`과 `MjData`, `qpos/qvel/ctrl`, 자유관절·hinge·actuator의 차이와 XML 파일 로딩을 실습한다. Ch12의 '설치→명령→관찰→실패 분석' 구조를 따른다.

## 1. 사전 준비
Ubuntu 24.04/WSL2, Python 3.12 기준. WSLg 뷰어는 화면 서버가 필요하다. ROS 2는 이 Python 예제의 필수 요건이 아니다. 저장소의 실제 위치에 맞게 `cd`한다.

```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install mujoco numpy
python -c 'import mujoco; print("MuJoCo", mujoco.__version__)'
```

## 2. 시연: 공 낙하
```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
source .venv/bin/activate
python run_mujoco.py
```

빨간 공이 떨어지며 지면과 접촉하는 장면을 관찰한다. 종료는 뷰어 닫기 또는 Ctrl+C. GUI가 없는 경우 뷰어 검증은 보류하고 아래의 헤드리스 물리 테스트만 실행한다.

## 3. 원리 확인: 모델/데이터/관절
```bash
python - <<'PY'
from pathlib import Path
import mujoco
base = Path.cwd()
files = [
    "src/my_robot_description/urdf/hello_mujoco.xml",
    "src/my_robot_description/assets/simple_arm_3dof.xml",
    "src/my_robot_description/assets/simple_arm_6dof.xml",
]
for name in files:
    model = mujoco.MjModel.from_xml_path(str(base / name))
    data = mujoco.MjData(model)
    print(name, "nq=",model.nq,"nv=",model.nv,
          "nu=",model.nu,"timestep=",model.opt.timestep,
          "ctrl_shape=",data.ctrl.shape)
PY
```

예상 구조: 공에는 freejoint, 3DOF 팔에는 관절/모터 각 3개, 6DOF 팔에는 각 6개가 존재한다. `nq`와 `nv`는 freejoint 때문에 다를 수 있다. 구체적인 출력은 사용한 XML 버전에 따라 달라진다.

## 4. 헤드리스 공 낙하 검증
```bash
python - <<'PY'
import mujoco
p="src/my_robot_description/urdf/hello_mujoco.xml"
m=mujoco.MjModel.from_xml_path(p)
d=mujoco.MjData(m)
start=float(d.qpos[2])
for _ in range(250):
    mujoco.mj_step(m,d)
print("start_z",start,"end_z",float(d.qpos[2]),"time",float(d.time))
assert d.time > 0
assert float(d.qpos[2]) < start, "중력 낙하가 관측되지 않음"
PY
```

## 5. 응용·문제 해결
- `timestep=0.002`와 250 step은 이론상 0.5초다. `time` 출력으로 확인.
- `FileNotFoundError`면 현재 경로를 `pwd`로 점검. `Ch08/ros2_ws`에서 다시 실행.
- WSLg에서 창이 안 뜨면 `echo "$DISPLAY"`, 그래픽 세션을 확인하고 헤드리스 결과와 구분.
- `simple_arm_3dof.xml`의 `gear` 값 변경은 action-to-torque 스케일을 바꾼다. **실제 로봇 하드웨어에는 연결하지 않는다.**
- 결과물: 터미널 출력·사용 버전·뷰어 캡처(가능한 경우)와 한 줄 해석.

**통과 기준:** MJCF 세 파일 로드, 공 낙하 확인, 3DOF/6DOF 모델 차이를 설명. 실물 실행 결과가 없으면 미검증으로 표시한다.

[리뷰 보고서](SECTION_8_2_REPORT_KO.md)
