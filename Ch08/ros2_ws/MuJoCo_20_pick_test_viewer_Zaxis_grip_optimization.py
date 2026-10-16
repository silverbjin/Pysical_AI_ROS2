import time
import numpy as np
import mujoco
import mujoco.viewer

XML_PATH = "src/my_robot_description/urdf/my_robot_6D.xml"

EE_SITE = "grasp_site"
CUBE_SITE = "cube_site"

# LOCK_JOINT = 4
# LOCK_VALUE = -np.pi / 2.0

model = mujoco.MjModel.from_xml_path(XML_PATH)
data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
cube_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, CUBE_SITE)

finger1_geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "finger1_collision")
finger2_geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "finger2_collision")

cube_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")
finger1_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger1")
finger2_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger2")

def get_tcp():
    return data.site_xpos[ee_site_id].copy()

def get_cube():
    return data.site_xpos[cube_site_id].copy()

def step_sim(n=500, viewer=None):
    for _ in range(n):
        mujoco.mj_step(model, data)
        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

def open_gripper(viewer=None):
    # data.ctrl[6] = 0.0225
    # data.ctrl[7] = 0.0225
    data.ctrl[6] = 0.0
    data.ctrl[7] = 0.0

    step_sim(2000, viewer)

def close_gripper(viewer=None):
    # data.ctrl[6] = 0.0
    # data.ctrl[7] = 0.0
    data.ctrl[6] = 0.0225
    data.ctrl[7] = 0.0225

    step_sim(3000, viewer)
    
# def solve_ik(target_pos, max_iter=300, damping=0.05, alpha=0.5, pos_tol=1e-3, rot_tol=1e-2):
#     q=data.qpos[:6].copy()
#     q_min=model.jnt_range[:6,0].copy()
#     q_max=model.jnt_range[:6,1].copy()
#     free_idx=[0,1,2,3,4,5]
#     jacp=np.zeros((3,model.nv))
#     jacr=np.zeros((3,model.nv))
#     desired_z=np.array([0.0,0.0,-1.0])

#     for i in range(max_iter):
#         data.qpos[:6]=q
#         mujoco.mj_forward(model,data)
#         current_pos=get_tcp()
#         pos_error=target_pos-current_pos
#         R=data.site_xmat[ee_site_id].reshape(3,3)
#         current_z=R[:,2]
#         rot_error=np.cross(current_z,desired_z)

#         if np.linalg.norm(pos_error)<pos_tol and np.linalg.norm(rot_error)<rot_tol:
#             print(f"IK Converged in {i} iterations")
#             return q

#         mujoco.mj_jacSite(model,data,jacp,jacr,ee_site_id)
#         J_pos=jacp[:,free_idx]
#         J_rot=jacr[:,free_idx]
#         J=np.vstack((J_pos,J_rot))
#         # error=np.concatenate((pos_error,0.5*rot_error))
#         error=np.concatenate((pos_error,1.0*rot_error))
#         dq=J.T@np.linalg.inv(J@J.T+damping*np.eye(6))@error
#         q+=alpha*dq
#         q=np.clip(q,q_min,q_max)

#     print("IK Failed")
#     return q

