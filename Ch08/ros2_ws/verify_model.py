import mujoco
import os

model_path = "src/my_robot_description/urdf/two_dof_arm.xml"

if not os.path.exists(model_path):
    print(f"파일 없음: {model_path}")
else:
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)
    
    print("="*50)
    print("[MuJoCo XML 모델 검증 리포트]")
    print("="*50)
    print(f"1. 모델에 정의된 관절 수 (nu/qpos): {model.nq}")
    print(f"2. 모델에 정의된 액추에이터(모터) 수 (nu): {model.nu}")
    print(f"3. 시뮬레이터 ctrl 배열의 실제 크기: {data.ctrl.shape}")
    print("-"*50)
    
    # 실제 액추에이터 이름들 출력해보기
    print("4. 등록된 액추에이터 이름 목록:")
    for i in range(model.nu):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        print(f"   - Actuator {i}: {name}")
    print("="*50)