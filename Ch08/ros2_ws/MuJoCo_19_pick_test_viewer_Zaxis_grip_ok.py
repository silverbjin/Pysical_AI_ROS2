import time
from xml.etree.ElementTree import XML
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
    
def solve_ik(target_pos, max_iter=300, damping=0.05, alpha=0.5, pos_tol=1e-3, rot_tol=1e-2):
    q=data.qpos[:6].copy()
    q_min=model.jnt_range[:6,0].copy()
    q_max=model.jnt_range[:6,1].copy()
    free_idx=[0,1,2,3,4,5]
    jacp=np.zeros((3,model.nv))
    jacr=np.zeros((3,model.nv))
    desired_z=np.array([0.0,0.0,-1.0])

    for i in range(max_iter):
        data.qpos[:6]=q
        mujoco.mj_forward(model,data)
        current_pos=get_tcp()
        pos_error=target_pos-current_pos
        R=data.site_xmat[ee_site_id].reshape(3,3)
        current_z=R[:,2]
        rot_error=np.cross(current_z,desired_z)

        if np.linalg.norm(pos_error)<pos_tol and np.linalg.norm(rot_error)<rot_tol:
            print(f"IK Converged in {i} iterations")
            return q

        mujoco.mj_jacSite(model,data,jacp,jacr,ee_site_id)
        J_pos=jacp[:,free_idx]
        J_rot=jacr[:,free_idx]
        J=np.vstack((J_pos,J_rot))
        # error=np.concatenate((pos_error,0.5*rot_error))
        error=np.concatenate((pos_error,1.0*rot_error))
        dq=J.T@np.linalg.inv(J@J.T+damping*np.eye(6))@error
        q+=alpha*dq
        q=np.clip(q,q_min,q_max)

    print("IK Failed")
    return q

import copy  # [추가] 파이썬 내장 복사 모듈 필요
def solve_ik_pure(target_pos, max_iter=300, damping=0.05, alpha=0.5, pos_tol=1e-3, rot_tol=1e-2):
# def solve_ik(target_pos, max_iter=300, damping=0.05, alpha=0.5, pos_tol=1e-3, rot_tol=1e-2):    
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
    
    """
    현재 조인트 위치에서 목표 조인트 위치까지 부드럽게 보간하여 이동합니다.
    """
    # 1. 이동 시작 시점의 현재 조인트 위치 캡처 (보간의 시작점)
    start_q = data.qpos[:6].copy()
    
    # 지정된 step 수만큼 반복하며 조금씩 이동 (궤적 생성)
    for i in range(max_steps):
        # 2. 현재 스텝(i)이 전체 제한 스텝(max_steps)에서 차지하는 진행률 계산 (0.0 ~ 1.0)
        t = i / float(max_steps - 1) if max_steps > 1 else 1.0
        
        # 3. 부드러운 가감속(Smoothstep)을 위한 코사인 보간 가중치 적용
        #   [선택사항] 더 부드러운 가감속을 위한 코사인 보간 (Cosine Interpolation / Smoothstep)
        #   시작과 끝에서 속도가 0이 되도록 만들어 오버슈팅을 더욱 방지합니다.
        alpha = 0.5 * (1.0 - np.cos(np.pi * t))
        
        # 4. 시작점과 목표점 사이의 부드러운 중간 목표 조인트 각도 연산
        #   현재 스텝에서의 타겟 각도 계산
        current_ctrl = (1.0 - alpha) * start_q + alpha * q_target
        
        # 5. 계산된 제어 입력을 엑추에이터에 인가
        data.ctrl[:6] = current_ctrl
        
        # 물리 엔진 1스텝 전진
        mujoco.mj_step(model, data)
        
        # 뷰어 동기화 및 타임 슬립 (너무 자주 업데이트하면 느려지므로 적절히 조절 가능)
        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

        # 6. 오차 판정 및 조기 종료 (기존 로직 유지)
        err = np.linalg.norm(q_target - data.qpos[:6])
        if err < joint_tol:
            print(f"Joint Converged in {i} steps")
            break
        
    # 최종 위치 한 번 더 강제 동기화 보장
    if viewer is not None:
        viewer.sync()


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