import copy  # [추가] 파이썬 내장 복사 모듈 필요
# def solve_ik_pure(target_pos, max_iter=300, damping=0.05, alpha=0.5, pos_tol=1e-3, rot_tol=1e-2):
def solve_ik(target_pos, max_iter=300, damping=0.05, alpha=0.5, pos_tol=1e-3, rot_tol=1e-2):    
    # 1. 메인 시뮬레이션 data의 현재 상태를 복사하여 독립된 IK 연산용 샌드박스 생성
    # ik_data = mujoco.MjData(model)
    # mujoco.mj_cloneData(model, ik_data, data)
    # ik_data = mujoco.mj_copyData(ik_data, model, data) # 구버전 호환용 C API 매핑
    
    # ik_data = data.copy()
   
    ik_data = copy.copy(data)
    
    
    # 기존 변수 초기화 로직 유지 (ik_data 기반으로 안전하게 복사)
    q = ik_data.qpos[:6].copy()
    q_min = model.jnt_range[:6, 0].copy()
    q_max = model.jnt_range[:6, 1].copy()
    free_idx = [0, 1, 2, 3, 4, 5]
    
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    desired_z = np.array([0.0, 0.0, -1.0])

    for i in range(max_iter):
        # 2. 메인 data가 아닌 ik_data의 qpos를 업데이트
        ik_data.qpos[:6] = q
        
        # 3. 격리된 공간에서 Forward Kinematics 수행 (물리적 Contact 상태 오염 없음)
        mujoco.mj_forward(model, ik_data)
        
        # 4. get_tcp() 대신 ik_data의 site_xpos를 직접 참조하여 샌드박스 내 현재 위치 획득
        current_pos = ik_data.site_xpos[ee_site_id].copy()
        pos_error = target_pos - current_pos
        
        # 회전 오차 계산 (기존 로직 유지)
        R = ik_data.site_xmat[ee_site_id].reshape(3, 3)
        current_z = R[:, 2]
        rot_error = np.cross(current_z, desired_z)

        # 수렴 조건 판정
        if np.linalg.norm(pos_error) < pos_tol and np.linalg.norm(rot_error) < rot_tol:
            print(f"IK Converged in {i} iterations")
            return q

        # 5. Jacobian 및 변화량 계산도 모두 ik_data를 기반으로 진행
        mujoco.mj_jacSite(model, ik_data, jacp, jacr, ee_site_id)
        J_pos = jacp[:, free_idx]
        J_rot = jacr[:, free_idx]
        J = np.vstack((J_pos, J_rot))
        
        error = np.concatenate((pos_error, 1.0 * rot_error))
        dq = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(6)) @ error
        
        q += alpha * dq
        q = np.clip(q, q_min, q_max)

    print("IK Failed")
    return q

    
# def move_to_joint_target(q_target, viewer=None, max_steps=15000, joint_tol=1e-3):
#     q_target = q_target.copy()
#     # q_target[LOCK_JOINT] = LOCK_VALUE
#     data.ctrl[:6] = q_target
#     for i in range(max_steps):
#         # data.ctrl[LOCK_JOINT] = LOCK_VALUE
#         mujoco.mj_step(model, data)
#         if viewer is not None:
#             viewer.sync()
#             time.sleep(0.001)

#         err = np.linalg.norm(q_target - data.qpos[:6])
#         if err < joint_tol:
#             print(f"Joint Converged in {i} steps")
#             break

def move_to_joint_target(q_target, viewer=None, max_steps=1000, joint_tol=1e-3):
    q_target = q_target.copy()
    
    # 1. 이동 시작 시점의 현재 조인트 위치 캡처 (보간의 시작점)
    start_q = data.qpos[:6].copy()
    
    for i in range(max_steps):
        # 2. 현재 스텝(i)이 전체 제한 스텝(max_steps)에서 차지하는 진행률 계산 (0.0 ~ 1.0)
        t = i / float(max_steps - 1) if max_steps > 1 else 1.0
        
        # 3. 부드러운 가감속(Smoothstep)을 위한 코사인 보간 가중치 적용
        alpha = 0.5 * (1.0 - np.cos(np.pi * t))
        
        # 4. 시작점과 목표점 사이의 부드러운 중간 목표 조인트 각도 연산
        current_ctrl = (1.0 - alpha) * start_q + alpha * q_target
        
        # 5. 계산된 제어 입력을 엑추에이터에 인가
        data.ctrl[:6] = current_ctrl
        
        # 물리 엔진 1스텝 전진
        mujoco.mj_step(model, data)
        
        # 뷰어 동기화 및 타임 슬립 (기존 로직 유지)
        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

        # 6. 오차 판정 및 조기 종료 (기존 로직 유지)
        err = np.linalg.norm(q_target - data.qpos[:6])
        if err < joint_tol:
            print(f"Joint Converged in {i} steps")
            break

