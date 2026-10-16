import time
import mujoco
import mujoco.viewer

# 1. XML 모델 로드 (컴파일 단계)
# 모델 파일이 있는 경로를 정확히 지정해야 한다.
xml_path = "src/my_robot_description/urdf/hello_mujoco.xml"
model = mujoco.MjModel.from_xml_path(xml_path)

# 2. 데이터 구조 생성 (런타임 단계)
data = mujoco.MjData(model)

# 3. 뷰어(Visualizer) 실행 및 시뮬레이션 루프
# 'with' 문을 사용하여 뷰어를 안전하게 열고 닫는다.
print("MuJoCo 시뮬레이션을 시작한다. (종료하려면 ESC)")
with mujoco.viewer.launch_passive(model, data) as viewer:
    start_time = time.time()
    
    # 뷰어가 켜져 있는 동안 반복
    while viewer.is_running():
        step_start = time.time()

        # [핵심] 물리 엔진을 한 스텝 진행시킨다.
        # mj_step은 data 내부의 qpos(위치), qvel(속도)를 갱신한다.
        mujoco.mj_step(model, data)

        # 뷰어에 변경된 데이터를 반영하여 화면을 갱신한다.
        viewer.sync()

        # 시뮬레이션 속도 조절 (실시간 속도에 맞추기 위함)
        # timestep(0.002)보다 계산이 빠르면 잠시 대기
        time_until_next_step = model.opt.timestep - (time.time() - step_start)
        if time_until_next_step > 0:
            time.sleep(time_until_next_step)

print("시뮬레이션 종료.")