# -------------------------------------------------------------
# 1. 기하학 및 좌표계 진단 (Kinematics & Alignment)
# -------------------------------------------------------------
def print_pick_frame_info():
    # 활용 목적: 그리퍼 핵심 부품(베이스, 양 손가락)들과 타겟 물체(Cube) 간의 
    #   글로벌 좌표 일치 여부 및 3차원 상대 거리를 한눈에 파악하여 
    #   초기 접근(Approach) 및 파지 위치의 타당성을 진단합니다.
    # 확인 가능한 결과:
    #   - ee_site($TCP$), tool0, 그리퍼 베이스 및 손가락 1, 2의 $X, Y, Z$ 절대 좌표.
    #   - 큐브의 절대 좌표 및 큐브와 $TCP$ 간의 3차원 오차 벡터($\Delta X, \Delta Y, \Delta Z$).
    
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
    # 활용 목적: End-Effector($TCP$)의 회전 행렬(Rotation Matrix)을 추출하여, 
    #   그리퍼가 물체를 향해 올바른 방향(예: 수직 하향)으로 접근하고 있는지 
    #   회전 상태를 진단합니다.
    # 확인 가능한 결과:
    #   - $TCP$ 사이트 기준 기저 벡터($X, Y, Z$ 축의 방향 벡터). 
    #   이를 통해 기절단 방향(Gimbal Lock 또는 회전 정렬 불량)을 시각적으로 매칭 가능.
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
    # 활용 목적: 각 스텝별로 그리퍼 기준점(grasp_site)과 큐브 간의 Z축 높이 오차를 
    #   자동 계산하고, 정상·높음·낮음 상태를 조건문으로 판별하여 시뮬레이션 시퀀스 플로우를 
    #   직관적으로 추적합니다.
    # 확인 가능한 결과:
    #   - 큐브 중심 및 그리퍼 사이트의 $X, Y, Z$ 좌표.
    #   - Z 오프셋 오차 알림: 정렬 정상(🟢), 높이 처짐(🔴), 너무 깊게 박힘(🔵) 상태 메시지.
    #   - 현재 액추에이터 제어 입력 전체(data.ctrl)와 전체 관절 공간 상태(data.qpos).
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

# debugging report: gripper geometry
def print_gripper_geometry_report(model, data):
    # 활용 목적: 손가락 콜리전(geom)과 큐브 기하 형상의 실제 물리적 크기(두께/높이)와 
    #   바운딩 박스의 Z축 범위(Min~Max)를 계산하여, 기하학적으로 "손가락이 큐브를 
    #   완전히 덮을 수 있는 영역인가"를 수학적으로 검증합니다.
    # 확인 가능한 결과:
    #   - 손가락들과 큐브, 사이트의 중심 좌표 및 각각의 XML 상 정의된 크기(geom_size).
    #   - 각 요소의 Z축 최하단(Bottom) 및 최상단(Top) 임계 위치값.
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

# -------------------------------------------------------------
# 2. 접촉 및 마찰력 진단 (Contact Mechanics)    
# -------------------------------------------------------------
# debugging report: Contacts Position
def print_contact_report(model, data):
    #활용 목적: 손가락 콜리전(geom)과 큐브 기하 형상의 실제 물리적 크기(두께/높이)와 
    #   바운딩 박스의 Z축 범위(Min~Max)를 계산하여, 
    #   기하학적으로 "손가락이 큐브를 완전히 덮을 수 있는 영역인가"를 수학적으로 검증합니다.
    # 확인 가능한 결과:
    #   - 손가락들과 큐브, 사이트의 중심 좌표 및 각각의 XML 상 정의된 크기(geom_size).
    #   - 각 요소의 Z축 최하단(Bottom) 및 최상단(Top) 임계 위치값.
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