# for debugging: move_to_joint_target with debug info
def move_to_joint_target(q_target, viewer=None, max_steps=15000, joint_tol=1e-3, debug=False):
    q_target = q_target.copy()
    # q_target[LOCK_JOINT] = LOCK_VALUE
    data.ctrl[:6] = q_target

    for i in range(max_steps):
        # data.ctrl[LOCK_JOINT] = LOCK_VALUE
        mujoco.mj_step(model, data)

        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

        # ----------------------------------------------------
        # Lift 시작 후 초기 20 Step 디버깅
        # ----------------------------------------------------
        if debug and i < 20:
            print(f"\n========== Step {i} ==========")
            print("TCP       :", np.round(get_tcp(), 5))
            print("Cube      :", np.round(get_cube(), 5))
            print("Contacts  :", data.ncon)

            print("Finger-Cube Contacts")
            found = False

            for j in range(data.ncon):
                contact = data.contact[j]

                geom1 = mujoco.mj_id2name(
                    model,
                    mujoco.mjtObj.mjOBJ_GEOM,
                    contact.geom1
                )

                geom2 = mujoco.mj_id2name(
                    model,
                    mujoco.mjtObj.mjOBJ_GEOM,
                    contact.geom2
                )

                if (
                    ("finger" in geom1 and "cube" in geom2)
                    or
                    ("cube" in geom1 and "finger" in geom2)
                ):
                    found = True

                    print(f"[{j}] {geom1} <--> {geom2}")
                    print("Position :", np.round(contact.pos, 5))
                    print("Distance :", contact.dist)

            if not found:
                print("No Finger-Cube Contact")
        err = np.linalg.norm(q_target - data.qpos[:6])
        if err < joint_tol:
            print(f"Joint Converged in {i} steps")
            break
                
def print_pick_frame_info():
    tool0_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "tool0")
    gripper_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "gripper_base")
    finger1_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger1")
    finger2_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger2")

    print("\n==============================")
    print("Pick Pose Frame Info")
    print("==============================")

    print("ee_site      =", np.round(get_tcp(), 6))
    print("tool0        =", np.round(data.xpos[tool0_id], 6))
    print("gripper_base =", np.round(data.xpos[gripper_id], 6))
    print("finger1      =", np.round(data.xpos[finger1_id], 6))
    print("finger2      =", np.round(data.xpos[finger2_id], 6))
    print("\nCube")

    print("cube         =", np.round(get_cube(), 6))
    print("cube-ee_site =", np.round(get_cube() - get_tcp(), 6))

def print_ee_orientation():
    R=data.site_xmat[ee_site_id].reshape(3,3)
    print("\nEE Orientation")
    print("X =",np.round(R[:,0],3))
    print("Y =",np.round(R[:,1],3))
    print("Z =",np.round(R[:,2],3))

# debugging report: States diagnostic
def print_diagnostic_report(model, data, step_name):
    """
    진단을 위해 필요한 로봇과 물체의 상태 로그를 출력하는 레포트 함수
    """
    print(f"\n📊 ==================== [디버깅 리포트: {step_name}] ====================")
    
    # 1. 물체(Cube) 정보 추출
    cube_pos = None
    try:
        cube_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")
        cube_pos = data.xpos[cube_id]
        print(f"[물체 상태] Cube 중심 위치   (X, Y, Z) : {cube_pos[0]:.4f}, {cube_pos[1]:.4f}, {cube_pos[2]:.4f}")
    except Exception:
        print("[물체 상태] 'cube' 바디를 찾을 수 없습니다.")

    # 2. 그리퍼 기준점(grasp_site 또는 TCP) 정보 추출
    site_pos = None
    try:
        # 사용 중이신 모델의 노란 구슬 site 이름("grasp_site" 등)으로 확인하세요.
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")
        site_pos = data.site_xpos[site_id]
        print(f"[그리퍼]   grasp_site 위치 (X, Y, Z) : {site_pos[0]:.4f}, {site_pos[1]:.4f}, {site_pos[2]:.4f}")
    except Exception:
        # 레퍼런스 코드용 예외 처리 (암 베이스 위치로 대체 가능)
        try:
            arm_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "arm")
            site_pos = data.xpos[arm_id]
            print(f"[그리퍼]   Arm Base 위치   (X, Y, Z) : {site_pos[0]:.4f}, {site_pos[1]:.4f}, {site_pos[2]:.4f} (Site 없음)")
        except Exception:
            pass

    # 3. 핵심 오차 진단 연산 (Z축 오프셋 분석)
    if cube_pos is not None and site_pos is not None:
        z_offset_error = site_pos[2] - cube_pos[2]
        print(f"💡 [진단] 큐브 중심과 그리퍼 기준점 간의 Z축 높이 차이: {z_offset_error:.4f} m")
        
        # 공식 문서 기준 매칭 조건 진단
        if abs(z_offset_error) < 0.01:
            print("🟢 진단 결과: 정렬 정상 (그리퍼 중심이 큐브 뱃속 정중앙에 위치함)")
        elif z_offset_error > 0.01:
            print(f"🔴 진단 결과: 높이 오차 발생 (그리퍼가 큐브보다 {z_offset_error*100:.1f}cm 높게 떠 있습니다!)")
        else:
            print(f"🔵 진단 결과: 깊이 오차 발생 (그리퍼가 큐브보다 {abs(z_offset_error)*100:.1f}cm 너무 낮게 박혀 있습니다)")

    # 4. 제어 신호 및 관절 값 출력
    print(f"[액추에이터] 현재 제어 입력값 (data.ctrl) : {list(np.round(data.ctrl, 4))}")
    print(f"[관절 공간] 현재 관절 위치값 (data.qpos) : {list(np.round(data.qpos, 4))}")
    print("====================================================================\n")
    