def print_contact_force_report(model, data):
    # 활용 목적: 손가락과 큐브 메쉬 사이에 가해지는 실제 물리적인 법선 힘(수직항력)과 
    #   마찰력(Friction Force) 뉴턴($N$) 단위를 정밀 측정하여, 
    #   리프트 시 물체가 미끄러져 떨어지는 원인이 마찰력 부족인지 진단합니다.
    # 확인 가능한 결과:
    #   - 지정된 충돌 패어의 수직 항력(Normal Force), 양방향 마찰력(Friction Force 1, 2), 
    #     그리고 접촉 비틀림 토크(Torque).
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

# -------------------------------------------------------------
# 3. 제어 및 액추에이터 역학 진단 (Dynamics & Forces)
# -------------------------------------------------------------
# debugging report: Constraint Forces
def print_force_report(data):
    # 활용 목적: 로봇 시스템 전체 및 그리퍼 손가락 관절에 작용하는 액추에이터 구동력, 
    #   물리적 구속력(제한/충돌력), 수동적 힘(중력/코리올리 등)의 역학적 분포를 비교하여 
    #   제어 성능을 분석합니다.
    # 확인 가능한 결과:
    #   - 전체 일반화 좌표계상의 액추에이터 힘(qfrc_actuator), 구속 반력(qfrc_constraint), 
    #     수동 힘(qfrc_passive).
    #   - 그리퍼 손가락 1, 2 관절(인덱스 6, 7번)이 받는 순수 구속력(Constraint Force).
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
    # 활용 목적: XML에 정의된 타치 센서(touch sensor) 데이터를 리딩하여, 
    #   손가락 패드 표면에 가해진 압력과 물리적 반력을 확인합니다. 
    #   (그리퍼 내부 폐루프 제어 시 피드백 변수로 활용 가능)
    # 확인 가능한 결과:
    #   - finger1_touch 및 finger2_touch 센서의 스칼라 검출값.
    adr1 = model.sensor_adr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "finger1_touch")]
    adr2 = model.sensor_adr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "finger2_touch")]

    print("\n========== Touch Sensor ==========")
    print("Finger1 Touch =", round(data.sensordata[adr1], 6))
    print("Finger2 Touch =", round(data.sensordata[adr2], 6))

# debugging report: gripper state
# 목적: Finger Target과 실제 위치 비교
def print_gripper_report(data):
    # 활용 목적: 그리퍼 모터에 내린 목표 제어 명령값(target)과 
    #   실제 관절이 도달한 위치(actual)를 비교하여, 그리퍼가 물체에 걸려 덜 닫힌 상태(정상 파지)인지 
    #   아니면 허공에서 다 닫혀버렸는지(파지 실패) 판별합니다.
    # 확인 가능한 결과:
    #   - 손가락 1, 2 관절의 data.ctrl(목표 변위) 대 data.qpos(실제 변위).
    print("\n========== Gripper State ==========")
    print(f"Finger1 : target={data.ctrl[6]:.4f} actual={data.qpos[6]:.4f}")
    print(f"Finger2 : target={data.ctrl[7]:.4f} actual={data.qpos[7]:.4f}")