# debugging report: Contacts Position
def print_contact_report(model, data):
    print("\n========== Contact Report ==========")
    print(f"Number of Contacts : {data.ncon}")

    for i in range(data.ncon):
        contact = data.contact[i]
        geom1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom1)
        geom2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom2)
        # print(f"[{i}] {geom1} <--> {geom2}")
        is_grip = ("finger" in geom1 or "finger" in geom2) and ("cube" in geom1 or "cube" in geom2)
        flag = "<<< GRIP CONTACT >>>" if is_grip else ""
        print(f"[{i}] {geom1} <--> {geom2} {flag}")
        # Contact Position
        print("Contact Position :", np.round(contact.pos,4))    
        print("Distance :", round(contact.dist, 6))
        print("Contact Normal :", np.round(contact.frame[:3], 4))

# debugging report: Constraint Forces
def print_force_report(data):
    print("\n========== Joint Force ==========")
    print("Actuator")
    print(np.round(data.qfrc_actuator,3))
    print("Constraint")
    print(np.round(data.qfrc_constraint,3))
    print("Passive")
    print(np.round(data.qfrc_passive,3))
    print("\n========== Finger Constraint Force ==========")
    print("Finger1 =", round(data.qfrc_constraint[6], 3))
    print("Finger2 =", round(data.qfrc_constraint[7], 3))
    

# debugging report: touch sensor
# 목적: "손가락이 실제로 큐브를 누르고 있는가?"를 판단
def print_touch_report(model, data):
    adr1 = model.sensor_adr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "finger1_touch")]
    adr2 = model.sensor_adr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "finger2_touch")]

    print("\n========== Touch Sensor ==========")
    print("Finger1 Touch =", round(data.sensordata[adr1], 6))
    print("Finger2 Touch =", round(data.sensordata[adr2], 6))

# debugging report: gripper state
# 목적: Finger Target과 실제 위치 비교
def print_gripper_report(data):
    print("\n========== Gripper State ==========")
    print(f"Finger1 : target={data.ctrl[6]:.4f} actual={data.qpos[6]:.4f}")
    print(f"Finger2 : target={data.ctrl[7]:.4f} actual={data.qpos[7]:.4f}")

# debugging report: gripper geometry
def print_gripper_geometry_report(model, data):
    print("\n========== Gripper Geometry ==========")

    finger1_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "finger1_collision")
    finger2_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "finger2_collision")
    cube_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")
    cube_geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "cube_geom")
    grasp_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")

    print("Finger1 center :", np.round(data.geom_xpos[finger1_id], 4))
    print("Finger2 center :", np.round(data.geom_xpos[finger2_id], 4))
    print("Cube center    :", np.round(data.xpos[cube_id], 4))
    print("Grasp site     :", np.round(data.site_xpos[grasp_id], 4))    
    
    
    
    print("Finger1 size =", model.geom_size[finger1_id])
    print("Finger2 size =", model.geom_size[finger2_id])
    print("Cube size    =", model.geom_size[cube_geom_id])
    
    
    bottom1 = data.geom_xpos[finger1_id][2] - model.geom_size[finger1_id][2]
    bottom2 = data.geom_xpos[finger2_id][2] - model.geom_size[finger2_id][2]

    top1 = data.geom_xpos[finger1_id][2] + model.geom_size[finger1_id][2]
    top2 = data.geom_xpos[finger2_id][2] + model.geom_size[finger2_id][2]

    print(f"Finger1 Z : {bottom1:.4f} ~ {top1:.4f}")
    print(f"Finger2 Z : {bottom2:.4f} ~ {top2:.4f}")

    cube_bottom = data.xpos[cube_id][2] - model.geom_size[cube_geom_id][2]
    cube_top = data.xpos[cube_id][2] + model.geom_size[cube_geom_id][2]

    print(f"Cube    Z : {cube_bottom:.4f} ~ {cube_top:.4f}")
    