# -------------------------------------------------------------
# 4. 구조적 결함 및 외력 진단 (Advanced Troubleshooting)
# -------------------------------------------------------------
def print_gripper_orientation():
    # 활용 목적: 양쪽 손가락 지오메트리 자체의 개별 회전 행렬을 검사하여, 
    #   그리퍼 조립 시 손가락 메쉬 자체가 꼬이거나 
    #   반대로 뒤집혀서 조립되었는지(XML 모델링 에러) 확인합니다.
    # 확인 가능한 결과:
    #   - Finger 1과 Finger 2 각각의 글로벌 회전 행렬($R_{mat}$) 및 대칭성 여부.
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
    # 활용 목적: 손가락 바디의 로컬 이동 축(local_axis)을 월드 좌표계(world_axis)로 변환하여, 
    #   그리퍼가 다치거나 열릴 때 손가락이 의도한 방향(예: X축 평행 방향)으로 
    #   똑바로 슬라이딩하고 있는지 구동 축을 검증합니다.
    # 확인 가능한 결과:
    #   - 월드 좌표계로 투영된 손가락 1, 2의 실시간 구동 방향 벡터.
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
    # 활용 목적: 큐브와 손가락 바디에 작용하는 
    #   순수 외력 합력 렌치(External Force/Torque 6자유도 벡터)를 확인하여, 
    #   공간 상에서 예상치 못한 비정상적인 충돌 유령 힘이나 중력 처짐 외력이 작용하는지 파악합니다.
    # 확인 가능한 결과:
    #   - 큐브 및 양 손가락 링크 바디 중심에 걸리는 3차원 외력($F_x, F_y, F_z$)과 
    #     외력 토크($T_x, T_y, T_z$) 배열.
    print("\n========== External Force ==========")

    print("Cube")
    print(np.round(data.cfrc_ext[cube_body_id], 4))

    print("Finger1")
    print(np.round(data.cfrc_ext[finger1_body_id], 4))

    print("Finger2")
    print(np.round(data.cfrc_ext[finger2_body_id], 4))
   
def print_grip_gap(model, data):
    # 활용 목적: 파지 직전/직후 손가락 사이의 절대 거리와 
    #   큐브 중심 기준 양 손가락의 상대적 이격 거리를 나노미터 단위 레벨로 추적하여, 
    #   그리퍼 중심이 큐브 한가운데 정중앙에 편심 없이 정확히 안착했는지 진단합니다.
    # 확인 가능한 결과:
    #   - Finger1과 큐브 간의 $X$축 거리 오차, Finger2와 큐브 간의 $X$축 거리 오차.
    #   - 양 손가락 사이의 순수 간격 거리(Finger Distance).
    
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
    # print_contact_report(model, data)
    # print_force_report(data)

    input("\nENTER : Open 확인")
    # -------------------------------------------------------------
    # STEP 2: Pick 자세 확인 단계
    # -------------------------------------------------------------
    q_approach = solve_ik(approach_pos)
    move_to_joint_target(q_approach, viewer)
    viewer.sync()

    print_diagnostic_report(model, data, "STEP 2-1. Approach Top (Approach 자세)")
    # print_contact_report(model, data)
    # print_force_report(data)
    print("\nTCP at Approach:", np.round(get_tcp(), 6))

    input("\nENTER : Approach 확인")
    q_pick = solve_ik(pick_pos)
    move_to_joint_target(q_pick, viewer)
    viewer.sync()

    print_diagnostic_report(model, data, "STEP 2-2. Approach Pick (Pick 자세)")
    # print_pick_frame_info()
    # print_ee_orientation()
    # print_contact_report(model, data)
    # print_force_report(data)
    print("\nTCP at Pick:", np.round(get_tcp(), 6))

    input("\nENTER : Pick 자세 확인")
    # -------------------------------------------------------------
    # STEP 3: Gripping (물체 파지 상태) *핵심 디버깅 구간
    # -------------------------------------------------------------
    close_gripper(viewer)
    viewer.sync()
        
    print_diagnostic_report(model, data, "STEP 3. Grip (손가락 닫힘 완료)")
    # print_gripper_orientation()
    # print_finger_axis()
    # print_gripper_geometry_report(model, data)
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
    q_lift = solve_ik_pure(lift_pos)
    
    # print("\n========== After IK ==========")
    # print("TCP =", np.round(get_tcp(), 5))
    # print("Joint =", np.round(data.qpos[:6], 5))
    # print("Contacts =", data.ncon)
    
    # move_to_joint_target(q_lift, viewer, debug=True)
    move_to_joint_target(q_lift, viewer)
    viewer.sync()

    print_diagnostic_report(model, data, "STEP 4. Lift (들어올리기)")
    # print_gripper_orientation()
    # print_gripper_geometry_report(model, data)
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