def print_contact_force_report(model, data):
    print("\n========== Contact Force ==========")

    force = np.zeros(6)

    for i in range(data.ncon):
        contact = data.contact[i]

        geom1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom1)
        geom2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom2)

        if "finger" in geom1 and geom2 == "cube_geom":
            mujoco.mj_contactForce(model, data, i, force)

            print(f"\n[{i}] {geom1} <--> {geom2}")
            print("Normal Force      =", round(force[0], 4))
            print("Friction Force 1  =", round(force[1], 4))
            print("Friction Force 2  =", round(force[2], 4))
            print("Torque           =", np.round(force[3:], 4))
    
    
def print_gripper_orientation():
    print("\n========== Gripper Orientation ==========")

    R1 = data.geom_xmat[finger1_geom_id].reshape(3, 3)
    R2 = data.geom_xmat[finger2_geom_id].reshape(3, 3)

    print("\nFinger1 Rotation Matrix")
    print(np.round(R1, 4))
    print("X =", np.round(R1[:, 0], 4))
    print("Y =", np.round(R1[:, 1], 4))
    print("Z =", np.round(R1[:, 2], 4))

    print("\nFinger2 Rotation Matrix")
    print(np.round(R2, 4))
    print("X =", np.round(R2[:, 0], 4))
    print("Y =", np.round(R2[:, 1], 4))
    print("Z =", np.round(R2[:, 2], 4))    


def print_finger_axis():
    print("\n========== Finger Slide Axis ==========")

    finger1_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger1")
    finger2_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger2")

    R1 = data.xmat[finger1_id].reshape(3,3)
    R2 = data.xmat[finger2_id].reshape(3,3)

    local_axis1 = np.array([1,0,0])
    local_axis2 = np.array([-1,0,0])

    world_axis1 = R1 @ local_axis1
    world_axis2 = R2 @ local_axis2

    print("Finger1 World Axis =", np.round(world_axis1,4))
    print("Finger2 World Axis =", np.round(world_axis2,4))
    

def print_external_force(data):
    print("\n========== External Force ==========")

    print("Cube")
    print(np.round(data.cfrc_ext[cube_body_id], 4))

    print("Finger1")
    print(np.round(data.cfrc_ext[finger1_body_id], 4))

    print("Finger2")
    print(np.round(data.cfrc_ext[finger2_body_id], 4))
   

def print_grip_gap(model, data):
    finger1 = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "finger1_collision")
    finger2 = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "finger2_collision")
    cube = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "cube_geom")

    f1 = data.geom_xpos[finger1]
    f2 = data.geom_xpos[finger2]
    c = data.geom_xpos[cube]

    print("\n========== Grip Gap ==========")
    print(f"Finger1-Cube X = {abs(f1[0]-c[0]):.5f}")
    print(f"Finger2-Cube X = {abs(f2[0]-c[0]):.5f}")
    print(f"Finger Distance = {abs(f1[0]-f2[0]):.5f}")

    
mujoco.mj_forward(model, data)
# cube_pos = get_cube()
cube_start = get_cube().copy()
# approach_pos = (cube_start + np.array([0.0, 0.0, 0.18]))
approach_pos = (cube_start + np.array([0.0, 0.0, 0.28]))
# pick_pos = (cube_start + np.array([0.0, 0.0, 0.05]))
pick_pos = (cube_start + np.array([0.0, 0.0, 0.02]))
lift_pos = (cube_start + np.array([0.0, 0.0, 0.20]))

print("\n==============================")
print("Pick Test Start")
print("==============================")

print("Cube Pos:", cube_start)
print("Approach Pos:", approach_pos)
print("Pick Pos:", pick_pos)
print("Lift Pos:", lift_pos)

with mujoco.viewer.launch_passive(model, data) as viewer:
    viewer.sync()
    
    # -------------------------------------------------------------
    # STEP 1: 초기 대기 상태
    # -------------------------------------------------------------
    input( "\nENTER : Initial State")

    open_gripper(viewer)
    
    # print("f1 =", data.qpos[6])
    # print("f2 =", data.qpos[7])
    print_diagnostic_report(model, data, "STEP 1. Initial State (대기)")
    print_contact_report(model, data)
    print_force_report(data)

    input("\nENTER : Open 확인")
    
    # -------------------------------------------------------------
    # STEP 2: Pick 자세 확인 단계
    # -------------------------------------------------------------
    q_approach = solve_ik(approach_pos)

    move_to_joint_target(q_approach, viewer)
    viewer.sync()

    print_diagnostic_report(model, data, "STEP 2-1. Approach Top (Approach 자세)")
    print_contact_report(model, data)
    print_force_report(data)
    print("\nTCP at Approach:", np.round(get_tcp(), 6))

    input("\nENTER : Approach 확인")

    q_pick = solve_ik(pick_pos)

    move_to_joint_target(q_pick, viewer)
    viewer.sync()

    print_pick_frame_info()
    # print_ee_orientation()
    print_diagnostic_report(model, data, "STEP 2-2. Approach Pick (Pick 자세)")
    print_contact_report(model, data)
    print_force_report(data)
    print("\nTCP at Pick:", np.round(get_tcp(), 6))

    input("\nENTER : Pick 자세 확인")

    # -------------------------------------------------------------
    # STEP 3: Gripping (물체 파지 상태) *핵심 디버깅 구간
    # -------------------------------------------------------------
    close_gripper(viewer)
    viewer.sync()
        
    # print_gripper_orientation()
    # print_finger_axis()
    # print_gripper_geometry_report(model, data)
    print_diagnostic_report(model, data, "STEP 3. Grip (손가락 닫힘 완료)")
    # print_contact_report(model, data)
    # print_force_report(data)
    
    # print("\n========== Finger Joint ==========")
    # print(f"Finger1 target = {data.ctrl[6]:.5f}")
    # print(f"Finger1 actual = {data.qpos[6]:.5f}")
    # print(f"Finger2 target = {data.ctrl[7]:.5f}")
    # print(f"Finger2 actual = {data.qpos[7]:.5f}")
    # print("\n========== Finger Actuator Force ==========")
    # print(f"Finger1 actuator = {data.actuator_force[6]:.4f}")
    # print(f"Finger2 actuator = {data.actuator_force[7]:.4f}")

    # print_contact_force_report(model, data)
    # print_external_force(data)
    # print_touch_report(model, data)
    print_grip_gap(model, data)
    

    input("\nENTER : Close 결과 확인")
    
    # -------------------------------------------------------------
    # STEP 4: Lift (들어올리기 및 슬립 여부 확인)
    # -------------------------------------------------------------
    # q_lift = solve_ik(lift_pos)
    # TEST code 
    # data.ctrl[3] = 0.1  # 제어 신호를 위로 상승 유도 from test_grip_reference.py
    # move_to_joint_target(q_approach, viewer)
    # q_lift = solve_ik_pure(lift_pos)
    q_lift = solve_ik(lift_pos)
    
    print("\n========== After IK ==========")
    print("TCP =", np.round(get_tcp(), 5))
    print("Joint =", np.round(data.qpos[:6], 5))
    print("Contacts =", data.ncon)
    
    # move_to_joint_target(q_lift, viewer, debug=True)
    move_to_joint_target(q_lift, viewer)
    viewer.sync()

    # print_gripper_orientation()
    # print_gripper_geometry_report(model, data)
    print_diagnostic_report(model, data, "STEP 4. Lift (들어올리기)")
    # print_contact_report(model, data)
    # print_force_report(data)
    # print_touch_report(model, data)
    
    # print("\n========== Finger Joint ==========")
    # print(f"Finger1 target = {data.ctrl[6]:.5f}")
    # print(f"Finger1 actual = {data.qpos[6]:.5f}")
    # print(f"Finger2 target = {data.ctrl[7]:.5f}")
    # print(f"Finger2 actual = {data.qpos[7]:.5f}")
    # print("\n========== Finger Actuator Force ==========")
    # print(f"Finger1 actuator = {data.actuator_force[6]:.4f}")
    # print(f"Finger2 actuator = {data.actuator_force[7]:.4f}")
    print_grip_gap(model, data)
    
    cube_now = get_cube()
    print("\n========== Cube Movement ==========")
    print("Initial Z =", round(cube_start[2], 4))
    print("Current Z =", round(cube_now[2], 4))
    print("Lift Distance =", round(cube_now[2] - cube_start[2], 4))

    input("\nENTER : Lift 결과 확인")
